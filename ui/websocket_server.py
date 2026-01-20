"""
WebSocket server for live transcription streaming.

Handles real-time audio streaming, draft caption delivery, and verified
transcription updates via WebSocket connections.

Phase 6: Live Mode + WebSocket UI
Phase 15: Shabad Mode with Praman Suggestions
"""
import logging
import base64
import io
import time
from typing import Dict, Optional, Any, Callable, List
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
    - Shabad mode with praman suggestions (Phase 15)
    """
    
    def __init__(
        self,
        app: Flask,
        orchestrator_callback: Optional[Callable] = None,
        shabad_callback: Optional[Callable] = None
    ):
        """
        Initialize WebSocket server.
        
        Args:
            app: Flask application instance
            orchestrator_callback: Callback function to process audio chunks
                                 Signature: (audio_data: bytes, session_id: str, data: dict) -> None
            shabad_callback: Callback function for shabad mode processing
                           Signature: (audio_data: bytes, session_id: str, data: dict) -> dict
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
        self.shabad_callback = shabad_callback
        
        # Track active sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Track shabad mode sessions and their preferences
        self.shabad_sessions: Dict[str, Dict[str, Any]] = {}
        
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
        
        # ==========================================
        # Shabad Mode Event Handlers (Phase 15)
        # ==========================================
        
        @self.socketio.on('shabad_start')
        def handle_shabad_start(data: Dict[str, Any]):
            """
            Handle start of shabad mode session.
            
            Expected data:
            {
                "similar_count": 5,
                "dissimilar_count": 3,
                "show_similar": true,
                "show_dissimilar": true
            }
            """
            session_id = self._get_session_id()
            
            # Initialize shabad session with preferences
            self.shabad_sessions[session_id] = {
                'started_at': time.time(),
                'similar_count': data.get('similar_count', 5),
                'dissimilar_count': data.get('dissimilar_count', 3),
                'show_similar': data.get('show_similar', True),
                'show_dissimilar': data.get('show_dissimilar', True),
                'chunks_processed': 0,
                'shabads_detected': 0
            }
            
            logger.info(f"Shabad mode started: session_id={session_id}")
            emit('shabad_started', {
                'session_id': session_id,
                'status': 'ok',
                'preferences': self.shabad_sessions[session_id]
            })
        
        @self.socketio.on('shabad_stop')
        def handle_shabad_stop():
            """Handle stop of shabad mode session."""
            session_id = self._get_session_id()
            
            if session_id in self.shabad_sessions:
                session_data = self.shabad_sessions.pop(session_id)
                logger.info(
                    f"Shabad mode stopped: session_id={session_id}, "
                    f"chunks={session_data['chunks_processed']}, "
                    f"shabads={session_data['shabads_detected']}"
                )
            
            emit('shabad_stopped', {'session_id': session_id, 'status': 'ok'})
        
        @self.socketio.on('shabad_audio_chunk')
        def handle_shabad_audio_chunk(data: Dict[str, Any]):
            """
            Handle audio chunk for shabad mode processing.
            
            Expected data format:
            {
                "data": "base64_encoded_audio",
                "timestamp": 1737234567890,
                "sequence": 42,
                "similar_count": 5,
                "dissimilar_count": 3
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
                
                # Get preferences from session or data
                prefs = self.shabad_sessions.get(session_id, {})
                similar_count = data.get('similar_count', prefs.get('similar_count', 5))
                dissimilar_count = data.get('dissimilar_count', prefs.get('dissimilar_count', 3))
                
                # Update session stats
                if session_id in self.shabad_sessions:
                    self.shabad_sessions[session_id]['chunks_processed'] += 1
                
                # Call shabad callback if provided
                if self.shabad_callback:
                    try:
                        result = self.shabad_callback(
                            audio_bytes,
                            session_id,
                            {
                                **data,
                                'similar_count': similar_count,
                                'dissimilar_count': dissimilar_count
                            }
                        )
                        
                        # Track shabads detected
                        if result and result.get('matched_line'):
                            if session_id in self.shabad_sessions:
                                self.shabad_sessions[session_id]['shabads_detected'] += 1
                        
                    except Exception as e:
                        logger.error(f"Shabad callback error: {e}", exc_info=True)
                        emit('error', {'message': f'Shabad processing error: {str(e)}'})
                else:
                    logger.warning("No shabad callback registered")
                
                # Acknowledge receipt
                emit('shabad_chunk_received', {
                    'sequence': data.get('sequence', 0),
                    'timestamp': data.get('timestamp', time.time() * 1000)
                })
                
            except Exception as e:
                logger.error(f"Error handling shabad audio chunk: {e}", exc_info=True)
                emit('error', {'message': f'Server error: {str(e)}'})
        
        @self.socketio.on('shabad_preferences')
        def handle_shabad_preferences(data: Dict[str, Any]):
            """
            Handle shabad mode preference updates.
            
            Expected data:
            {
                "similar_count": 5,
                "dissimilar_count": 3,
                "show_similar": true,
                "show_dissimilar": true
            }
            """
            session_id = self._get_session_id()
            
            if session_id in self.shabad_sessions:
                # Update preferences
                if 'similar_count' in data:
                    self.shabad_sessions[session_id]['similar_count'] = data['similar_count']
                if 'dissimilar_count' in data:
                    self.shabad_sessions[session_id]['dissimilar_count'] = data['dissimilar_count']
                if 'show_similar' in data:
                    self.shabad_sessions[session_id]['show_similar'] = data['show_similar']
                if 'show_dissimilar' in data:
                    self.shabad_sessions[session_id]['show_dissimilar'] = data['show_dissimilar']
                
                logger.debug(f"Shabad preferences updated: session_id={session_id}")
                emit('shabad_preferences_updated', {
                    'status': 'ok',
                    'preferences': self.shabad_sessions[session_id]
                })
            else:
                emit('error', {'message': 'No active shabad session'})
        
        @self.socketio.on('shabad_reset')
        def handle_shabad_reset():
            """Handle shabad context reset request."""
            session_id = self._get_session_id()
            logger.info(f"Shabad context reset requested: session_id={session_id}")
            emit('shabad_context_reset', {'session_id': session_id, 'status': 'ok'})
    
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
    
    # ==========================================
    # Shabad Mode Emit Methods (Phase 15)
    # ==========================================
    
    def emit_shabad_update(
        self,
        session_id: str,
        matched_line: Optional[Dict[str, Any]] = None,
        next_line: Optional[Dict[str, Any]] = None,
        shabad_info: Optional[Dict[str, Any]] = None,
        transcribed_text: str = "",
        audio_mode: str = "unknown",
        mode_confidence: float = 0.0,
        match_confidence: float = 0.0,
        is_new_shabad: bool = False,
        start_time: float = 0.0,
        end_time: float = 0.0
    ) -> None:
        """
        Emit shabad line update to client.
        
        Args:
            session_id: Client session ID
            matched_line: Matched shabad line info
            next_line: Next line in the shabad
            shabad_info: Current shabad context info
            transcribed_text: Transcribed text from ASR
            audio_mode: Detected audio mode (shabad/katha)
            mode_confidence: Mode detection confidence
            match_confidence: Line match confidence
            is_new_shabad: Whether this is a new shabad
            start_time: Audio chunk start time
            end_time: Audio chunk end time
        """
        try:
            message = {
                'type': 'shabad_update',
                'session_id': session_id,
                'transcribed_text': transcribed_text,
                'audio_mode': audio_mode,
                'mode_confidence': mode_confidence,
                'match_confidence': match_confidence,
                'is_new_shabad': is_new_shabad,
                'start_time': start_time,
                'end_time': end_time,
                'timestamp': time.time() * 1000
            }
            
            if matched_line:
                message['matched_line'] = matched_line
            if next_line:
                message['next_line'] = next_line
            if shabad_info:
                message['shabad_info'] = shabad_info
            
            self.socketio.emit('shabad_update', message, room=session_id)
            logger.debug(f"Emitted shabad update: session_id={session_id}")
            
        except Exception as e:
            logger.error(f"Error emitting shabad update: {e}", exc_info=True)
    
    def emit_praman_suggestions(
        self,
        session_id: str,
        similar_pramans: List[Dict[str, Any]],
        dissimilar_pramans: List[Dict[str, Any]],
        query_line_id: Optional[str] = None
    ) -> None:
        """
        Emit praman suggestions to client.
        
        Args:
            session_id: Client session ID
            similar_pramans: List of similar praman results
            dissimilar_pramans: List of dissimilar praman results
            query_line_id: Line ID that was used for the query
        """
        try:
            # Apply session preferences for filtering
            prefs = self.shabad_sessions.get(session_id, {})
            show_similar = prefs.get('show_similar', True)
            show_dissimilar = prefs.get('show_dissimilar', True)
            
            message = {
                'type': 'praman_suggestions',
                'session_id': session_id,
                'query_line_id': query_line_id,
                'similar_pramans': similar_pramans if show_similar else [],
                'dissimilar_pramans': dissimilar_pramans if show_dissimilar else [],
                'timestamp': time.time() * 1000
            }
            
            self.socketio.emit('praman_suggestions', message, room=session_id)
            logger.debug(
                f"Emitted praman suggestions: session_id={session_id}, "
                f"similar={len(similar_pramans)}, dissimilar={len(dissimilar_pramans)}"
            )
            
        except Exception as e:
            logger.error(f"Error emitting praman suggestions: {e}", exc_info=True)
    
    def emit_shabad_full_update(
        self,
        session_id: str,
        shabad_result: Dict[str, Any]
    ) -> None:
        """
        Emit combined shabad update with line and pramans.
        
        Args:
            session_id: Client session ID
            shabad_result: Full result from orchestrator.process_shabad_audio_chunk()
        """
        try:
            # Emit shabad line update
            self.emit_shabad_update(
                session_id=session_id,
                matched_line=shabad_result.get('matched_line'),
                next_line=shabad_result.get('next_line'),
                shabad_info=shabad_result.get('shabad_info'),
                transcribed_text=shabad_result.get('transcribed_text', ''),
                audio_mode=shabad_result.get('audio_mode', 'unknown'),
                mode_confidence=shabad_result.get('mode_confidence', 0.0),
                match_confidence=shabad_result.get('match_confidence', 0.0),
                is_new_shabad=shabad_result.get('is_new_shabad', False),
                start_time=shabad_result.get('start_time', 0.0),
                end_time=shabad_result.get('end_time', 0.0)
            )
            
            # Emit praman suggestions if available
            if shabad_result.get('similar_pramans') or shabad_result.get('dissimilar_pramans'):
                self.emit_praman_suggestions(
                    session_id=session_id,
                    similar_pramans=shabad_result.get('similar_pramans', []),
                    dissimilar_pramans=shabad_result.get('dissimilar_pramans', []),
                    query_line_id=shabad_result.get('matched_line', {}).get('line_id')
                )
            
        except Exception as e:
            logger.error(f"Error emitting shabad full update: {e}", exc_info=True)
    
    def get_shabad_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a shabad session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Shabad session statistics dict or None if session not found
        """
        return self.shabad_sessions.get(session_id)
    
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
