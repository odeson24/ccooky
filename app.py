from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request as FastAPIRequest
import requests
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GitLab MR Lister")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# GitLab configuration
GITLAB_URL = os.getenv('GITLAB_URL', 'https://gitlab.com')
GITLAB_PROJECT_ID = os.getenv('GITLAB_PROJECT_ID')
GITLAB_PRIVATE_TOKEN = os.getenv('GITLAB_PRIVATE_TOKEN')


@app.get('/', response_class=HTMLResponse)
async def index(request: FastAPIRequest):
    """Serve the main page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get('/api/merge-requests')
async def get_merge_requests(
    state: str = Query('opened', description="Filter by state: opened, merged, closed, all"),
    per_page: int = Query(20, description="Results per page"),
    page: int = Query(1, description="Page number")
):
    """Fetch merge requests from GitLab API"""
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
        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()

        # Return the data
        return response.json()

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


@app.get('/api/health')
async def health_check():
    """Health check endpoint"""
    configured = bool(GITLAB_PROJECT_ID and GITLAB_PRIVATE_TOKEN)
    return {
        'status': 'ok',
        'configured': configured,
        'gitlab_url': GITLAB_URL,
        'project_id': GITLAB_PROJECT_ID if configured else 'Not configured'
    }


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
