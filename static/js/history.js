/**
 * History page JavaScript for viewing and downloading transcriptions.
 */

const historyContainer = document.getElementById('historyContainer');
const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    if (refreshHistoryBtn) {
        refreshHistoryBtn.addEventListener('click', loadHistory);
    }
});

async function loadHistory() {
    try {
        const response = await fetch('/log');
        const data = await response.json();
        
        if (data.log.length === 0) {
            historyContainer.innerHTML = '<p class="empty-message">No transcriptions yet. Process some files to see them here.</p>';
            return;
        }
        
        // Sort by timestamp (newest first)
        const sortedLog = data.log.slice().reverse();
        
        historyContainer.innerHTML = sortedLog.map(entry => {
            const timestamp = new Date(entry.timestamp);
            const hasFiles = entry.text_file || entry.json_file;
            
            return `
                <div class="history-entry ${entry.status}">
                    <div class="history-header">
                        <div class="history-file-info">
                            <span class="history-filename">${escapeHtml(entry.filename)}</span>
                            <span class="history-timestamp">${timestamp.toLocaleString()}</span>
                        </div>
                        <span class="history-status ${entry.status}">${entry.status}</span>
                    </div>
                    <div class="history-details">
                        ${entry.language_detected ? `<span><strong>Language:</strong> ${entry.language_detected}</span>` : ''}
                        ${entry.model_used ? `<span><strong>Model:</strong> ${entry.model_used}</span>` : ''}
                    </div>
                    ${entry.error ? `<div class="history-error">Error: ${escapeHtml(entry.error)}</div>` : ''}
                    ${hasFiles && entry.status === 'success' ? `
                        <div class="history-actions">
                            <div class="export-dropdown-container">
                                <select class="format-select" id="format-select-${escapeHtml(entry.filename).replace(/[^a-zA-Z0-9]/g, '_')}">
                                    <option value="">Export Format...</option>
                                    <option value="txt">Plain Text (.txt)</option>
                                    <option value="json-raw">Raw JSON (.json)</option>
                                    <option value="json">Structured JSON</option>
                                    <option value="markdown">Markdown (.md)</option>
                                    <option value="html">HTML Document</option>
                                    <option value="docx">Word Document (.docx)</option>
                                    <option value="pdf">PDF Document</option>
                                </select>
                                <button class="btn-primary export-btn" onclick="exportFromHistory('${escapeHtml(entry.filename)}', document.getElementById('format-select-${escapeHtml(entry.filename).replace(/[^a-zA-Z0-9]/g, '_')}').value)">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                        <polyline points="7 10 12 15 17 10"></polyline>
                                        <line x1="12" y1="15" x2="12" y2="3"></line>
                                    </svg>
                                    Export
                                </button>
                            </div>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
    } catch (error) {
        historyContainer.innerHTML = `<p class="error-message">Error loading history: ${error.message}</p>`;
    }
}

function exportFromHistory(filename, format) {
    if (!format) {
        alert('Please select an export format');
        return;
    }
    
    // Direct export via URL
    window.location.href = `/export/${encodeURIComponent(filename)}/${format}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
