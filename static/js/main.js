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
const detailedProgressSection = document.getElementById('detailedProgressSection');
const detailedProgressContainer = document.getElementById('detailedProgressContainer');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    initializeAdvancedOptions();
    checkServerStatus();
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
    
    // Advanced options toggle
    const toggleOptionsBtn = document.getElementById('toggleOptionsBtn');
    if (toggleOptionsBtn) {
        toggleOptionsBtn.addEventListener('click', toggleAdvancedOptions);
    }
    
    // Reset options button
    const resetOptionsBtn = document.getElementById('resetOptionsBtn');
    if (resetOptionsBtn) {
        resetOptionsBtn.addEventListener('click', resetAdvancedOptions);
    }
    
    // VAD aggressiveness slider value display
    const vadAggressiveness = document.getElementById('vadAggressiveness');
    if (vadAggressiveness) {
        vadAggressiveness.addEventListener('input', (e) => {
            const valueDisplay = document.getElementById('vadAggressivenessValue');
            if (valueDisplay) {
                valueDisplay.textContent = e.target.value;
            }
        });
    }
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

// Advanced Options Functions
function initializeAdvancedOptions() {
    // Load saved preferences from localStorage
    const savedOptions = localStorage.getItem('transcriptionOptions');
    if (savedOptions) {
        try {
            const options = JSON.parse(savedOptions);
            applyAdvancedOptions(options);
        } catch (e) {
            console.error('Failed to load saved options:', e);
        }
    }
}

function toggleAdvancedOptions() {
    const panel = document.getElementById('advancedOptionsPanel');
    const toggleBtn = document.getElementById('toggleOptionsBtn');
    
    if (!panel || !toggleBtn) return;
    
    const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
    panel.style.display = isExpanded ? 'none' : 'block';
    toggleBtn.setAttribute('aria-expanded', !isExpanded);
    
    const toggleText = toggleBtn.querySelector('.toggle-text');
    if (toggleText) {
        toggleText.textContent = isExpanded ? 'Show Options' : 'Hide Options';
    }
}

function collectAdvancedOptions() {
    return {
        // Denoising options
        denoiseEnabled: document.getElementById('denoiseEnabled')?.checked || false,
        denoiseBackend: document.getElementById('denoiseBackend')?.value || 'noisereduce',
        denoiseStrength: document.getElementById('denoiseStrength')?.value || 'medium',
        
        // Segment processing options
        vadAggressiveness: parseInt(document.getElementById('vadAggressiveness')?.value || '2'),
        vadMinChunkDuration: parseFloat(document.getElementById('vadMinChunkDuration')?.value || '1.0'),
        vadMaxChunkDuration: parseFloat(document.getElementById('vadMaxChunkDuration')?.value || '30.0'),
        segmentRetryEnabled: document.getElementById('segmentRetryEnabled')?.checked !== false,
        maxSegmentRetries: parseInt(document.getElementById('maxSegmentRetries')?.value || '2'),
        
        // Processing options
        parallelProcessingEnabled: document.getElementById('parallelProcessingEnabled')?.checked !== false,
        parallelWorkers: parseInt(document.getElementById('parallelWorkers')?.value || '2')
    };
}

function applyAdvancedOptions(options) {
    // Denoising
    if (options.denoiseEnabled !== undefined) {
        const checkbox = document.getElementById('denoiseEnabled');
        if (checkbox) checkbox.checked = options.denoiseEnabled;
    }
    if (options.denoiseBackend) {
        const select = document.getElementById('denoiseBackend');
        if (select) select.value = options.denoiseBackend;
    }
    if (options.denoiseStrength) {
        const select = document.getElementById('denoiseStrength');
        if (select) select.value = options.denoiseStrength;
    }
    
    // Segment processing
    if (options.vadAggressiveness !== undefined) {
        const slider = document.getElementById('vadAggressiveness');
        if (slider) {
            slider.value = options.vadAggressiveness;
            const valueDisplay = document.getElementById('vadAggressivenessValue');
            if (valueDisplay) valueDisplay.textContent = options.vadAggressiveness;
        }
    }
    if (options.vadMinChunkDuration !== undefined) {
        const input = document.getElementById('vadMinChunkDuration');
        if (input) input.value = options.vadMinChunkDuration;
    }
    if (options.vadMaxChunkDuration !== undefined) {
        const input = document.getElementById('vadMaxChunkDuration');
        if (input) input.value = options.vadMaxChunkDuration;
    }
    if (options.segmentRetryEnabled !== undefined) {
        const checkbox = document.getElementById('segmentRetryEnabled');
        if (checkbox) checkbox.checked = options.segmentRetryEnabled;
    }
    if (options.maxSegmentRetries !== undefined) {
        const input = document.getElementById('maxSegmentRetries');
        if (input) input.value = options.maxSegmentRetries;
    }
    
    // Processing
    if (options.parallelProcessingEnabled !== undefined) {
        const checkbox = document.getElementById('parallelProcessingEnabled');
        if (checkbox) checkbox.checked = options.parallelProcessingEnabled;
    }
    if (options.parallelWorkers !== undefined) {
        const input = document.getElementById('parallelWorkers');
        if (input) input.value = options.parallelWorkers;
    }
}

