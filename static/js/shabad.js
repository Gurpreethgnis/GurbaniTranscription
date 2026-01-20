/**
 * Shabad Mode Client - Live Kirtan Detection with Praman Suggestions
 * 
 * Handles:
 * - WebSocket connection for shabad mode
 * - Audio capture and streaming
 * - Display of current/next shabad lines
 * - Praman suggestions display and filtering
 * - User preference management
 */

class ShabadModeClient {
    constructor() {
        this.socket = null;
        this.mediaRecorder = null;
        this.audioStream = null;
        this.isRecording = false;
        this.sessionId = null;
        this.startTime = null;
        this.chunkSequence = 0;
        
        // Preferences
        this.preferences = {
            similarCount: 5,
            dissimilarCount: 3,
            showSimilar: true,
            showDissimilar: true
        };
        
        // Current state
        this.currentShabadId = null;
        this.currentFilter = 'all';
        
        // Load saved preferences
        this.loadPreferences();
        
        this.initializeUI();
        this.initializeSocket();
    }
    
    loadPreferences() {
        try {
            const saved = localStorage.getItem('shabadModePreferences');
            if (saved) {
                this.preferences = { ...this.preferences, ...JSON.parse(saved) };
            }
        } catch (e) {
            console.warn('Failed to load shabad preferences:', e);
        }
    }
    
    savePreferences() {
        try {
            localStorage.setItem('shabadModePreferences', JSON.stringify(this.preferences));
        } catch (e) {
            console.warn('Failed to save shabad preferences:', e);
        }
    }
    
