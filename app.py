from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request as FastAPIRequest
from contextlib import asynccontextmanager
import requests
import os
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from database import init_db, get_db, CacheManager
from sqlalchemy.orm import Session

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Background scheduler for auto-refresh
scheduler = BackgroundScheduler()


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("Starting up...")
    init_db()

    # Start background scheduler if auto-refresh is enabled
    auto_refresh_interval = int(os.getenv('AUTO_REFRESH_INTERVAL_MINUTES', 5))
    if auto_refresh_interval > 0:
        scheduler.add_job(
            auto_refresh_cache,
            'interval',
            minutes=auto_refresh_interval,
            id='auto_refresh',
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"Auto-refresh enabled: every {auto_refresh_interval} minutes")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(title="GitLab MR Lister", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# GitLab configuration
GITLAB_URL = os.getenv('GITLAB_URL', 'https://gitlab.com')
GITLAB_PROJECT_ID = os.getenv('GITLAB_PROJECT_ID')
GITLAB_PRIVATE_TOKEN = os.getenv('GITLAB_PRIVATE_TOKEN')

# ClickUp configuration
CLICKUP_API_TOKEN = os.getenv('CLICKUP_API_TOKEN')
CLICKUP_API_URL = 'https://api.clickup.com/api/v2'

# Cache configuration
MR_CACHE_TTL = int(os.getenv('MR_CACHE_TTL_MINUTES', 5))
CLICKUP_CACHE_TTL = int(os.getenv('CLICKUP_CACHE_TTL_MINUTES', 10))

# Initialize cache manager
cache_manager = CacheManager(
    mr_ttl_minutes=MR_CACHE_TTL,
    clickup_ttl_minutes=CLICKUP_CACHE_TTL
)


def extract_clickup_task_id(branch_name):
    """Extract ClickUp task ID from branch name in format ...CU-{task-id}"""
    import re
    if not branch_name:
        return None

    # Match pattern like "CU-abc123" or "CU-123xyz"
    match = re.search(r'CU-([a-zA-Z0-9]+)', branch_name)
    if match:
        return match.group(1)
    return None


def get_clickup_task(task_id, db: Session = None):
    """Fetch ClickUp task information by task ID (with caching)"""
    if not CLICKUP_API_TOKEN or not task_id:
        return None

    # Try to get from cache first
    if db:
        cached_task = cache_manager.get_cached_clickup_task(db, task_id)
        if cached_task:
            return cached_task

    try:
        api_url = f"{CLICKUP_API_URL}/task/{task_id}"
        headers = {
            'Authorization': CLICKUP_API_TOKEN
        }

        response = requests.get(api_url, headers=headers, timeout=5)
        response.raise_for_status()

        task_data = response.json()

        # Extract relevant task information
        task_info = {
            'id': task_data.get('id'),
            'name': task_data.get('name'),
            'status': task_data.get('status', {}).get('status'),
            'url': task_data.get('url'),
            'priority': task_data.get('priority', {}).get('priority') if task_data.get('priority') else None,
            'due_date': task_data.get('due_date'),
            'tags': [tag.get('name') for tag in task_data.get('tags', [])]
        }

        # Cache the task
        if db:
            cache_manager.cache_clickup_task(db, task_id, task_info)

        return task_info

    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch ClickUp task {task_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing ClickUp task {task_id}: {e}")
        return None


@app.get('/', response_class=HTMLResponse)
async def index(request: FastAPIRequest):
    """Serve the main page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get('/api/merge-requests')
async def get_merge_requests(
    state: str = Query('opened', description="Filter by state: opened, merged, closed, all"),
    per_page: int = Query(20, description="Results per page"),
    page: int = Query(1, description="Page number"),
    force_refresh: bool = Query(False, description="Force refresh from API, bypass cache"),
    db: Session = Depends(get_db)
):
    """Fetch merge requests from GitLab API (with caching)"""
    try:
        # Check configuration
        if not GITLAB_PROJECT_ID or not GITLAB_PRIVATE_TOKEN:
            raise HTTPException(
                status_code=400,
                detail={
                    'error': 'GitLab configuration missing',
                    'message': 'Please set GITLAB_PROJECT_ID and GITLAB_PRIVATE_TOKEN in .env file'
                }
            )

        # Try to get from cache first (only for first page with default per_page)
        merge_requests = None
        from_cache = False

        if not force_refresh and page == 1 and per_page <= 50:
            merge_requests = cache_manager.get_cached_merge_requests(db, GITLAB_PROJECT_ID, state)
            if merge_requests:
                from_cache = True
                logger.info(f"Returning {len(merge_requests)} MRs from cache")

        # If not in cache or force refresh, fetch from API
        if merge_requests is None:
            # Build API URL
            api_url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests"

            # Set headers
            headers = {
                'PRIVATE-TOKEN': GITLAB_PRIVATE_TOKEN
            }

            # Set parameters
            params = {
                'state': state,
                'per_page': per_page,
                'page': page,
                'order_by': 'updated_at',
                'sort': 'desc'
            }

            # Make request to GitLab API
            logger.info(f"Fetching MRs from GitLab API (state={state}, page={page})")
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()

            merge_requests = response.json()

        # Enrich merge requests with ClickUp task information
        for mr in merge_requests:
            source_branch = mr.get('source_branch')
            if source_branch:
                task_id = extract_clickup_task_id(source_branch)
                if task_id:
                    clickup_task = get_clickup_task(task_id, db)
                    mr['clickup_task'] = clickup_task
                    mr['clickup_task_id'] = task_id
                else:
                    mr['clickup_task'] = None
                    mr['clickup_task_id'] = None
            else:
                mr['clickup_task'] = None
                mr['clickup_task_id'] = None

        # Cache the enriched data (only for first page)
        if not from_cache and page == 1 and per_page <= 50:
            cache_manager.cache_merge_requests(db, GITLAB_PROJECT_ID, state, merge_requests)

        # Return the enriched data with cache metadata
        return {
            'data': merge_requests,
            'from_cache': from_cache,
            'cache_ttl_minutes': MR_CACHE_TTL
        }

    except requests.exceptions.HTTPError as e:
        logger.error(f'GitLab API error: {e}')
        raise HTTPException(
            status_code=e.response.status_code,
            detail={
                'error': 'Failed to fetch merge requests from GitLab',
                'status_code': e.response.status_code,
                'details': e.response.text
            }
        )

    except requests.exceptions.RequestException as e:
        logger.error(f'Request error: {e}')
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Failed to connect to GitLab',
                'details': str(e)
            }
        )

    except HTTPException:
        # Re-raise HTTPExceptions
        raise

    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        raise HTTPException(
            status_code=500,
            detail={
                'error': 'Internal server error',
                'details': str(e)
            }
        )


def auto_refresh_cache():
    """Background job to refresh cache automatically"""
    logger.info("Auto-refresh: Starting cache refresh...")
    try:
        db = SessionLocal()
        try:
            # Refresh for common states
            states = ['opened', 'merged', 'closed']
            for state in states:
                try:
                    # Force refresh by clearing cache and fetching new data
                    logger.info(f"Auto-refresh: Refreshing {state} MRs...")

                    # Build API URL
                    api_url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests"
                    headers = {'PRIVATE-TOKEN': GITLAB_PRIVATE_TOKEN}
                    params = {
                        'state': state,
                        'per_page': 50,
                        'page': 1,
                        'order_by': 'updated_at',
                        'sort': 'desc'
                    }

                    response = requests.get(api_url, headers=headers, params=params, timeout=10)
                    response.raise_for_status()
                    merge_requests = response.json()

                    # Enrich with ClickUp data
                    for mr in merge_requests:
                        source_branch = mr.get('source_branch')
                        if source_branch:
                            task_id = extract_clickup_task_id(source_branch)
                            if task_id:
                                clickup_task = get_clickup_task(task_id, db)
                                mr['clickup_task'] = clickup_task
                                mr['clickup_task_id'] = task_id

                    # Cache the data
                    cache_manager.cache_merge_requests(db, GITLAB_PROJECT_ID, state, merge_requests)
                    logger.info(f"Auto-refresh: Cached {len(merge_requests)} {state} MRs")

                except Exception as e:
                    logger.error(f"Auto-refresh: Error refreshing {state} MRs: {e}")

        finally:
            db.close()

        logger.info("Auto-refresh: Cache refresh completed")

    except Exception as e:
        logger.error(f"Auto-refresh: Fatal error: {e}")


@app.get('/api/health')
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    configured = bool(GITLAB_PROJECT_ID and GITLAB_PRIVATE_TOKEN)
    cache_stats = cache_manager.get_cache_stats(db)

    return {
        'status': 'ok',
        'configured': configured,
        'gitlab_url': GITLAB_URL,
        'project_id': GITLAB_PROJECT_ID if configured else 'Not configured',
        'cache_enabled': True,
        'cache_stats': cache_stats
    }


@app.post('/api/cache/clear')
async def clear_cache(db: Session = Depends(get_db)):
    """Clear all cache"""
    try:
        cache_manager.clear_all_cache(db)
        return {'status': 'success', 'message': 'Cache cleared successfully'}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail={'error': 'Failed to clear cache', 'details': str(e)})


@app.post('/api/cache/refresh')
async def refresh_cache(db: Session = Depends(get_db)):
    """Force refresh cache from APIs"""
    try:
        # Clear existing cache
        cache_manager.clear_all_cache(db)

        # Trigger immediate refresh
        auto_refresh_cache()

        return {'status': 'success', 'message': 'Cache refreshed successfully'}
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail={'error': 'Failed to refresh cache', 'details': str(e)})


@app.get('/api/cache/stats')
async def get_cache_stats(db: Session = Depends(get_db)):
    """Get cache statistics"""
    try:
        stats = cache_manager.get_cache_stats(db)
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail={'error': 'Failed to get cache stats', 'details': str(e)})


if __name__ == '__main__':
    import uvicorn

    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    print(f"Starting GitLab MR Lister on http://localhost:{port}")
    print(f"GitLab URL: {GITLAB_URL}")
    print(f"Project ID: {GITLAB_PROJECT_ID or 'Not configured'}")
    print(f"Token configured: {'Yes' if GITLAB_PRIVATE_TOKEN else 'No'}")

    uvicorn.run(
        "app:app",
        host='0.0.0.0',
        port=port,
        reload=debug,
        log_level='debug' if debug else 'info'
    )