function resetAdvancedOptions() {
    // Reset to defaults
    const defaults = {
        denoiseEnabled: false,
        denoiseBackend: 'noisereduce',
        denoiseStrength: 'medium',
        vadAggressiveness: 2,
        vadMinChunkDuration: 1.0,
        vadMaxChunkDuration: 30.0,
        segmentRetryEnabled: true,
        maxSegmentRetries: 2,
        parallelProcessingEnabled: true,
        parallelWorkers: 2
    };
    
    applyAdvancedOptions(defaults);
    saveAdvancedOptions(defaults);
    updateStatus('Options reset to defaults', 'success');
}

function saveAdvancedOptions(options) {
    try {
        localStorage.setItem('transcriptionOptions', JSON.stringify(options));
    } catch (e) {
        console.error('Failed to save options:', e);
    }
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
                const processingOptions = collectAdvancedOptions();
                const transcribeResponse = await fetch('/transcribe-v2', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        filename: uploadData.filename,
                        processing_options: processingOptions
                    })
                });
                
                if (transcribeResponse.ok) {
                    const transcribeData = await transcribeResponse.json();
                    if (transcribeData.status === 'success') {
                        fileData.status = 'success';
                        // Handle v2 response structure
                        if (transcribeData.result) {
                            const transcription = transcribeData.result.transcription || {};
                            fileData.transcription = transcription.gurmukhi || transcription.roman || '';
                            fileData.language = transcribeData.result.segments?.[0]?.language || 'unknown';
                        } else {
                            fileData.transcription = transcribeData.transcription || '';
                            fileData.language = transcribeData.language || 'unknown';
                        }
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
        
        // Collect processing options and save them
        const processingOptions = collectAdvancedOptions();
        saveAdvancedOptions(processingOptions);
        
        // Start transcription in background
        const transcribePromise = fetch('/transcribe-v2', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                filename: uploadData.filename,
                processing_options: processingOptions
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
            // Handle v2 response structure
            if (transcribeData.result) {
                // Extract transcription from result
                const transcription = transcribeData.result.transcription || {};
                fileData.transcription = transcription.gurmukhi || transcription.roman || '';
                fileData.language = transcribeData.result.segments?.[0]?.language || 'unknown';
            } else {
                // Fallback to old structure
                fileData.transcription = transcribeData.transcription || '';
                fileData.language = transcribeData.language || 'unknown';
            }
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
            <div class="transcription-text" id="transcriptionText-${index}">${escapeHtml(transcription).replace(/\n/g, '<br>')}</div>
            <div class="result-actions">
                <button class="btn-secondary" onclick="copyToClipboard(${index})" id="copyBtn-${index}">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    Copy to Clipboard
                </button>
                <div class="export-dropdown-container" style="position: relative; display: inline-block;">
                    <select id="formatSelect-${index}" class="format-select" style="padding: 8px 12px; border: 1px solid var(--color-primary); border-radius: 4px 0 0 4px; font-size: 14px; background: white; cursor: pointer; min-width: 180px;">
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
                    <button class="btn-primary" onclick="exportDocument(${index})" id="exportBtn-${index}" style="border-radius: 0 4px 4px 0; margin-left: -1px;">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        Download
                    </button>
                </div>
            </div>
            <div class="export-help" style="margin-top: 15px; padding: 12px; background: #f8f9fa; border-radius: 6px; font-size: 0.85em; color: #666;">
                <strong>Export Options:</strong>
                <ul style="margin: 8px 0 0 20px; padding: 0;">
                    <li><strong>Plain Text / Raw JSON:</strong> Simple output files with just the transcription</li>
                    <li><strong>Formatted Documents:</strong> Rich documents with sections, scripture quotes, and metadata</li>
                </ul>
            </div>
        </div>
    `;
    
    resultsContainer.scrollIntoView({ behavior: 'smooth' });
}

function copyToClipboard(index) {
    const fileData = appState.files[index];
    if (!fileData.transcription) return;
    
    const transcription = typeof fileData.transcription === 'string' 
        ? fileData.transcription 
        : fileData.transcription.transcription || fileData.transcription.text || '';
    
    navigator.clipboard.writeText(transcription).then(() => {
        const copyBtn = document.getElementById(`copyBtn-${index}`);
        if (copyBtn) {
            const originalText = copyBtn.innerHTML;
            copyBtn.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                Copied!
            `;
            copyBtn.style.background = 'var(--color-success)';
            copyBtn.style.color = 'white';
            
            setTimeout(() => {
                copyBtn.innerHTML = originalText;
                copyBtn.style.background = '';
                copyBtn.style.color = '';
            }, 2000);
        }
    }).catch(err => {
        console.error('Failed to copy:', err);
        updateStatus('Failed to copy to clipboard', 'error');
    });
}

