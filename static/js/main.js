/**
 * Main JavaScript for audio transcription application.
 */

// Application state
const appState = {
    files: [],
    processingMode: 'one-by-one',
    processing: false,
    currentProcessingIndex: -1
};

// DOM elements
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const fileList = document.getElementById('fileList');
const clearAllBtn = document.getElementById('clearAllBtn');
const modeButtons = document.querySelectorAll('.mode-btn');
const statusMessage = document.getElementById('statusMessage');
const progressBar = document.getElementById('progressBar');
const resultsSection = document.getElementById('resultsSection');
const resultsContainer = document.getElementById('resultsContainer');
const logContainer = document.getElementById('logContainer');
const refreshLogBtn = document.getElementById('refreshLogBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    checkServerStatus();
    loadLog();
});

function initializeEventListeners() {
    // File input
    fileInput.addEventListener('change', handleFileSelect);
    
    // Upload area
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('drop', handleDrop);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    
    // Mode buttons
    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            modeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            appState.processingMode = btn.dataset.mode;
        });
    });
    
    // Clear all button
    clearAllBtn.addEventListener('click', clearAllFiles);
    
    // Refresh log
    refreshLogBtn.addEventListener('click', loadLog);
}

function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const files = Array.from(e.dataTransfer.files);
    addFiles(files);
}

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    addFiles(files);
}

function addFiles(files) {
    const audioFiles = files.filter(file => {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        return file.type.startsWith('audio/') || file.type.startsWith('video/') || 
               ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm', '.mp4'].includes(ext);
    });
    
    audioFiles.forEach(file => {
        if (!appState.files.find(f => f.name === file.name && f.size === file.size)) {
            appState.files.push({
                file: file,
                name: file.name,
                size: file.size,
                status: 'pending',
                transcription: null,
                error: null
            });
        }
    });
    
    updateFileList();
}

function updateFileList() {
    fileList.innerHTML = '';
    clearAllBtn.style.display = appState.files.length > 0 ? 'block' : 'none';
    
    if (appState.files.length === 0) {
        fileList.innerHTML = '<p class="empty-message">No files selected</p>';
        return;
    }
    
    appState.files.forEach((fileData, index) => {
        const fileItem = createFileItem(fileData, index);
        fileList.appendChild(fileItem);
    });
}

function createFileItem(fileData, index) {
    const item = document.createElement('div');
    item.className = `file-item ${fileData.status}`;
    
    const statusIcon = getStatusIcon(fileData.status);
    const statusText = getStatusText(fileData.status);
    
    // Progress bar HTML (if processing)
    let progressHtml = '';
    if (fileData.status === 'processing' && fileData.progress !== undefined) {
        const progressPercent = Math.round(fileData.progress || 0);
        let progressText = `${progressPercent}%`;
        if (fileData.estimatedRemaining !== null && fileData.estimatedRemaining > 0) {
            progressText += ` • ~${formatTime(fileData.estimatedRemaining)} remaining`;
        } else if (fileData.elapsedTime > 0) {
            progressText += ` • ${formatTime(fileData.elapsedTime)} elapsed`;
        }
        progressHtml = `
            <div class="file-progress-info">
                <div class="file-progress-bar-container">
                    <div class="file-progress-bar" style="width: ${progressPercent}%"></div>
                </div>
                <div class="file-progress-text">${progressText}</div>
            </div>
        `;
    }
    
    item.innerHTML = `
        <div class="file-info">
            <div class="file-icon">${statusIcon}</div>
            <div class="file-details">
                <div class="file-name">${escapeHtml(fileData.name)}</div>
                <div class="file-meta">
                    <span>${formatFileSize(fileData.size)}</span>
                    ${fileData.audioDuration ? `<span>Duration: ${formatTime(fileData.audioDuration)}</span>` : ''}
                    <span class="status-badge ${fileData.status}">${statusText}</span>
                </div>
            </div>
        </div>
        <div class="file-actions">
            ${progressHtml}
            ${fileData.status === 'pending' && !appState.processing ? 
                `<button class="btn-process" onclick="processFile(${index})">Process</button>` : ''}
            ${fileData.status === 'processing' ? 
                `<div class="spinner"></div>` : ''}
            ${fileData.status === 'success' ? 
                `<button class="btn-view" onclick="viewTranscription(${index})">View</button>
                 <button class="btn-download" onclick="downloadTranscription(${index})">Download</button>` : ''}
            ${fileData.status === 'error' ? 
                `<button class="btn-retry" onclick="processFile(${index})">Retry</button>` : ''}
            <button class="btn-remove" onclick="removeFile(${index})" title="Remove">×</button>
        </div>
    `;
    
    return item;
}

function getStatusIcon(status) {
    const icons = {
        'pending': '⏳',
        'processing': '🔄',
        'success': '✅',
        'error': '❌'
    };
    return icons[status] || '⏳';
}

