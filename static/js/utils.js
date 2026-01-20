/**
 * Shared utility functions for Katha Transcription Application.
 * 
 * This module provides common functions used across multiple pages.
 */

/**
 * Escape HTML special characters to prevent XSS.
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text safe for HTML insertion
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format file size in human-readable format.
 * @param {number} bytes - File size in bytes
 * @returns {string} - Formatted size string (e.g., "1.5 MB")
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format time duration in human-readable format.
 * @param {number} seconds - Duration in seconds
 * @returns {string} - Formatted time string (e.g., "2m 30s")
 */
function formatTime(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.round(seconds % 60);
        return `${mins}m ${secs}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${mins}m`;
    }
}

/**
 * Create export dropdown HTML for a given filename.
 * @param {string} filename - The filename for export
 * @param {string} selectId - Unique ID for the select element
 * @returns {string} - HTML string for the export dropdown
 */
function createExportDropdown(filename, selectId) {
    const safeFilename = escapeHtml(filename);
    return `
        <div class="export-dropdown-container">
            <select id="${selectId}" class="format-select">
                <optgroup label="Simple Downloads">
                    <option value="txt">Plain Text (.txt)</option>
                    <option value="json-raw">Raw JSON (.json)</option>
                </optgroup>
                <optgroup label="Formatted Documents">
                    <option value="json">Structured JSON</option>
                    <option value="markdown">Markdown (.md)</option>
                    <option value="html">HTML Document</option>
                    <option value="docx">Word Document (.docx)</option>
                    <option value="pdf">PDF Document</option>
                </optgroup>
            </select>
            <button class="btn-primary export-btn" data-filename="${safeFilename}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                Download
            </button>
        </div>
    `;
}

/**
 * Create export help text HTML.
 * @returns {string} - HTML string for export help section
 */
function createExportHelpText() {
    return `
        <div class="export-help">
            <strong>Export Options:</strong>
            <ul>
                <li><strong>Plain Text / Raw JSON:</strong> Simple output files with just the transcription</li>
                <li><strong>Formatted Documents:</strong> Rich documents with sections, scripture quotes, and metadata</li>
            </ul>
        </div>
    `;
}

/**
 * Get confidence badge class based on confidence value.
 * @param {number} confidence - Confidence value (0-1)
 * @returns {string} - CSS class name for confidence level
 */
function getConfidenceClass(confidence) {
    if (confidence >= 0.8) return 'confidence-high';
    if (confidence >= 0.6) return 'confidence-medium';
    return 'confidence-low';
}

/**
 * Get status icon for file processing status.
 * @param {string} status - Status string ('pending', 'processing', 'success', 'error')
 * @returns {string} - Emoji icon
 */
function getStatusIcon(status) {
    const icons = {
        'pending': '⏳',
        'processing': '🔄',
        'success': '✅',
        'error': '❌'
    };
    return icons[status] || '⏳';
}

/**
 * Get human-readable status text.
 * @param {string} status - Status string
 * @returns {string} - Human-readable status
 */
function getStatusText(status) {
    const texts = {
        'pending': 'Pending',
        'processing': 'Processing...',
        'success': 'Completed',
        'error': 'Error'
    };
    return texts[status] || 'Pending';
}

/**
 * Export document via API with error handling.
 * @param {string} filename - The filename to export
 * @param {string} format - Export format (txt, json, markdown, etc.)
 * @param {HTMLButtonElement} [exportBtn] - Optional button to show loading state
 * @returns {Promise<void>}
 */
async function exportDocument(filename, format, exportBtn) {
    if (!format) {
        alert('Please select an export format');
        return;
    }
    
    const originalBtnContent = exportBtn ? exportBtn.innerHTML : null;
    
    if (exportBtn) {
        exportBtn.disabled = true;
        exportBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 6v6l4 2"></path>
            </svg>
            Exporting...
        `;
    }
    
    const extensionMap = {
        'txt': '.txt',
        'json-raw': '.json',
        'json': '.json',
        'markdown': '.md',
        'html': '.html',
        'docx': '.docx',
        'pdf': '.pdf'
    };
    const extension = extensionMap[format] || '.txt';
    const downloadFilename = filename.replace(/\.[^/.]+$/, '') + extension;
    const exportUrl = `/export/${encodeURIComponent(filename)}/${format}`;
    
    try {
        const response = await fetch(exportUrl);
        
        if (!response.ok) {
            let errorMessage = `Export failed (${response.status})`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.error || errorMessage;
                if (errorData.hint) {
                    errorMessage += ` - ${errorData.hint}`;
                }
            } catch (e) {
                // Response wasn't JSON, use default message
            }
            throw new Error(errorMessage);
        }
        
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = downloadFilename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        
        setTimeout(() => {
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }, 100);
        
        if (exportBtn) {
            exportBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                Downloaded!
            `;
            exportBtn.style.background = 'var(--color-success)';
            
            setTimeout(() => {
                exportBtn.disabled = false;
                exportBtn.innerHTML = originalBtnContent;
                exportBtn.style.background = '';
            }, 2000);
        }
        
        return true;
        
    } catch (error) {
        console.error('Export error:', error);
        
        if (exportBtn) {
            exportBtn.disabled = false;
            exportBtn.innerHTML = originalBtnContent;
            exportBtn.style.background = '';
        }
        
        throw error;
    }
}

// Export functions for use in other scripts
window.KathaUtils = {
    escapeHtml,
    formatFileSize,
    formatTime,
    createExportDropdown,
    createExportHelpText,
    getConfidenceClass,
    getStatusIcon,
    getStatusText,
    exportDocument
};