function downloadTranscription(index) {
    // Redirect to unified export function with txt format
    const formatSelect = document.getElementById(`formatSelect-${index}`);
    if (formatSelect) {
        formatSelect.value = 'txt';
    }
    exportDocument(index, 'txt');
}

function downloadJSON(index) {
    // Redirect to unified export function with json-raw format
    const formatSelect = document.getElementById(`formatSelect-${index}`);
    if (formatSelect) {
        formatSelect.value = 'json-raw';
    }
    exportDocument(index, 'json-raw');
}

async function exportDocument(index, overrideFormat = null) {
    const fileData = appState.files[index];
    if (!fileData.name) {
        updateStatus('File name not available', 'error');
        return;
    }
    
    const formatSelect = document.getElementById(`formatSelect-${index}`);
    const exportBtn = document.getElementById(`exportBtn-${index}`);
    
    if (!formatSelect || !exportBtn) {
        updateStatus('Export controls not found', 'error');
        return;
    }
    
    const format = overrideFormat || formatSelect.value;
    const filename = fileData.name;
    
    // Store original button content
    const originalBtnContent = exportBtn.innerHTML;
    
    // Disable button and show loading state
    exportBtn.disabled = true;
    exportBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 6v6l4 2"></path>
        </svg>
        Exporting...
    `;
    
    // Get the format extension for download filename
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
    
    // Export via API using fetch to handle errors properly
    const exportUrl = `/export/${encodeURIComponent(filename)}/${format}`;
    
    try {
        const response = await fetch(exportUrl);
        
        if (!response.ok) {
            // Try to get error message from JSON response
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
        
        // Get the blob from response
        const blob = await response.blob();
        
        // Create download link
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = downloadFilename;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        
        // Cleanup
        setTimeout(() => {
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }, 100);
        
        // Show success state
        exportBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Downloaded!
        `;
        exportBtn.style.background = 'var(--color-success)';
        updateStatus(`Downloaded ${format.toUpperCase()} document`, 'success');
        
        // Reset button after delay
        setTimeout(() => {
            exportBtn.disabled = false;
            exportBtn.innerHTML = originalBtnContent;
            exportBtn.style.background = '';
        }, 2000);
        
    } catch (error) {
        console.error('Export error:', error);
        updateStatus(`Export failed: ${error.message}`, 'error');
        
        // Reset button on error
        exportBtn.disabled = false;
        exportBtn.innerHTML = originalBtnContent;
        exportBtn.style.background = '';
    }
}

// For backwards compatibility
function exportFormattedDocument(index) {
    exportDocument(index);
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
    fileData.currentStep = progressData.current_step || 'initializing';
    fileData.stepProgress = progressData.step_progress || 0;
    fileData.stepDetails = progressData.step_details || null;
    
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
    
    // Update detailed progress section
    updateDetailedProgress(fileIndex, progressData);
    
    // Update status message
    if (fileData.progressMessage) {
        updateStatus(fileData.progressMessage, 'info');
    }
}

