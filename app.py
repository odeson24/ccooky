from flask import Flask, render_template, jsonify, request
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# GitLab configuration
GITLAB_URL = os.getenv('GITLAB_URL', 'https://gitlab.com')
GITLAB_PROJECT_ID = os.getenv('GITLAB_PROJECT_ID')
GITLAB_PRIVATE_TOKEN = os.getenv('GITLAB_PRIVATE_TOKEN')


@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')


@app.route('/api/merge-requests')
def get_merge_requests():
    """Fetch merge requests from GitLab API"""
    try:
        # Check configuration
        if not GITLAB_PROJECT_ID or not GITLAB_PRIVATE_TOKEN:
            return jsonify({
                'error': 'GitLab configuration missing',
                'message': 'Please set GITLAB_PROJECT_ID and GITLAB_PRIVATE_TOKEN in .env file'
            }), 400

        # Get query parameters
        state = request.args.get('state', 'opened')
        per_page = request.args.get('per_page', 20, type=int)
        page = request.args.get('page', 1, type=int)

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
        return jsonify(response.json())

    except requests.exceptions.HTTPError as e:
        app.logger.error(f'GitLab API error: {e}')
        return jsonify({
            'error': 'Failed to fetch merge requests from GitLab',
            'status_code': e.response.status_code,
            'details': e.response.text
        }), e.response.status_code

    except requests.exceptions.RequestException as e:
        app.logger.error(f'Request error: {e}')
        return jsonify({
            'error': 'Failed to connect to GitLab',
            'details': str(e)
        }), 500

    except Exception as e:
        app.logger.error(f'Unexpected error: {e}')
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    configured = bool(GITLAB_PROJECT_ID and GITLAB_PRIVATE_TOKEN)
    return jsonify({
        'status': 'ok',
        'configured': configured,
        'gitlab_url': GITLAB_URL,
        'project_id': GITLAB_PROJECT_ID if configured else 'Not configured'
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    print(f"Starting GitLab MR Lister on http://localhost:{port}")
    print(f"GitLab URL: {GITLAB_URL}")
    print(f"Project ID: {GITLAB_PROJECT_ID or 'Not configured'}")
    print(f"Token configured: {'Yes' if GITLAB_PRIVATE_TOKEN else 'No'}")

    app.run(host='0.0.0.0', port=port, debug=debug)