function getStatusText(status) {
    const texts = {
        'pending': 'Pending',
        'processing': 'Processing...',
        'success': 'Completed',
        'error': 'Error'
    };
    return texts[status] || 'Pending';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function processFile(index) {
    // If in batch mode, process all files instead
    if (appState.processingMode === 'batch') {
        processBatch();
        return;
    }
    
    if (appState.processing) return;
    
    const fileData = appState.files[index];
    if (fileData.status === 'processing') return;
    
    appState.processing = true;
    appState.currentProcessingIndex = index;
    fileData.status = 'processing';
    updateFileList();
    updateStatus('Uploading file...', 'info');
    
    try {
        // Upload file
        const formData = new FormData();
        formData.append('file', fileData.file);
        
        const uploadResponse = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            throw new Error('Upload failed');
        }
        
        const uploadData = await uploadResponse.json();
        
        // Check if already processed
        if (uploadData.already_processed && uploadData.log_entry) {
            // Fetch the actual transcription text from the server
            try {
                const transcribeResponse = await fetch('/transcribe', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        filename: uploadData.filename
                    })
                });
                
                if (transcribeResponse.ok) {
                    const transcribeData = await transcribeResponse.json();
                    if (transcribeData.status === 'success') {
                        fileData.status = 'success';
                        fileData.transcription = transcribeData.transcription;
                        fileData.language = transcribeData.language;
                        fileData.text_file = transcribeData.text_file;
                        fileData.json_file = transcribeData.json_file;
                        updateFileList();
                        updateStatus('File already processed', 'success');
                        appState.processing = false;
                        return;
                    }
                }
            } catch (error) {
                console.error('Error fetching already processed transcription:', error);
                // Fall through to process normally
            }
        }
        
        updateStatus('Transcribing...', 'info');
        showProgress(true);
        
        // Start transcription in background
        const transcribePromise = fetch('/transcribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: uploadData.filename
            })
        });
        
        // Poll for progress updates
        const progressInterval = setInterval(async () => {
            try {
                const progressResponse = await fetch(`/progress/${uploadData.filename}`);
                if (progressResponse.ok) {
                    const progressData = await progressResponse.json();
                    updateFileProgress(index, progressData);
                }
            } catch (error) {
                // Ignore progress fetch errors
            }
        }, 500); // Poll every 500ms
        
        // Wait for transcription to complete
        let transcribeResponse;
        try {
            transcribeResponse = await transcribePromise;
        } finally {
            // Clear progress polling
            clearInterval(progressInterval);
        }
        
        if (!transcribeResponse.ok) {
            const errorData = await transcribeResponse.json();
            throw new Error(errorData.error || 'Transcription failed');
        }
        
        const transcribeData = await transcribeResponse.json();
        
        if (transcribeData.status === 'success') {
            fileData.status = 'success';
            fileData.transcription = transcribeData.transcription;
            fileData.language = transcribeData.language;
            fileData.text_file = transcribeData.text_file;
            fileData.json_file = transcribeData.json_file;
            updateStatus('Transcription completed!', 'success');
        } else {
            throw new Error(transcribeData.error || 'Transcription failed');
        }
        
    } catch (error) {
        fileData.status = 'error';
        fileData.error = error.message;
        updateStatus(`Error: ${error.message}`, 'error');
    } finally {
        appState.processing = false;
        appState.currentProcessingIndex = -1;
        showProgress(false);
        updateFileList();
        loadLog();
    }
}

