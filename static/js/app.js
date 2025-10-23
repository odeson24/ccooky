// DOM elements
const stateFilter = document.getElementById('state-filter');
const refreshBtn = document.getElementById('refresh-btn');
const clearCacheBtn = document.getElementById('clear-cache-btn');
const loading = document.getElementById('loading');
const errorDiv = document.getElementById('error');
const mrList = document.getElementById('mr-list');
const projectInfo = document.getElementById('project-info');
const connectionStatus = document.getElementById('connection-status');
const cacheStatus = document.getElementById('cache-status');

// State
let currentState = 'opened';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadMergeRequests();

    // Event listeners
    stateFilter.addEventListener('change', (e) => {
        currentState = e.target.value;
        loadMergeRequests();
    });

    refreshBtn.addEventListener('click', () => {
        loadMergeRequests(true);  // Force refresh
    });

    if (clearCacheBtn) {
        clearCacheBtn.addEventListener('click', async () => {
            await clearCache();
        });
    }
});

// Check API health and configuration
async function checkHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        if (data.configured) {
            connectionStatus.textContent = 'Connected';
            connectionStatus.classList.add('connected');
            connectionStatus.classList.remove('error');
            projectInfo.textContent = `Project: ${data.project_id}`;

            // Show cache stats if available
            if (data.cache_stats && cacheStatus) {
                const stats = data.cache_stats;
                cacheStatus.textContent = `Cache: ${stats.mr_cache_count} MRs, ${stats.clickup_cache_count} tasks (TTL: ${stats.mr_ttl_minutes}m)`;
            }
        } else {
            connectionStatus.textContent = 'Not Configured';
            connectionStatus.classList.add('error');
            connectionStatus.classList.remove('connected');
            showError('GitLab is not configured. Please set up your .env file.');
        }
    } catch (error) {
        connectionStatus.textContent = 'Connection Error';
        connectionStatus.classList.add('error');
        connectionStatus.classList.remove('connected');
        console.error('Health check failed:', error);
    }
}

// Load merge requests from API
async function loadMergeRequests(forceRefresh = false) {
    showLoading();
    hideError();

    try {
        const url = `/api/merge-requests?state=${currentState}&per_page=50${forceRefresh ? '&force_refresh=true' : ''}`;
        const response = await fetch(url);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail?.error || errorData.error || 'Failed to fetch merge requests');
        }

        const responseData = await response.json();

        // Handle new response format with metadata
        const mergeRequests = responseData.data || responseData;
        const fromCache = responseData.from_cache || false;

        // Update cache status indicator
        if (cacheStatus && responseData.from_cache !== undefined) {
            const cacheIndicator = fromCache ? ' (cached)' : ' (fresh)';
            const currentText = cacheStatus.textContent;
            if (currentText) {
                cacheStatus.textContent = currentText.replace(/ \((cached|fresh)\)$/, '') + cacheIndicator;
            }
        }

        displayMergeRequests(mergeRequests);

        // Refresh health check to update cache stats
        checkHealth();
    } catch (error) {
        showError(error.message);
        console.error('Error loading merge requests:', error);
    } finally {
        hideLoading();
    }
}

// Clear cache
async function clearCache() {
    try {
        showLoading();
        const response = await fetch('/api/cache/clear', { method: 'POST' });

        if (!response.ok) {
            throw new Error('Failed to clear cache');
        }

        // Reload merge requests after clearing cache
        await loadMergeRequests(true);

        // Show success message briefly
        const successMsg = document.createElement('div');
        successMsg.className = 'success-message';
        successMsg.textContent = 'Cache cleared successfully';
        document.querySelector('.container').prepend(successMsg);
        setTimeout(() => successMsg.remove(), 3000);

    } catch (error) {
        showError('Failed to clear cache: ' + error.message);
        console.error('Error clearing cache:', error);
    } finally {
        hideLoading();
    }
}

