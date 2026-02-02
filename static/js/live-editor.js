/**
 * Live Transcription Rich Text Editor
 * 
 * Features:
 * - Real-time transcription display in editable rich text editor
 * - Word-like toolbar with formatting options
 * - Segment metadata shown on hover
 * - Edit tracking and export functionality
 */

class LiveEditorClient {
    constructor() {
        this.socket = null;
        this.mediaRecorder = null;
        this.audioStream = null;
        this.isRecording = false;
        this.sessionId = null;

        // Segment tracking
        this.segments = new Map(); // segment_id -> segment data
        this.currentOutputMode = 'gurmukhi'; // 'gurmukhi', 'roman', 'both'

        // Recording state
        this.startTime = null;
        this.chunkSequence = 0;

        // Editor state
        this.editor = null;
        this.lastCursorPosition = null;
        this.isComposing = false; // For IME support

        this.init();
    }

    init() {
        this.editor = document.getElementById('transcriptEditor');
        this.initializeUI();
        this.initializeSocket();
        this.initializeToolbar();
        this.initializeTooltip();
        this.updateStats();
    }

    initializeUI() {
        // Recording controls
        document.getElementById('startBtn').addEventListener('click', () => this.startRecording());
        document.getElementById('stopBtn').addEventListener('click', () => this.stopRecording());
        document.getElementById('downloadBtn').addEventListener('click', () => this.downloadTranscription());
        document.getElementById('clearEditorBtn').addEventListener('click', () => this.clearEditor());

        // Output mode toggle
        document.querySelectorAll('.output-toggle .toggle-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.output-toggle .toggle-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentOutputMode = e.target.dataset.output;
                this.refreshEditorContent();
            });
        });

        // Translation toggle
        const includeTranslation = document.getElementById('includeTranslation');
        const targetLanguage = document.getElementById('targetLanguage');
        if (includeTranslation && targetLanguage) {
            includeTranslation.addEventListener('change', (e) => {
                targetLanguage.disabled = !e.target.checked;
            });
        }

        // Editor input handling
        this.editor.addEventListener('input', () => this.onEditorInput());
        this.editor.addEventListener('compositionstart', () => this.isComposing = true);
        this.editor.addEventListener('compositionend', () => this.isComposing = false);

        // Font size selector
        const fontSizeSelect = document.getElementById('fontSizeSelect');
        if (fontSizeSelect) {
            fontSizeSelect.addEventListener('change', (e) => {
                this.editor.style.fontSize = e.target.value;
            });
        }
    }

    initializeToolbar() {
        // Toolbar button commands
        document.querySelectorAll('.toolbar-btn[data-command]').forEach(btn => {
            btn.addEventListener('click', () => {
                const command = btn.dataset.command;
                this.executeCommand(command);

                // Toggle active state for formatting buttons
                if (['bold', 'italic', 'underline'].includes(command)) {
                    btn.classList.toggle('active');
                }
            });
        });
    }

    executeCommand(command) {
        this.editor.focus();

        switch (command) {
            case 'undo':
                document.execCommand('undo');
                break;
            case 'redo':
                document.execCommand('redo');
                break;
            case 'bold':
                document.execCommand('bold');
                break;
            case 'italic':
                document.execCommand('italic');
                break;
            case 'underline':
                document.execCommand('underline');
                break;
            case 'justifyLeft':
            case 'justifyCenter':
            case 'justifyRight':
                document.execCommand(command);
                break;
        }

        this.updateStats();
    }

    initializeTooltip() {
        const tooltip = document.getElementById('segmentTooltip');

        // Show tooltip on segment hover
        this.editor.addEventListener('mouseover', (e) => {
            const segmentEl = e.target.closest('.segment-text');
            if (segmentEl) {
                const segmentId = segmentEl.dataset.segmentId;
                const segment = this.segments.get(segmentId);
                if (segment) {
                    this.showTooltip(tooltip, segment, e);
                }
            }
        });

        this.editor.addEventListener('mouseout', (e) => {
            const segmentEl = e.target.closest('.segment-text');
            if (segmentEl) {
                this.hideTooltip(tooltip);
            }
        });

        // Move tooltip with mouse
        this.editor.addEventListener('mousemove', (e) => {
            if (tooltip.style.display !== 'none') {
                this.positionTooltip(tooltip, e);
            }
        });
    }

    showTooltip(tooltip, segment, event) {
        const data = segment.verified || segment.draft;
        if (!data) return;

        // Confidence badge
        const conf = data.confidence || 0;
        const confEl = document.getElementById('tooltipConfidence');
        confEl.textContent = `${Math.round(conf * 100)}%`;
        confEl.className = 'tooltip-confidence ' + (conf >= 0.8 ? 'high' : conf >= 0.6 ? 'medium' : 'low');

        // Time
        document.getElementById('tooltipTime').textContent =
            `${segment.start.toFixed(1)}s - ${segment.end.toFixed(1)}s`;

        // Language
        const langMap = { 'pa': 'Punjabi', 'en': 'English', 'hi': 'Hindi' };
        document.getElementById('tooltipLanguage').textContent =
            langMap[segment.language] || segment.language || 'Unknown';

        // Quote info
        const quoteRow = document.getElementById('tooltipQuoteRow');
        const sourceRow = document.getElementById('tooltipSourceRow');

        if (segment.verified?.quote_match) {
            const quote = segment.verified.quote_match;
            quoteRow.style.display = 'flex';
            sourceRow.style.display = 'flex';
            document.getElementById('tooltipQuote').textContent = 'Yes - Scripture Match';
            document.getElementById('tooltipSource').textContent =
                `${quote.source || 'SGGS'} • Ang ${quote.ang || 'N/A'}`;
        } else {
            quoteRow.style.display = 'none';
            sourceRow.style.display = 'none';
        }

        this.positionTooltip(tooltip, event);
        tooltip.style.display = 'block';
    }

    positionTooltip(tooltip, event) {
        const x = event.clientX + 15;
        const y = event.clientY + 15;

        // Keep tooltip in viewport
        const rect = tooltip.getBoundingClientRect();
        const maxX = window.innerWidth - rect.width - 20;
        const maxY = window.innerHeight - rect.height - 20;

        tooltip.style.left = `${Math.min(x, maxX)}px`;
        tooltip.style.top = `${Math.min(y, maxY)}px`;
    }

    hideTooltip(tooltip) {
        tooltip.style.display = 'none';
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
            this.audioStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            const options = {
                mimeType: 'audio/webm;codecs=opus',
                audioBitsPerSecond: 128000
            };

            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options.mimeType = 'audio/webm';
            }

            this.mediaRecorder = new MediaRecorder(this.audioStream, options);

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.sendAudioChunk(event.data);
                }
            };

            const chunkDuration = 1000; // 1 second chunks
            this.mediaRecorder.start(chunkDuration);
            this.isRecording = true;
            this.startTime = Date.now();
            this.chunkSequence = 0;

            // Update UI
            document.getElementById('startBtn').disabled = true;
            document.getElementById('stopBtn').disabled = false;
            this.updateStatus('recording', 'Recording...');

            // Show recording indicator
            document.getElementById('recordingIndicator').style.display = 'flex';

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
        this.updateStatus('connected', 'Stopped');

        // Hide recording indicator
        document.getElementById('recordingIndicator').style.display = 'none';

        console.log('Recording stopped');
    }

    async sendAudioChunk(audioBlob) {
        if (!this.socket || !this.socket.connected) {
            console.warn('Socket not connected');
            return;
        }

        try {
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64data = reader.result.split(',')[1];
                const elapsed = (Date.now() - this.startTime) / 1000;
                const chunkDuration = audioBlob.size / 16000;

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
        }
    }

    handleDraftCaption(data) {
        console.log('Draft caption:', data);

        const segment = {
            id: data.segment_id,
            start: data.start,
            end: data.end,
            language: data.language || 'pa',
            draft: {
                text: data.text,
                gurmukhi: data.gurmukhi || data.text,
                roman: data.roman || '',
                confidence: data.confidence
            },
            verified: null,
            isDraft: true
        };

        this.segments.set(data.segment_id, segment);
        this.appendToEditor(segment);
        this.updateStats();
    }

    handleVerifiedUpdate(data) {
        console.log('Verified update:', data);

        let segment = this.segments.get(data.segment_id);

        if (segment) {
            segment.verified = {
                gurmukhi: data.gurmukhi,
                roman: data.roman,
                confidence: data.confidence,
                quote_match: data.quote_match,
                needs_review: data.needs_review
            };
            segment.isDraft = false;
        } else {
            segment = {
                id: data.segment_id,
                start: data.start,
                end: data.end,
                language: data.language || 'pa',
                draft: null,
                verified: {
                    gurmukhi: data.gurmukhi,
                    roman: data.roman,
                    confidence: data.confidence,
                    quote_match: data.quote_match,
                    needs_review: data.needs_review
                },
                isDraft: false
            };
            this.segments.set(data.segment_id, segment);
        }

        // Update the segment in the editor
        this.updateSegmentInEditor(segment);
        this.updateStats();
    }

    appendToEditor(segment) {
        const data = segment.verified || segment.draft;
        if (!data) return;

        // Create segment HTML
        const html = this.createSegmentHTML(segment);

        // Append to editor
        this.editor.insertAdjacentHTML('beforeend', html + ' ');

        // Scroll to bottom
        this.editor.scrollTop = this.editor.scrollHeight;

        // Update last updated time
        document.getElementById('lastUpdated').textContent =
            'Updated: ' + new Date().toLocaleTimeString();
    }

    updateSegmentInEditor(segment) {
        // Find existing segment element
        const existingEl = this.editor.querySelector(`[data-segment-id="${segment.id}"]`);

        if (existingEl) {
            // Replace with updated content
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = this.createSegmentHTML(segment);
            const newEl = tempDiv.firstChild;
            existingEl.replaceWith(newEl);
        } else {
            // Append if not found
            this.appendToEditor(segment);
        }

        // Update last updated time
        document.getElementById('lastUpdated').textContent =
            'Updated: ' + new Date().toLocaleTimeString();
    }

    createSegmentHTML(segment) {
        const data = segment.verified || segment.draft;
        if (!data) return '';

        const text = this.getDisplayText(data);
        const isDraft = segment.isDraft && !segment.verified;
        const hasQuote = segment.verified?.quote_match;
        const lowConfidence = (data.confidence || 0) < 0.6;

        let classes = 'segment-text';
        if (isDraft) classes += ' draft';
        else classes += ' verified';
        if (hasQuote) classes += ' quote';
        if (lowConfidence) classes += ' low-confidence';

        let html = `<span class="${classes}" data-segment-id="${segment.id}">${this.escapeHtml(text)}</span>`;

        // Add roman transliteration if in "both" mode
        if (this.currentOutputMode === 'both' && data.roman) {
            html += `<span class="segment-roman">${this.escapeHtml(data.roman)}</span>`;
        }

        return html;
    }

    getDisplayText(data) {
        if (this.currentOutputMode === 'roman' && data.roman) {
            return data.roman;
        }
        return data.gurmukhi || data.text || '';
    }

    refreshEditorContent() {
        // Rebuild editor content based on current output mode
        const sortedSegments = Array.from(this.segments.values())
            .sort((a, b) => a.start - b.start);

        let html = '';
        for (const segment of sortedSegments) {
            html += this.createSegmentHTML(segment) + ' ';
        }

        this.editor.innerHTML = html;
    }

    onEditorInput() {
        if (!this.isComposing) {
            this.updateStats();
        }
    }

    updateStats() {
        const text = this.editor.textContent || '';
        const words = text.trim() ? text.trim().split(/\s+/).length : 0;
        const chars = text.length;

        document.getElementById('wordCount').textContent = `Words: ${words}`;
        document.getElementById('charCount').textContent = `Characters: ${chars}`;
        document.getElementById('segmentCount').textContent = `Segments: ${this.segments.size}`;
    }

    updateStatus(status, message) {
        const statusEl = document.getElementById('status');
        const statusText = document.getElementById('statusText');

        statusEl.className = `status ${status}`;
        statusText.textContent = message;
    }

    showError(message) {
        const errorEl = document.getElementById('errorMessage');
        errorEl.textContent = message;
        errorEl.style.display = 'block';

        setTimeout(() => {
            errorEl.style.display = 'none';
        }, 5000);
    }

    clearEditor() {
        if (this.segments.size > 0) {
            if (!confirm('Clear all transcribed content?')) {
                return;
            }
        }

        this.editor.innerHTML = '';
        this.segments.clear();
        this.updateStats();
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    downloadTranscription() {
        const format = document.getElementById('downloadFormat').value || 'txt';
        const content = this.generateExportContent(format);

        if (!content) {
            this.showError('No content to download');
            return;
        }

        const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
        let filename = `katha_transcription_${timestamp}`;
        let mimeType = 'text/plain';

        switch (format) {
            case 'html':
                filename += '.html';
                mimeType = 'text/html';
                break;
            case 'json':
                filename += '.json';
                mimeType = 'application/json';
                break;
            case 'markdown':
                filename += '.md';
                mimeType = 'text/markdown';
                break;
            default:
                filename += '.txt';
        }

        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        console.log(`Downloaded as ${format}`);
    }

    generateExportContent(format) {
        // Get current editor content (includes user edits)
        const editedText = this.editor.textContent;
        const sortedSegments = Array.from(this.segments.values())
            .sort((a, b) => a.start - b.start);

        switch (format) {
            case 'html':
                return this.generateHTMLExport(editedText, sortedSegments);
            case 'json':
                return this.generateJSONExport(editedText, sortedSegments);
            case 'markdown':
                return this.generateMarkdownExport(editedText, sortedSegments);
            default:
                return this.generateTextExport(editedText, sortedSegments);
        }
    }

    generateTextExport(editedText, segments) {
        let content = `Katha Transcription\n`;
        content += `Generated: ${new Date().toLocaleString()}\n`;
        content += `${'='.repeat(50)}\n\n`;
        content += editedText;
        return content;
    }

    generateHTMLExport(editedText, segments) {
        let html = `<!DOCTYPE html>
<html lang="pa">
<head>
    <meta charset="UTF-8">
    <title>Katha Transcription</title>
    <style>
        body { font-family: 'Noto Sans Gurmukhi', sans-serif; max-width: 800px; margin: 2rem auto; padding: 1rem; line-height: 1.8; }
        h1 { color: #333; }
        .metadata { color: #666; font-size: 0.9em; margin-bottom: 2rem; }
        .content { font-size: 1.1em; }
    </style>
</head>
<body>
    <h1>ਕਥਾ Katha Transcription</h1>
    <div class="metadata">Generated: ${new Date().toLocaleString()}</div>
    <div class="content">${this.editor.innerHTML}</div>
</body>
</html>`;
        return html;
    }

    generateJSONExport(editedText, segments) {
        const data = {
            type: 'katha_transcription',
            created_at: new Date().toISOString(),
            edited_text: editedText,
            total_segments: segments.length,
            segments: segments.map(seg => ({
                id: seg.id,
                start: seg.start,
                end: seg.end,
                language: seg.language,
                gurmukhi: seg.verified?.gurmukhi || seg.draft?.gurmukhi || '',
                roman: seg.verified?.roman || seg.draft?.roman || '',
                confidence: seg.verified?.confidence || seg.draft?.confidence || 0,
                is_verified: !!seg.verified,
                quote_match: seg.verified?.quote_match || null
            }))
        };
        return JSON.stringify(data, null, 2);
    }

    generateMarkdownExport(editedText, segments) {
        let content = `# ਕਥਾ Katha Transcription\n\n`;
        content += `*Generated: ${new Date().toLocaleString()}*\n\n`;
        content += `---\n\n`;
        content += editedText;
        return content;
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.liveEditor = new LiveEditorClient();
});