    initializeUI() {
        // Button handlers
        document.getElementById('startShabadBtn').addEventListener('click', () => this.startListening());
        document.getElementById('stopShabadBtn').addEventListener('click', () => this.stopListening());
        document.getElementById('resetContextBtn').addEventListener('click', () => this.resetContext());
        
        // Preferences toggle
        document.getElementById('preferencesToggle').addEventListener('click', () => {
            const panel = document.getElementById('preferencesPanel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        });
        
        // Preference sliders
        const similarSlider = document.getElementById('similarCount');
        const dissimilarSlider = document.getElementById('dissimilarCount');
        
        similarSlider.value = this.preferences.similarCount;
        dissimilarSlider.value = this.preferences.dissimilarCount;
        document.getElementById('similarCountValue').textContent = this.preferences.similarCount;
        document.getElementById('dissimilarCountValue').textContent = this.preferences.dissimilarCount;
        
        similarSlider.addEventListener('input', (e) => {
            this.preferences.similarCount = parseInt(e.target.value);
            document.getElementById('similarCountValue').textContent = e.target.value;
            this.savePreferences();
            this.updateServerPreferences();
        });
        
        dissimilarSlider.addEventListener('input', (e) => {
            this.preferences.dissimilarCount = parseInt(e.target.value);
            document.getElementById('dissimilarCountValue').textContent = e.target.value;
            this.savePreferences();
            this.updateServerPreferences();
        });
        
        // Checkboxes
        const showSimilarCheck = document.getElementById('showSimilar');
        const showDissimilarCheck = document.getElementById('showDissimilar');
        
        showSimilarCheck.checked = this.preferences.showSimilar;
        showDissimilarCheck.checked = this.preferences.showDissimilar;
        
        showSimilarCheck.addEventListener('change', (e) => {
            this.preferences.showSimilar = e.target.checked;
            this.savePreferences();
            this.updateServerPreferences();
            this.updatePramanVisibility();
        });
        
        showDissimilarCheck.addEventListener('change', (e) => {
            this.preferences.showDissimilar = e.target.checked;
            this.savePreferences();
            this.updateServerPreferences();
            this.updatePramanVisibility();
        });
        
        // Filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentFilter = e.target.dataset.filter;
                this.updatePramanVisibility();
            });
        });
    }
    
    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.updateStatus('connected', 'Connected');
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.updateStatus('disconnected', 'Disconnected');
        });
        
        this.socket.on('connected', (data) => {
            this.sessionId = data.session_id;
            console.log('Session ID:', this.sessionId);
        });
        
        this.socket.on('shabad_started', (data) => {
            console.log('Shabad mode started:', data);
            this.updateStatus('listening', 'Listening for kirtan...');
        });
        
        this.socket.on('shabad_stopped', (data) => {
            console.log('Shabad mode stopped:', data);
        });
        
        this.socket.on('shabad_update', (data) => {
            console.log('Shabad update received:', data);
            this.handleShabadUpdate(data);
        });
        
        this.socket.on('praman_suggestions', (data) => {
            console.log('Praman suggestions received:', data);
            this.handlePramanSuggestions(data);
        });
        
        this.socket.on('shabad_chunk_received', (data) => {
            console.log('Chunk received:', data.sequence);
        });
        
        this.socket.on('shabad_context_reset', (data) => {
            console.log('Shabad context reset:', data);
            this.clearDisplay();
        });
        
        this.socket.on('error', (data) => {
            console.error('Server error:', data);
            this.showError(data.message || 'An error occurred');
        });
    }
    
    async startListening() {
        try {
            // Request microphone access
            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });
            
            // Initialize MediaRecorder
            const options = {
                mimeType: 'audio/webm;codecs=opus',
                audioBitsPerSecond: 128000
            };
            
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options.mimeType = 'audio/webm';
            }
            
            this.mediaRecorder = new MediaRecorder(this.audioStream, options);
            
            // Handle data available
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.sendAudioChunk(event.data);
                }
            };
            
            // Start shabad mode on server
            this.socket.emit('shabad_start', this.preferences);
            
            // Start recording with 2-second chunks for better shabad detection
            const chunkDuration = 2000;
            this.mediaRecorder.start(chunkDuration);
            this.isRecording = true;
            this.startTime = Date.now();
            this.chunkSequence = 0;
            
            // Update UI
            document.getElementById('startShabadBtn').disabled = true;
            document.getElementById('stopShabadBtn').disabled = false;
            this.updateStatus('listening', 'Listening for kirtan...');
            
            console.log('Shabad mode started');
            
        } catch (error) {
            console.error('Error starting shabad mode:', error);
            this.showError('Failed to access microphone: ' + error.message);
        }
    }
    
    stopListening() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
        }
        
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
            this.audioStream = null;
        }
        
        // Stop shabad mode on server
        this.socket.emit('shabad_stop');
        
        // Update UI
        document.getElementById('startShabadBtn').disabled = false;
        document.getElementById('stopShabadBtn').disabled = true;
        this.updateStatus('connected', 'Stopped (still connected)');
        
        console.log('Shabad mode stopped');
    }
    
    resetContext() {
        this.socket.emit('shabad_reset');
        this.currentShabadId = null;
        this.clearDisplay();
    }
    
    async sendAudioChunk(audioBlob) {
        if (!this.socket || !this.socket.connected) {
            console.warn('Socket not connected, cannot send audio chunk');
            return;
        }
        
        try {
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64data = reader.result.split(',')[1];
                
                const elapsed = (Date.now() - this.startTime) / 1000;
                const chunkDuration = 2.0; // 2 second chunks
                
                const chunkData = {
                    data: base64data,
                    timestamp: Date.now(),
                    sequence: this.chunkSequence++,
                    start_time: elapsed - chunkDuration,
                    end_time: elapsed,
                    similar_count: this.preferences.similarCount,
                    dissimilar_count: this.preferences.dissimilarCount
                };
                
                this.socket.emit('shabad_audio_chunk', chunkData);
            };
            reader.readAsDataURL(audioBlob);
            
        } catch (error) {
            console.error('Error sending audio chunk:', error);
        }
    }
    
    handleShabadUpdate(data) {
        // Update mode indicator
        const modeIndicator = document.getElementById('modeIndicator');
        const modeText = document.getElementById('modeText');
        
        if (data.audio_mode === 'shabad') {
            modeIndicator.className = 'shabad-mode-indicator shabad-mode';
            modeText.textContent = 'Shabad Detected';
        } else if (data.audio_mode === 'katha') {
            modeIndicator.className = 'shabad-mode-indicator katha-mode';
            modeText.textContent = 'Katha Mode';
        } else {
            modeIndicator.className = 'shabad-mode-indicator';
            modeText.textContent = 'Analyzing...';
        }
        
        // Update current line display
        if (data.matched_line) {
            this.displayCurrentLine(data.matched_line, data.is_new_shabad);
            
            // Show metadata
            document.getElementById('shabadMetadata').style.display = 'flex';
            this.updateMetadata(data.matched_line, data.shabad_info);
        }
        
        // Update next line
        if (data.next_line) {
            this.displayNextLine(data.next_line);
        }
        
        // Track new shabads
        if (data.is_new_shabad) {
            this.currentShabadId = data.matched_line?.shabad_id;
        }
    }
    
    displayCurrentLine(line, isNewShabad) {
        const container = document.getElementById('currentLineDisplay');
        
        const html = `
            <div class="current-line ${isNewShabad ? 'new-shabad' : ''}">
                <p class="gurmukhi-text">${this.escapeHtml(line.gurmukhi)}</p>
                ${line.roman ? `<p class="roman-text">${this.escapeHtml(line.roman)}</p>` : ''}
            </div>
        `;
        
        container.innerHTML = html;
        
        // Add animation class
        if (isNewShabad) {
            container.classList.add('shabad-transition');
            setTimeout(() => container.classList.remove('shabad-transition'), 500);
        }
    }
    
    displayNextLine(line) {
        const container = document.getElementById('nextLineDisplay');
        
        const html = `
            <div class="next-line-label">Next Line:</div>
            <div class="next-line-content">
                <p class="gurmukhi-text dim">${this.escapeHtml(line.gurmukhi)}</p>
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    updateMetadata(line, shabadInfo) {
        document.getElementById('metaAng').innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
            </svg>
            Ang: ${line.ang || '—'}
        `;
        
        document.getElementById('metaRaag').innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18V5l12-2v13"></path>
                <circle cx="6" cy="18" r="3"></circle>
                <circle cx="18" cy="16" r="3"></circle>
            </svg>
            Raag: ${line.raag || '—'}
        `;
        
        document.getElementById('metaAuthor').innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
            </svg>
            Author: ${line.author || '—'}
        `;
        
        if (shabadInfo) {
            document.getElementById('metaProgress').innerHTML = `
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="8" y1="6" x2="21" y2="6"></line>
                    <line x1="8" y1="12" x2="21" y2="12"></line>
                    <line x1="8" y1="18" x2="21" y2="18"></line>
                    <line x1="3" y1="6" x2="3.01" y2="6"></line>
                    <line x1="3" y1="12" x2="3.01" y2="12"></line>
                    <line x1="3" y1="18" x2="3.01" y2="18"></line>
                </svg>
                Line: ${(shabadInfo.current_line_index || 0) + 1} / ${shabadInfo.total_lines || '—'}
            `;
        }
    }
    
    handlePramanSuggestions(data) {
        // Update similar pramans
        this.displayPramans('similarPramansList', data.similar_pramans, 'similar');
        
        // Update dissimilar pramans
        this.displayPramans('dissimilarPramansList', data.dissimilar_pramans, 'dissimilar');
        
        // Apply visibility filters
        this.updatePramanVisibility();
    }
    
    displayPramans(containerId, pramans, type) {
        const container = document.getElementById(containerId);
        
        if (!pramans || pramans.length === 0) {
            container.innerHTML = `
                <div class="praman-placeholder">
                    <p>No ${type === 'similar' ? 'similar' : 'contrasting'} pramans found</p>
                </div>
            `;
            return;
        }
        
        const html = pramans.map(praman => `
            <div class="praman-card ${type}">
                <div class="praman-text">
                    <p class="gurmukhi-text">${this.escapeHtml(praman.gurmukhi)}</p>
                    ${praman.roman ? `<p class="roman-text">${this.escapeHtml(praman.roman)}</p>` : ''}
                </div>
                <div class="praman-meta">
                    <span class="praman-source">${praman.source}</span>
                    ${praman.ang ? `<span class="praman-ang">Ang ${praman.ang}</span>` : ''}
                    ${praman.raag ? `<span class="praman-raag">${praman.raag}</span>` : ''}
                </div>
                ${praman.shared_keywords?.length > 0 ? `
                    <div class="praman-keywords">
                        ${praman.shared_keywords.map(kw => `<span class="keyword">${this.escapeHtml(kw)}</span>`).join('')}
                    </div>
                ` : ''}
                <div class="praman-score">
                    ${(praman.similarity_score * 100).toFixed(0)}% ${type === 'similar' ? 'similar' : 'contrasting'}
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
    }
    
    updatePramanVisibility() {
        const similarPanel = document.getElementById('similarPramansPanel');
        const dissimilarPanel = document.getElementById('dissimilarPramansPanel');
        
        // Apply filter
        if (this.currentFilter === 'similar') {
            similarPanel.style.display = 'block';
            dissimilarPanel.style.display = 'none';
        } else if (this.currentFilter === 'dissimilar') {
            similarPanel.style.display = 'none';
            dissimilarPanel.style.display = 'block';
        } else {
            // Show both, but respect preferences
            similarPanel.style.display = this.preferences.showSimilar ? 'block' : 'none';
            dissimilarPanel.style.display = this.preferences.showDissimilar ? 'block' : 'none';
        }
    }
    
    updateServerPreferences() {
        if (this.socket && this.socket.connected) {
            this.socket.emit('shabad_preferences', this.preferences);
        }
    }
    
    clearDisplay() {
        // Reset current line
        document.getElementById('currentLineDisplay').innerHTML = `
            <div class="line-placeholder">
                <p class="gurmukhi-text placeholder-text">ਸ਼ਬਦ ਸੁਣਨ ਲਈ "Start Listening" ਦਬਾਓ</p>
                <p class="roman-text placeholder-text">Press "Start Listening" to detect shabads</p>
            </div>
        `;
        
        // Reset next line
        document.getElementById('nextLineDisplay').innerHTML = `
            <div class="next-line-label">Next Line:</div>
            <div class="next-line-content">
                <p class="gurmukhi-text dim">—</p>
            </div>
        `;
        
        // Hide metadata
        document.getElementById('shabadMetadata').style.display = 'none';
        
        // Reset mode indicator
        document.getElementById('modeIndicator').className = 'shabad-mode-indicator';
        document.getElementById('modeText').textContent = 'Waiting for audio...';
        
        // Clear pramans
        document.getElementById('similarPramansList').innerHTML = `
            <div class="praman-placeholder">
                <p>Similar pramans will appear here when a shabad line is detected</p>
            </div>
        `;
        document.getElementById('dissimilarPramansList').innerHTML = `
            <div class="praman-placeholder">
                <p>Contrasting pramans will appear here when a shabad line is detected</p>
            </div>
        `;
    }
    
    updateStatus(status, message) {
        const statusEl = document.getElementById('shabadStatus');
        statusEl.className = `status ${status}`;
        document.getElementById('statusText').textContent = message;
    }
    
    showError(message) {
        const errorEl = document.getElementById('errorMessage');
        errorEl.textContent = message;
        errorEl.style.display = 'block';
        
        setTimeout(() => {
            errorEl.style.display = 'none';
        }, 5000);
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.shabadClient = new ShabadModeClient();
});

