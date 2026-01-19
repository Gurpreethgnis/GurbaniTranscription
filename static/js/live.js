/**
 * Live transcription client using WebSocket.
 * 
 * Handles:
 * - WebSocket connection management
 * - Audio capture using MediaRecorder API
 * - Draft and verified caption display
 * - Segment update/replacement
 */

class LiveTranscriptionClient {
    constructor() {
        this.socket = null;
        this.mediaRecorder = null;
        this.audioStream = null;
        this.isRecording = false;
        this.sessionId = null;
        this.segments = new Map(); // segment_id -> segment data
        this.currentOutputMode = 'gurmukhi'; // 'gurmukhi', 'roman', 'both'
        this.startTime = null;
        this.chunkSequence = 0;
        
        this.initializeUI();
        this.initializeSocket();
    }
    
    initializeUI() {
        // Button handlers
        document.getElementById('startBtn').addEventListener('click', () => this.startRecording());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopRecording());
        
        // Output toggle
        document.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentOutputMode = e.target.dataset.output;
                this.updateDisplay();
            });
        });
    }
    
    initializeSocket() {
        // Connect to WebSocket server
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
        
        this.socket.on('draft_caption', (data) => {
            this.handleDraftCaption(data);
        });
        
        this.socket.on('verified_update', (data) => {
            this.handleVerifiedUpdate(data);
        });
        
        this.socket.on('error', (data) => {
            this.showError(data.message || 'An error occurred');
        });
        
        this.socket.on('chunk_received', (data) => {
            console.log('Chunk received:', data.sequence);
        });
    }
    
    async startRecording() {
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
            
            // Fallback to default if codec not supported
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
            
            // Start recording with timeslice (chunk duration)
            const chunkDuration = 1000; // 1 second chunks
            this.mediaRecorder.start(chunkDuration);
            this.isRecording = true;
            this.startTime = Date.now();
            this.chunkSequence = 0;
            
            // Update UI
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            this.updateStatus('recording', 'Recording...');
            this.clearTranscript();
            
            console.log('Recording started');
            
        } catch (error) {
            console.error('Error starting recording:', error);
            this.showError('Failed to access microphone: ' + error.message);
        }
    }
    
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
        }
        
        if (this.audioStream) {
            this.audioStream.getTracks().forEach(track => track.stop());
            this.audioStream = null;
        }
        
        // Update UI
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        this.updateStatus('connected', 'Stopped (still connected)');
        
        console.log('Recording stopped');
    }
    
    async sendAudioChunk(audioBlob) {
        if (!this.socket || !this.socket.connected) {
            console.warn('Socket not connected, cannot send audio chunk');
            return;
        }
        
        try {
            // Convert blob to base64
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64data = reader.result.split(',')[1]; // Remove data:audio/webm;base64, prefix
                
                const elapsed = (Date.now() - this.startTime) / 1000; // seconds
                const chunkDuration = audioBlob.size / 16000; // Approximate duration
                
                const chunkData = {
                    data: base64data,
                    timestamp: Date.now(),
                    sequence: this.chunkSequence++,
                    start_time: elapsed,
                    end_time: elapsed + chunkDuration
                };
                
                this.socket.emit('audio_chunk', chunkData);
            };
            reader.readAsDataURL(audioBlob);
            
        } catch (error) {
            console.error('Error sending audio chunk:', error);
            this.showError('Failed to send audio chunk: ' + error.message);
        }
    }
    
    handleDraftCaption(data) {
        console.log('Draft caption received:', data);
        
        // Store or update segment
        if (!this.segments.has(data.segment_id)) {
            this.segments.set(data.segment_id, {
                id: data.segment_id,
                start: data.start,
                end: data.end,
                draft: {
                    text: data.text,
                    gurmukhi: data.gurmukhi || data.text,
                    roman: data.roman || '',
                    confidence: data.confidence
                },
                verified: null,
                isDraft: true
            });
        } else {
            // Update existing draft
            const segment = this.segments.get(data.segment_id);
            segment.draft = {
                text: data.text,
                gurmukhi: data.gurmukhi || data.text,
                roman: data.roman || '',
                confidence: data.confidence
            };
            segment.isDraft = true;
        }
        
        this.updateDisplay();
    }
    
    handleVerifiedUpdate(data) {
        console.log('Verified update received:', data);
        
        // Update segment with verified data
        if (this.segments.has(data.segment_id)) {
            const segment = this.segments.get(data.segment_id);
            segment.verified = {
                gurmukhi: data.gurmukhi,
                roman: data.roman,
                confidence: data.confidence,
                quote_match: data.quote_match,
                needs_review: data.needs_review
            };
            segment.isDraft = false;
        } else {
            // Create new segment if draft was missed
            this.segments.set(data.segment_id, {
                id: data.segment_id,
                start: data.start,
                end: data.end,
                draft: null,
                verified: {
                    gurmukhi: data.gurmukhi,
                    roman: data.roman,
                    confidence: data.confidence,
                    quote_match: data.quote_match,
                    needs_review: data.needs_review
                },
                isDraft: false
            });
        }
        
        this.updateDisplay();
    }
    
    updateDisplay() {
        const transcriptArea = document.getElementById('transcriptArea');
        
        if (this.segments.size === 0) {
            transcriptArea.innerHTML = '<p style="color: #6c757d; text-align: center; margin-top: 50px;">Click "Start Recording" to begin live transcription...</p>';
            return;
        }
        
        // Sort segments by start time
        const sortedSegments = Array.from(this.segments.values())
            .sort((a, b) => a.start - b.start);
        
        let html = '';
        for (const segment of sortedSegments) {
            const isDraft = segment.isDraft && !segment.verified;
            const hasQuote = segment.verified && segment.verified.quote_match;
            
            let segmentClass = isDraft ? 'draft' : 'verified';
            if (hasQuote) {
                segmentClass += ' quote';
            }
            
            // Determine text to display based on output mode
            let displayText = '';
            let displayRoman = '';
            
            if (segment.verified) {
                displayText = segment.verified.gurmukhi;
                displayRoman = segment.verified.roman;
            } else if (segment.draft) {
                displayText = segment.draft.gurmukhi;
                displayRoman = segment.draft.roman;
            }
            
            const confidence = segment.verified ? segment.verified.confidence : (segment.draft ? segment.draft.confidence : 0);
            const confidenceClass = confidence >= 0.8 ? 'high' : (confidence >= 0.6 ? 'medium' : 'low');
            
            html += `<div class="segment ${segmentClass}">`;
            html += `<div class="segment-header">`;
            html += `<span>${segment.start.toFixed(1)}s - ${segment.end.toFixed(1)}s</span>`;
            html += `<span class="confidence-badge confidence-${confidenceClass}">${(confidence * 100).toFixed(0)}%</span>`;
            html += `</div>`;
            
            if (this.currentOutputMode === 'gurmukhi' || this.currentOutputMode === 'both') {
                html += `<div class="segment-text">${this.escapeHtml(displayText)}</div>`;
            }
            
            if (this.currentOutputMode === 'roman' || this.currentOutputMode === 'both') {
                if (displayRoman) {
                    html += `<div class="segment-roman">${this.escapeHtml(displayRoman)}</div>`;
                }
            }
            
            if (hasQuote) {
                const quote = segment.verified.quote_match;
                html += `<div class="quote-metadata">`;
                html += `Quote: ${quote.source} | Ang: ${quote.ang || 'N/A'} | Raag: ${quote.raag || 'N/A'}`;
                if (quote.author) {
                    html += ` | Author: ${quote.author}`;
                }
                html += `</div>`;
            }
            
            if (isDraft) {
                html += `<div style="font-size: 12px; color: #ffc107; margin-top: 5px;">Draft (awaiting verification...)</div>`;
            }
            
            html += `</div>`;
        }
        
        transcriptArea.innerHTML = html;
        
        // Auto-scroll to bottom
        transcriptArea.scrollTop = transcriptArea.scrollHeight;
    }
    
    updateStatus(status, message) {
        const statusEl = document.getElementById('status');
        statusEl.className = `status ${status}`;
        statusEl.textContent = message;
    }
    
    showError(message) {
        const errorEl = document.getElementById('errorMessage');
        errorEl.textContent = message;
        errorEl.style.display = 'block';
        
        // Hide after 5 seconds
        setTimeout(() => {
            errorEl.style.display = 'none';
        }, 5000);
    }
    
    clearTranscript() {
        this.segments.clear();
        this.updateDisplay();
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.liveClient = new LiveTranscriptionClient();
});
