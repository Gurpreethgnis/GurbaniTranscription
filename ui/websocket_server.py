"""
WebSocket server for live transcription streaming.

Handles real-time audio streaming, draft caption delivery, and verified
transcription updates via WebSocket connections.

Phase 6: Live Mode + WebSocket UI
"""
import logging
import base64
import io
import time
from typing import Dict, Optional, Any, Callable
from flask import Flask
from flask_socketio import SocketIO, emit, disconnect
import config

logger = logging.getLogger(__name__)


class WebSocketServer:
    """
    WebSocket server for live transcription.
    
    Manages WebSocket connections and handles:
    - Audio chunk reception from clients
    - Draft caption emission (immediate ASR-A output)
    - Verified update emission (after quote detection/replacement)
    - Connection lifecycle management
    """
    
    def __init__(self, app: Flask, orchestrator_callback: Optional[Callable] = None):
        """
        Initialize WebSocket server.
        
        Args:
            app: Flask application instance
            orchestrator_callback: Callback function to process audio chunks
                                 Signature: (audio_data: bytes, session_id: str) -> None
        """
        self.app = app
        self.socketio = SocketIO(
            app,
            cors_allowed_origins="*",
            ping_interval=getattr(config, 'WEBSOCKET_PING_INTERVAL', 25),
            ping_timeout=getattr(config, 'WEBSOCKET_PING_TIMEOUT', 120),
            async_mode='eventlet'  # Use eventlet for async support
        )
        self.orchestrator_callback = orchestrator_callback
        
        # Track active sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Register event handlers
        self._register_handlers()
        
        logger.info("WebSocket server initialized")
    
    def _register_handlers(self) -> None:
        """Register WebSocket event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect(auth: Optional[Dict] = None):
            """Handle client connection."""
            session_id = self._get_session_id()
            self.active_sessions[session_id] = {
                'connected_at': time.time(),
                'chunks_received': 0,
                'drafts_sent': 0,
                'verified_sent': 0
            }
            logger.info(f"Client connected: session_id={session_id}")
            emit('connected', {'session_id': session_id, 'status': 'ok'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            session_id = self._get_session_id()
            if session_id in self.active_sessions:
                session_data = self.active_sessions.pop(session_id)
                logger.info(
                    f"Client disconnected: session_id={session_id}, "
                    f"chunks={session_data['chunks_received']}, "
                    f"drafts={session_data['drafts_sent']}, "
                    f"verified={session_data['verified_sent']}"
                )
        
        @self.socketio.on('audio_chunk')
        def handle_audio_chunk(data: Dict[str, Any]):
            """
            Handle audio chunk from client.
            
            Expected data format:
            {
                "data": "base64_encoded_audio",
                "timestamp": 1737234567890,
                "sequence": 42
            }
            """
            session_id = self._get_session_id()
            
            try:
                # Validate data
                if 'data' not in data:
                    emit('error', {'message': 'Missing audio data'})
                    return
                
                # Decode base64 audio
                try:
                    audio_bytes = base64.b64decode(data['data'])
                except Exception as e:
                    logger.error(f"Failed to decode base64 audio: {e}")
                    emit('error', {'message': 'Invalid audio data encoding'})
                    return
                
                # Update session stats
                if session_id in self.active_sessions:
                    self.active_sessions[session_id]['chunks_received'] += 1
                
                # Call orchestrator callback if provided
                if self.orchestrator_callback:
                    try:
                        self.orchestrator_callback(audio_bytes, session_id, data)
                    except Exception as e:
                        logger.error(f"Orchestrator callback error: {e}", exc_info=True)
                        emit('error', {'message': f'Processing error: {str(e)}'})
                else:
                    logger.warning("No orchestrator callback registered")
                
                # Acknowledge receipt
                emit('chunk_received', {
                    'sequence': data.get('sequence', 0),
                    'timestamp': data.get('timestamp', time.time() * 1000)
                })
                
            except Exception as e:
                logger.error(f"Error handling audio chunk: {e}", exc_info=True)
                emit('error', {'message': f'Server error: {str(e)}'})
        
        @self.socketio.on('ping')
        def handle_ping():
            """Handle ping from client."""
            emit('pong', {'timestamp': time.time() * 1000})
    
    def emit_draft_caption(
        self,
        session_id: str,
        segment_id: str,
        start: float,
        end: float,
        text: str,
        confidence: float,
        gurmukhi: Optional[str] = None,
        roman: Optional[str] = None
    ) -> None:
        """
        Emit draft caption to client.
        
        Args:
            session_id: Client session ID
            segment_id: Unique segment identifier
            start: Start timestamp (seconds)
            end: End timestamp (seconds)
            text: Draft text (may be ASR-A output)
            confidence: Confidence score (0.0-1.0)
            gurmukhi: Gurmukhi text (if available)
            roman: Roman transliteration (if available)
        """
        try:
            message = {
                'type': 'draft',
                'segment_id': segment_id,
                'start': start,
                'end': end,
                'text': text,
                'confidence': confidence,
                'timestamp': time.time() * 1000
            }
            
            if gurmukhi:
                message['gurmukhi'] = gurmukhi
            if roman:
                message['roman'] = roman
            
            self.socketio.emit('draft_caption', message, room=session_id)
            
            # Update session stats
            if session_id in self.active_sessions:
                self.active_sessions[session_id]['drafts_sent'] += 1
            
            logger.debug(f"Emitted draft caption: session_id={session_id}, segment_id={segment_id}")
            
        except Exception as e:
            logger.error(f"Error emitting draft caption: {e}", exc_info=True)
    
    def emit_verified_update(
        self,
        session_id: str,
        segment_id: str,
        start: float,
        end: float,
        gurmukhi: str,
        roman: str,
        confidence: float,
        quote_match: Optional[Dict[str, Any]] = None,
        needs_review: bool = False
    ) -> None:
        """
        Emit verified transcription update to client.
        
        Args:
            session_id: Client session ID
            segment_id: Unique segment identifier (should match draft)
            start: Start timestamp (seconds)
            end: End timestamp (seconds)
            gurmukhi: Verified Gurmukhi text
            roman: Verified Roman transliteration
            confidence: Final confidence score
            quote_match: Quote match metadata if applicable
            needs_review: Whether segment needs human review
        """
        try:
            message = {
                'type': 'verified',
                'segment_id': segment_id,
                'start': start,
                'end': end,
                'gurmukhi': gurmukhi,
                'roman': roman,
                'confidence': confidence,
                'needs_review': needs_review,
                'timestamp': time.time() * 1000
            }
            
            if quote_match:
                message['quote_match'] = quote_match
            
            self.socketio.emit('verified_update', message, room=session_id)
            
            # Update session stats
            if session_id in self.active_sessions:
                self.active_sessions[session_id]['verified_sent'] += 1
            
            logger.debug(f"Emitted verified update: session_id={session_id}, segment_id={segment_id}")
            
        except Exception as e:
            logger.error(f"Error emitting verified update: {e}", exc_info=True)
    
    def emit_error(self, session_id: str, message: str, error_type: str = "processing") -> None:
        """
        Emit error message to client.
        
        Args:
            session_id: Client session ID
            message: Error message
            error_type: Error type (e.g., "processing", "connection")
        """
        try:
            self.socketio.emit('error', {
                'type': error_type,
                'message': message,
                'timestamp': time.time() * 1000
            }, room=session_id)
            logger.warning(f"Emitted error to session {session_id}: {message}")
        except Exception as e:
            logger.error(f"Error emitting error message: {e}", exc_info=True)
    
    def _get_session_id(self) -> str:
        """
        Get current session ID from Flask request context.
        
        Returns:
            Session ID string
        """
        from flask import request
        # Use SocketIO's session ID
        return request.sid if hasattr(request, 'sid') else 'unknown'
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Session statistics dict or None if session not found
        """
        return self.active_sessions.get(session_id)
    
    def run(self, host: str = "0.0.0.0", port: int = 5000, debug: bool = False) -> None:
        """
        Run the SocketIO server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            debug: Enable debug mode
        """
        logger.info(f"Starting WebSocket server on {host}:{port}")
        self.socketio.run(self.app, host=host, port=port, debug=debug)