async function processBatch() {
    if (appState.processing || appState.files.length === 0) return;
    
    appState.processing = true;
    updateStatus('Starting batch processing...', 'info');
    showProgress(true);
    
    const pendingFiles = appState.files.filter(f => f.status === 'pending');
    
    // Upload all files first
    const uploadPromises = pendingFiles.map(async (fileData, index) => {
        const formData = new FormData();
        formData.append('file', fileData.file);
        
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Upload failed');
            }
            
            return await response.json();
        } catch (error) {
            fileData.status = 'error';
            fileData.error = error.message;
            return null;
        }
    });
    
    const uploadResults = await Promise.all(uploadPromises);
    const filenames = uploadResults.filter(r => r !== null).map(r => r.filename);
    
    if (filenames.length === 0) {
        updateStatus('No files to process', 'error');
        appState.processing = false;
        showProgress(false);
        updateFileList();
        return;
    }
    
    // Update file statuses
    uploadResults.forEach((result, index) => {
        if (result) {
            const fileData = pendingFiles[index];
            if (result.already_processed) {
                fileData.status = 'success';
                fileData.transcription = result.log_entry;
            } else {
                fileData.status = 'processing';
            }
        }
    });
    updateFileList();
    
    // Batch transcribe with progress tracking
    try {
        updateStatus('Transcribing files...', 'info');
        
        // Start batch transcription
        const batchPromise = fetch('/transcribe-batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filenames: filenames
            })
        });
        
        // Poll for progress on all files
        const batchProgressInterval = setInterval(async () => {
            for (let i = 0; i < filenames.length; i++) {
                const filename = filenames[i];
                const fileData = appState.files.find(f => 
                    f.name === filename || filename.includes(f.name)
                );
                if (fileData && fileData.status === 'processing') {
                    try {
                        const progressResponse = await fetch(`/progress/${filename}`);
                        if (progressResponse.ok) {
                            const progressData = await progressResponse.json();
                            const fileIndex = appState.files.indexOf(fileData);
                            if (fileIndex >= 0) {
                                updateFileProgress(fileIndex, progressData);
                            }
                        }
                    } catch (error) {
                        // Ignore progress fetch errors
                    }
                }
            }
        }, 1000); // Poll every second for batch
        
        // Wait for batch to complete
        let response;
        try {
            response = await batchPromise;
        } finally {
            clearInterval(batchProgressInterval);
        }
        
        if (!response.ok) {
            throw new Error('Batch transcription failed');
        }
        
        const data = await response.json();
        
        // Update file statuses based on results
        data.results.forEach(result => {
            const fileData = appState.files.find(f => 
                f.name === result.filename || result.filename.includes(f.name)
            );
            
            if (fileData) {
                if (result.status === 'success') {
                    fileData.status = 'success';
                    fileData.transcription = result.transcription;
                    fileData.language = result.language;
                    fileData.text_file = result.text_file;
                    fileData.json_file = result.json_file;
                } else if (result.status === 'error') {
                    fileData.status = 'error';
                    fileData.error = result.error;
                }
            }
        });
        
        updateStatus(
            `Batch processing completed: ${data.successful} successful, ${data.errors} errors, ${data.skipped} skipped`,
            data.errors > 0 ? 'warning' : 'success'
        );
        
    } catch (error) {
        updateStatus(`Batch processing error: ${error.message}`, 'error');
    } finally {
        appState.processing = false;
        showProgress(false);
        updateFileList();
        loadLog();
    }
}

function removeFile(index) {
    appState.files.splice(index, 1);
    updateFileList();
}

function clearAllFiles() {
    if (confirm('Clear all files?')) {
        appState.files = [];
        updateFileList();
        resultsSection.style.display = 'none';
    }
}

function viewTranscription(index) {
    const fileData = appState.files[index];
    if (!fileData.transcription) return;
    
    const transcription = typeof fileData.transcription === 'string' 
        ? fileData.transcription 
        : fileData.transcription.transcription || fileData.transcription.text || '';
    
    resultsSection.style.display = 'block';
    resultsContainer.innerHTML = `
        <div class="result-item">
            <h3>${escapeHtml(fileData.name)}</h3>
            ${fileData.language ? `<p class="language-info">Language: ${fileData.language}</p>` : ''}
            <div class="transcription-text">${escapeHtml(transcription).replace(/\n/g, '<br>')}</div>
            <div class="result-actions">
                <button class="btn-download" onclick="downloadTranscription(${index})">Download Text</button>
                ${fileData.json_file ? `<button class="btn-download" onclick="downloadJSON(${index})">Download JSON</button>` : ''}
            </div>
        </div>
    `;
    
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
}