// Display merge requests
function displayMergeRequests(mergeRequests) {
    mrList.innerHTML = '';

    if (!mergeRequests || mergeRequests.length === 0) {
        mrList.innerHTML = `
            <div class="empty-state">
                <h2>No merge requests found</h2>
                <p>There are no ${currentState} merge requests in this project.</p>
            </div>
        `;
        return;
    }

    mergeRequests.forEach(mr => {
        const mrElement = createMergeRequestElement(mr);
        mrList.appendChild(mrElement);
    });
}

// Create merge request element
function createMergeRequestElement(mr) {
    const div = document.createElement('div');
    div.className = 'mr-item';

    const createdDate = new Date(mr.created_at).toLocaleDateString();
    const updatedDate = new Date(mr.updated_at).toLocaleDateString();

    // Format description
    const description = mr.description
        ? `<div class="mr-description">${escapeHtml(mr.description.substring(0, 200))}${mr.description.length > 200 ? '...' : ''}</div>`
        : '';

    // Format labels
    const labels = mr.labels && mr.labels.length > 0
        ? `<div class="mr-labels">
            ${mr.labels.map(label => `<span class="mr-label" style="background-color: #6b7280;">${escapeHtml(label)}</span>`).join('')}
           </div>`
        : '';

    // Format ClickUp task information
    let clickupTask = '';
    if (mr.clickup_task) {
        const task = mr.clickup_task;
        const taskTags = task.tags && task.tags.length > 0
            ? `<div class="clickup-tags">
                ${task.tags.map(tag => `<span class="clickup-tag">${escapeHtml(tag)}</span>`).join('')}
               </div>`
            : '';

        const priorityText = task.priority ? `Priority ${task.priority}` : '';

        clickupTask = `
            <div class="clickup-task">
                <div class="clickup-header">
                    <strong>ClickUp Task:</strong>
                    <a href="${task.url}" target="_blank" rel="noopener noreferrer" class="clickup-link">
                        ${escapeHtml(task.name)}
                    </a>
                </div>
                <div class="clickup-meta">
                    <span class="clickup-status">${escapeHtml(task.status)}</span>
                    ${priorityText ? `<span class="clickup-priority">${escapeHtml(priorityText)}</span>` : ''}
                </div>
                ${taskTags}
            </div>
        `;
    } else if (mr.clickup_task_id) {
        // Task ID found but couldn't fetch task details
        clickupTask = `
            <div class="clickup-task">
                <div class="clickup-header">
                    <strong>ClickUp Task ID:</strong> CU-${escapeHtml(mr.clickup_task_id)}
                    <span class="clickup-error">(Could not load task details)</span>
                </div>
            </div>
        `;
    }

    div.innerHTML = `
        <div class="mr-header">
            <div>
                <div class="mr-title">
                    <a href="${mr.web_url}" target="_blank" rel="noopener noreferrer">
                        ${escapeHtml(mr.title)}
                    </a>
                </div>
                <div class="mr-id">!${mr.iid}</div>
            </div>
            <span class="mr-state ${mr.state}">${mr.state.toUpperCase()}</span>
        </div>
        <div class="mr-meta">
            <div class="mr-meta-item">
                <span>Author:</span>
                <span class="mr-author">${escapeHtml(mr.author.name)}</span>
            </div>
            <div class="mr-meta-item">
                <span>Created:</span>
                <span>${createdDate}</span>
            </div>
            <div class="mr-meta-item">
                <span>Updated:</span>
                <span>${updatedDate}</span>
            </div>
            ${mr.source_branch ? `
            <div class="mr-meta-item">
                <span>Branch:</span>
                <span>${escapeHtml(mr.source_branch)}</span>
            </div>
            ` : ''}
        </div>
        ${description}
        ${clickupTask}
        ${labels}
    `;

    return div;
}

// Utility functions
function showLoading() {
    loading.classList.remove('hidden');
    mrList.classList.add('hidden');
}

function hideLoading() {
    loading.classList.add('hidden');
    mrList.classList.remove('hidden');
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

function hideError() {
    errorDiv.classList.add('hidden');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