function updateDetailedProgress(fileIndex, progressData) {
    if (!detailedProgressSection || !detailedProgressContainer) return;
    
    const fileData = appState.files[fileIndex];
    if (!fileData) return;
    
    const currentStep = progressData.current_step || 'initializing';
    const stepProgress = progressData.step_progress || 0;
    const overallProgress = progressData.progress || 0;
    const message = progressData.message || '';
    const stepDetails = progressData.step_details || null;
    
    // Show the detailed progress section
    detailedProgressSection.style.display = 'block';
    
    // Update filename display if in batch mode
    const sectionHeader = document.getElementById('detailedProgressTitle');
    if (sectionHeader && appState.processingMode === 'batch') {
        const processingFiles = appState.files.filter(f => f.status === 'processing');
        if (processingFiles.length > 1) {
            sectionHeader.textContent = `Processing Progress (${processingFiles.length} files)`;
        } else {
            sectionHeader.textContent = `Processing: ${fileData.name}`;
        }
    } else if (sectionHeader) {
        sectionHeader.textContent = 'Processing Progress';
    }
    
    // Update overall progress
    const overallProgressBar = document.getElementById('overallProgressBar');
    const overallProgressPercentage = document.getElementById('overallProgressPercentage');
    if (overallProgressBar) {
        overallProgressBar.style.width = `${overallProgress}%`;
    }
    if (overallProgressPercentage) {
        overallProgressPercentage.textContent = `${Math.round(overallProgress)}%`;
    }
    
    // Update current step
    const currentStepName = document.getElementById('currentStepName');
    const currentStepDetails = document.getElementById('currentStepDetails');
    const currentStepProgressBar = document.getElementById('currentStepProgressBar');
    const currentStepProgress = document.getElementById('currentStepProgress');
    const currentStepIcon = document.getElementById('currentStepIcon');
    
    // Step name mapping
    const stepNames = {
        'denoising': 'Denoising Audio',
        'chunking': 'Creating Audio Chunks',
        'transcribing': 'Transcribing Chunks',
        'post_processing': 'Post-processing',
        'initializing': 'Initializing'
    };
    
    const stepIcons = {
        'denoising': '🔊',
        'chunking': '✂️',
        'transcribing': '📝',
        'post_processing': '✨',
        'initializing': '⏳'
    };
    
    if (currentStepName) {
        currentStepName.textContent = stepNames[currentStep] || currentStep;
    }
    if (currentStepIcon) {
        currentStepIcon.textContent = stepIcons[currentStep] || '⏳';
    }
    if (currentStepDetails) {
        let detailsText = message;
        if (stepDetails) {
            if (stepDetails.current_chunk && stepDetails.total_chunks) {
                detailsText = `Chunk ${stepDetails.current_chunk} of ${stepDetails.total_chunks}`;
            } else if (stepDetails.chunk_count) {
                detailsText = `${stepDetails.chunk_count} chunks created`;
            }
        }
        currentStepDetails.textContent = detailsText;
    }
    if (currentStepProgressBar) {
        currentStepProgressBar.style.width = `${stepProgress}%`;
    }
    if (currentStepProgress) {
        currentStepProgress.textContent = `${Math.round(stepProgress)}%`;
    }
    
    // Update step list - mark completed steps
    const stepsList = document.getElementById('stepsList');
    if (stepsList) {
        const stepItems = stepsList.querySelectorAll('.step-item');
        const stepOrder = ['denoising', 'chunking', 'transcribing', 'post_processing'];
        const currentStepIndex = stepOrder.indexOf(currentStep);
        
        // If step is "initializing" or not found, show all as upcoming
        const validStepIndex = currentStepIndex >= 0 ? currentStepIndex : -1;
        
        stepItems.forEach((item, index) => {
            const stepName = item.dataset.step;
            const stepCheck = item.querySelector('.step-check');
            
            if (validStepIndex >= 0 && index < validStepIndex) {
                // Completed step
                item.classList.add('completed');
                item.classList.remove('active');
                if (stepCheck) stepCheck.textContent = '✓';
            } else if (index === validStepIndex) {
                // Current step
                item.classList.add('active');
                item.classList.remove('completed');
                if (stepCheck) stepCheck.textContent = '⟳';
            } else {
                // Upcoming step
                item.classList.remove('active', 'completed');
                if (stepCheck) stepCheck.textContent = '○';
            }
        });
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
    } else {
        // Hide detailed progress when processing stops
        if (detailedProgressSection) {
            detailedProgressSection.style.display = 'none';
        }
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

// Removed loadLog function - Processing Log section removed

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