function downloadTranscription(index) {
    const fileData = appState.files[index];
    
    // Use the filename from server response if available, otherwise construct from original name
    let filename;
    if (fileData.text_file) {
        // Extract filename from server path (e.g., "/app/outputs/transcriptions/file.txt" -> "file.txt")
        const pathParts = fileData.text_file.split('/');
        filename = pathParts[pathParts.length - 1];
    } else {
        // Fallback: construct from original filename
        filename = fileData.name.replace(/\.[^/.]+$/, '') + '.txt';
    }
    
    if (fileData.text_file) {
        // Download from server - use the actual filename from server
        window.open(`/download/${encodeURIComponent(filename)}`, '_blank');
    } else {
        // Create and download
        const transcription = typeof fileData.transcription === 'string' 
            ? fileData.transcription 
            : fileData.transcription.transcription || fileData.transcription.text || '';
        
        const blob = new Blob([transcription], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }
}

function downloadJSON(index) {
    const fileData = appState.files[index];
    
    // Use the filename from server response if available
    let filename;
    if (fileData.json_file) {
        // Extract filename from server path
        const pathParts = fileData.json_file.split('/');
        filename = pathParts[pathParts.length - 1];
    } else {
        // Fallback: construct from original filename
        filename = fileData.name.replace(/\.[^/.]+$/, '') + '.json';
    }
    
    if (fileData.json_file) {
        window.open(`/download/${encodeURIComponent(filename)}`, '_blank');
    }
}

function updateFileProgress(fileIndex, progressData) {
    const fileData = appState.files[fileIndex];
    if (!fileData) return;
    
    // Update file data with progress
    fileData.progress = progressData.progress || 0;
    fileData.progressMessage = progressData.message || '';
    fileData.elapsedTime = progressData.elapsed_time || 0;
    fileData.estimatedRemaining = progressData.estimated_remaining;
    fileData.audioDuration = progressData.audio_duration;
    
    // Update the file item in the UI
    const fileItems = fileList.querySelectorAll('.file-item');
    if (fileItems[fileIndex]) {
        const fileItem = fileItems[fileIndex];
        const progressInfo = fileItem.querySelector('.file-progress-info');
        
        if (progressInfo) {
            // Update existing progress info
            const progressBar = progressInfo.querySelector('.file-progress-bar');
            const progressText = progressInfo.querySelector('.file-progress-text');
            
            if (progressBar) {
                progressBar.style.width = `${fileData.progress}%`;
            }
            
            if (progressText) {
                let text = `${Math.round(fileData.progress)}%`;
                if (fileData.estimatedRemaining !== null && fileData.estimatedRemaining > 0) {
                    const remaining = formatTime(fileData.estimatedRemaining);
                    text += ` • ~${remaining} remaining`;
                } else if (fileData.elapsedTime > 0) {
                    const elapsed = formatTime(fileData.elapsedTime);
                    text += ` • ${elapsed} elapsed`;
                }
                progressText.textContent = text;
            }
        } else {
            // Create progress info if it doesn't exist
            const progressDiv = document.createElement('div');
            progressDiv.className = 'file-progress-info';
            progressDiv.innerHTML = `
                <div class="file-progress-bar-container">
                    <div class="file-progress-bar" style="width: ${fileData.progress}%"></div>
                </div>
                <div class="file-progress-text">${Math.round(fileData.progress)}%</div>
            `;
            
            const fileActions = fileItem.querySelector('.file-actions');
            if (fileActions) {
                fileActions.insertBefore(progressDiv, fileActions.firstChild);
            }
        }
    }
    
    // Update status message
    if (fileData.progressMessage) {
        updateStatus(fileData.progressMessage, 'info');
    }
}

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

function updateStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.className = `status-message ${type}`;
}

function showProgress(show) {
    progressBar.style.display = show ? 'block' : 'none';
    if (show) {
        progressBar.querySelector('.progress-fill').style.animation = 'progress 2s ease-in-out infinite';
    }
}

async function checkServerStatus() {
    try {
        const response = await fetch('/status');
        const data = await response.json();
        
        if (data.whisper_loaded) {
            updateStatus(`Server ready (Model: ${data.model_size})`, 'success');
        } else {
            updateStatus('Server ready, but Whisper model not loaded', 'warning');
        }
    } catch (error) {
        updateStatus('Cannot connect to server', 'error');
    }
}

async function loadLog() {
    try {
        const response = await fetch('/log');
        const data = await response.json();
        
        if (data.log.length === 0) {
            logContainer.innerHTML = '<p class="empty-message">No log entries yet</p>';
            return;
        }
        
        logContainer.innerHTML = data.log.reverse().map(entry => `
            <div class="log-entry ${entry.status}">
                <div class="log-header">
                    <span class="log-filename">${escapeHtml(entry.filename)}</span>
                    <span class="log-status ${entry.status}">${entry.status}</span>
                </div>
                <div class="log-details">
                    <span>${new Date(entry.timestamp).toLocaleString()}</span>
                    ${entry.language_detected ? `<span>Language: ${entry.language_detected}</span>` : ''}
                    ${entry.model_used ? `<span>Model: ${entry.model_used}</span>` : ''}
                </div>
                ${entry.error ? `<div class="log-error">Error: ${escapeHtml(entry.error)}</div>` : ''}
            </div>
        `).join('');
    } catch (error) {
        logContainer.innerHTML = `<p class="error-message">Error loading log: ${error.message}</p>`;
    }
}

// Update batch process button visibility and state
function updateBatchProcessButton() {
    const batchBtn = document.getElementById('batchProcessBtn');
    if (batchBtn) {
        if (appState.files.length > 0) {
            batchBtn.style.display = 'inline-block';
            batchBtn.disabled = appState.processing;
        } else {
            batchBtn.style.display = 'none';
        }
    }
}

// Initialize batch button
const batchProcessBtn = document.getElementById('batchProcessBtn');
if (batchProcessBtn) {
    batchProcessBtn.addEventListener('click', processBatch);
}

// Update batch button when file list changes
const originalUpdateFileList = updateFileList;
updateFileList = function() {
    originalUpdateFileList();
    updateBatchProcessButton();
};
