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

Returns the application status and configuration info.

Example:
```bash
curl http://localhost:5000/api/health
```

## Configuration Options

Edit `.env` to customize:

**GitLab Configuration:**
- `GITLAB_URL`: Your GitLab instance URL (default: https://gitlab.com)
- `GITLAB_PROJECT_ID`: Your project ID or path
- `GITLAB_PRIVATE_TOKEN`: Your personal access token

**ClickUp Configuration (Optional):**
- `CLICKUP_API_TOKEN`: Your ClickUp API token (optional - enables ClickUp task integration)

**Application Configuration:**
- `PORT`: Application port (default: 5000)
- `DEBUG`: Enable debug mode (default: False)

## Project Structure

```
ccooky/
├── app.py                  # FastAPI application
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment configuration
├── .gitignore             # Git ignore file
├── README.md              # This file
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
- **APIs**:
  - GitLab REST API v4
  - ClickUp REST API v2 (optional)
- **HTTP Client**: requests library

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
