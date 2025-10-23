# GitLab Merge Request Lister

A clean and modern web application to view and filter GitLab merge requests from any repository using the GitLab API.

## Features

- View all merge requests from a GitLab repository
- Filter by state (opened, merged, closed, all)
- Beautiful, responsive UI
- Real-time connection status
- Detailed MR information including author, dates, labels, and descriptions
- Direct links to merge requests
- **ClickUp Integration**: Automatically displays ClickUp task information for merge requests with branch names containing ClickUp task IDs (format: `...CU-{task-id}`)
- **Performance Caching**: SQLite-based caching with configurable TTL for fast loading
- **Auto-refresh**: Background job to keep cache updated automatically
- **Cache Management**: Clear cache and force refresh capabilities

## Prerequisites

- Python 3.7 or higher
- GitLab account with access to the repository
- GitLab Personal Access Token

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ccooky
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv

# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure GitLab settings:
```bash
cp .env.example .env
```

Edit `.env` and add your GitLab configuration:
```
GITLAB_URL=https://gitlab.com
GITLAB_PROJECT_ID=your_project_id
GITLAB_PRIVATE_TOKEN=your_private_token

# Optional: ClickUp integration
CLICKUP_API_TOKEN=your_clickup_api_token
```

## Getting GitLab Credentials

### 1. GitLab Project ID

You can find your project ID in several ways:

**Method 1: Project Settings**
- Go to your GitLab project
- Navigate to Settings > General
- The Project ID is displayed at the top

**Method 2: Project URL**
- You can also use the project path: `group/project-name`
- Example: `mygroup/myproject`

### 2. Personal Access Token

1. Log in to your GitLab account
2. Go to User Settings > Access Tokens
3. Create a new token with these scopes:
   - `api` (full API access)
   - `read_api` (read-only API access)
