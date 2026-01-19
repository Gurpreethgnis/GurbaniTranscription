# Phase 6: Live Transcription Testing Guide

## Prerequisites

1. **Install Phase 6 Dependencies**
   ```bash
   pip install flask-socketio>=5.3.0 python-socketio>=5.10.0 python-engineio>=4.8.0 eventlet>=0.35.0
   ```

2. **Verify Dependencies**
   ```bash
   pip list | grep -i socket
   pip list | grep -i eventlet
   ```

## Testing Steps

### 1. Start the Server

```bash
python app.py
```

You should see:
- "Initializing Whisper service..."
- "Initializing WebSocket server for live mode..."
- "Starting server with WebSocket support on http://0.0.0.0:5000"

### 2. Access Live Transcription Page

Open your browser and navigate to:
```
http://localhost:5000/live
```

### 3. Test WebSocket Connection

1. **Check Connection Status**
   - The status indicator should show "Connected" (green)
   - Check browser console (F12) for "Connected to server" message

2. **Verify Session ID**
   - Check browser console for "Session ID: [id]"
   - This confirms WebSocket handshake succeeded

### 4. Test Audio Capture

1. **Click "Start Recording"**
   - Browser will prompt for microphone permission
   - Grant permission
   - Status should change to "Recording..." (yellow)
   - Start button should be disabled
   - Stop button should be enabled

2. **Speak into Microphone**
   - Speak in Punjabi, English, or mixed
   - Try saying some Gurbani quotes if possible
   - Watch for draft captions appearing

### 5. Verify Draft Captions

- Draft captions should appear within ~1-2 seconds after speaking
- They should have yellow border (draft style)
- Should show "Draft (awaiting verification...)" label
- Confidence badge should be visible

### 6. Verify Verified Updates

- After 2-3 seconds, draft should be replaced with verified version
- Verified segments have green border
- If quote detected, should have purple border and show metadata
- Quote metadata should show: Source, Ang, Raag, Author (if available)

### 7. Test Output Modes

- Toggle between "Gurmukhi", "Roman", and "Both"
- Verify text updates correctly for each mode

### 8. Test Stop Recording

- Click "Stop Recording"
- Recording should stop
- Status should change to "Stopped (still connected)"
- Microphone should be released

## Expected Behavior

### Draft Captions
- **Latency**: < 500ms after speech ends
- **Content**: ASR-A output (may be in Shahmukhi/Urdu)
- **Style**: Yellow border, semi-transparent

### Verified Updates
- **Latency**: < 3 seconds behind draft
- **Content**: 
  - Gurmukhi text (normalized)
  - Roman transliteration
  - Quote metadata (if matched)
- **Style**: Green border (purple if quote)

### Quote Detection
- Quotes should be highlighted with purple border
- Metadata tooltip should show:
  - Source (SGGS, Dasam, etc.)
  - Ang (page number)
  - Raag
  - Author (if available)

## Troubleshooting

### Issue: "Disconnected" Status

**Possible Causes:**
- Server not running
- WebSocket server not initialized
- Port conflict

**Solutions:**
- Check server logs for errors
- Verify port 5000 is not in use
- Check browser console for connection errors

### Issue: Microphone Permission Denied

**Solutions:**
- Grant microphone permission in browser settings
- Use HTTPS (required for microphone access in some browsers)
- Check browser console for permission errors

### Issue: No Draft Captions Appearing

**Possible Causes:**
- Audio not being captured
- WebSocket not sending audio chunks
- Orchestrator not processing chunks

**Solutions:**
- Check browser console for errors
- Verify audio stream is active (check MediaRecorder state)
- Check server logs for processing errors
- Verify ASR models are loaded

### Issue: Draft Captions but No Verified Updates

**Possible Causes:**
- Quote detection taking too long
- Script conversion failing
- Orchestrator callback not working

**Solutions:**
- Check server logs for errors
- Verify script converter is initialized
- Check quote detection services are available

### Issue: Audio Format Errors

**Possible Causes:**
- Browser doesn't support WebM/Opus
- Audio encoding issues

**Solutions:**
- Try different browser (Chrome recommended)
- Check browser console for MediaRecorder errors
- Verify audio stream format

## Browser Compatibility

- **Chrome/Edge**: Full support (recommended)
- **Firefox**: Should work, may need HTTPS
- **Safari**: Limited support (may need polyfills)

## Performance Expectations

- **Draft Latency**: 500ms - 2s
- **Verified Latency**: 2s - 5s
- **Memory Usage**: ~200-500MB per session
- **CPU Usage**: Moderate (depends on ASR model size)

## Testing Checklist

- [ ] Server starts without errors
- [ ] WebSocket connection established
- [ ] Microphone permission granted
- [ ] Recording starts successfully
- [ ] Draft captions appear
- [ ] Verified updates replace drafts
- [ ] Quote detection works (if applicable)
- [ ] Output mode toggle works
- [ ] Stop recording works
- [ ] No memory leaks (test 10+ minutes)
- [ ] Multiple sessions work (if testing)

## Next Steps After Testing

1. Report any issues found
2. Verify all features work as expected
3. Test with real Katha audio
4. Check performance metrics
5. Create test suite (test_phase6.py)