4. Copy the token immediately (you won't be able to see it again)

## ClickUp Integration (Optional)

The application automatically displays ClickUp task information for merge requests when:
1. The branch name contains a ClickUp task ID in the format: `...CU-{task-id}`
   - Example: `feature/add-login-CU-abc123`
   - Example: `bugfix/fix-auth-CU-xyz789`
2. A ClickUp API token is configured in your `.env` file

### Getting a ClickUp API Token

1. Log in to your ClickUp account
2. Click on your avatar in the bottom-left corner
3. Go to Settings > Apps
4. Click "Generate" under API Token
5. Copy the token and add it to your `.env` file as `CLICKUP_API_TOKEN`

### What ClickUp Information is Displayed

When a ClickUp task is found, the application displays:
- Task name with a direct link to the task
- Task status
- Task priority (if set)
- Task tags (if any)

**Note:** If no ClickUp API token is configured, the application will still work normally but won't display ClickUp task information.

## Performance & Caching

The application uses SQLite-based caching to improve performance and reduce API calls:

### How It Works

1. **First Request**: Data is fetched from GitLab and ClickUp APIs and cached in the database
2. **Subsequent Requests**: Data is served from cache (much faster) until TTL expires
3. **Auto-refresh**: Background job automatically refreshes cache at configurable intervals
4. **Manual Control**: Use "Refresh" to force fetch fresh data or "Clear Cache" to reset

### Cache Configuration

Configure cache behavior in your `.env` file:

```env
# Cache TTL (Time To Live) in minutes
MR_CACHE_TTL_MINUTES=5          # How long to cache merge requests (default: 5)
CLICKUP_CACHE_TTL_MINUTES=10    # How long to cache ClickUp tasks (default: 10)

# Auto-refresh interval in minutes (0 to disable)
AUTO_REFRESH_INTERVAL_MINUTES=5  # Background refresh frequency (default: 5, 0=disabled)
```

### Cache Benefits

- **Faster Load Times**: Cached responses load instantly
- **Reduced API Rate Limits**: Fewer API calls to GitLab and ClickUp
- **Better UX**: Immediate response for cached data
- **Always Fresh**: Auto-refresh keeps data up-to-date

### Cache Indicators

- The UI shows cache status in the header: `Cache: X MRs, Y tasks (TTL: Zm)`
- MR list shows `(cached)` or `(fresh)` indicator
- Real-time cache statistics available

## Usage

1. Start the application:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

3. Use the dropdown to filter merge requests by state:
   - Opened: Currently open MRs
   - Merged: Merged MRs
   - Closed: Closed MRs
   - All: All MRs

4. Click "Refresh" to reload the merge requests

## API Endpoints

The application provides the following REST API endpoints:

### Get Merge Requests
```
GET /api/merge-requests
```

Query Parameters:
- `state` (optional): Filter by state (opened, merged, closed, all). Default: opened
- `per_page` (optional): Number of results per page. Default: 20
- `page` (optional): Page number. Default: 1

Example:
```bash
curl "http://localhost:5000/api/merge-requests?state=opened&per_page=10"
```

### Health Check
```
GET /api/health
```

Returns the application status, configuration info, and cache statistics.

Example:
```bash
curl http://localhost:5000/api/health
```

### Clear Cache
```
POST /api/cache/clear
```

Clears all cached data (merge requests and ClickUp tasks).

Example:
```bash
curl -X POST http://localhost:5000/api/cache/clear
```

### Refresh Cache
```
POST /api/cache/refresh
```

Forces a refresh of all cached data from APIs.

Example:
```bash
curl -X POST http://localhost:5000/api/cache/refresh
```

### Get Cache Statistics
```
GET /api/cache/stats
```

Returns detailed cache statistics.

Example:
```bash
curl http://localhost:5000/api/cache/stats
```

## Configuration Options

Edit `.env` to customize:

**GitLab Configuration:**
- `GITLAB_URL`: Your GitLab instance URL (default: https://gitlab.com)
- `GITLAB_PROJECT_ID`: Your project ID or path
- `GITLAB_PRIVATE_TOKEN`: Your personal access token

**ClickUp Configuration (Optional):**
- `CLICKUP_API_TOKEN`: Your ClickUp API token (optional - enables ClickUp task integration)

**Cache Configuration:**
- `MR_CACHE_TTL_MINUTES`: Merge request cache TTL in minutes (default: 5)
- `CLICKUP_CACHE_TTL_MINUTES`: ClickUp task cache TTL in minutes (default: 10)
- `AUTO_REFRESH_INTERVAL_MINUTES`: Auto-refresh interval in minutes, 0 to disable (default: 5)

**Application Configuration:**
- `PORT`: Application port (default: 5000)
- `DEBUG`: Enable debug mode (default: False)

## Project Structure

```
ccooky/
├── app.py                  # FastAPI application
├── database.py             # Database models and cache manager
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment configuration
├── .gitignore             # Git ignore file
├── README.md              # This file
├── mr_cache.db            # SQLite cache database (auto-created)
├── templates/
│   └── index.html         # Main HTML template
└── static/
    ├── css/
    │   └── style.css      # Stylesheet
    └── js/
        └── app.js         # Frontend JavaScript
```

## Troubleshooting

### Connection Issues

If you see "Not Configured" or connection errors:
1. Verify your `.env` file exists and has correct values
2. Check that your GitLab token has the required scopes
3. Ensure the project ID is correct
4. Verify you have access to the GitLab project

### API Errors

If you get 401 Unauthorized:
- Your token may be expired or invalid
- Create a new personal access token

If you get 404 Not Found:
- Verify the project ID is correct
- Check that you have access to the project

### Cache Issues

If cache seems stale or outdated:
- Click the "Clear Cache" button in the UI
- Use the API: `curl -X POST http://localhost:5000/api/cache/clear`
- Adjust `MR_CACHE_TTL_MINUTES` and `CLICKUP_CACHE_TTL_MINUTES` in `.env`
- Check auto-refresh is enabled: `AUTO_REFRESH_INTERVAL_MINUTES > 0`

If cache database is corrupted:
- Stop the application
- Delete `mr_cache.db` file
- Restart the application (database will be recreated)

## Development

To run in development mode with auto-reload:

1. Set DEBUG=True in `.env`
2. Run the application:
```bash
python app.py
```

Or run directly with uvicorn:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 5000
```

## Production Deployment

For production, use uvicorn with multiple workers:

```bash
uvicorn app:app --host 0.0.0.0 --port 5000 --workers 4
```

## Technologies Used

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Database**: SQLite with SQLAlchemy ORM
- **Caching**: Custom cache manager with TTL
- **Background Jobs**: APScheduler
- **APIs**:
  - GitLab REST API v4
  - ClickUp REST API v2 (optional)
- **HTTP Client**: requests library

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
