# 🔧 Troubleshooting Guide

## "Failed to Fetch" Error in Browser

### Issue Overview
You see "Failed to fetch" error when trying to process a video through the web interface.

### Quick Diagnosis

**1. Check if server is running:**
```bash
curl http://localhost:5001/api/status
```

**Expected response:**
```json
{
  "status": "online",
  "services": {
    "gemini": "configured",
    "deepgram": "configured",
    "ffmpeg": "available"
  }
}
```

✅ If you get this response, server is running correctly!

### Common Causes & Solutions

---

## Cause 1: Server Not Running ❌

**Symptom:** `curl` returns "Connection refused"

**Solution:**
```bash
cd "/Users/gervaciusjr/Desktop/ALL FILES/YT automation"
./run.sh
```

Or manually:
```bash
cd "/Users/gervaciusjr/Desktop/ALL FILES/YT automation"
source venv/bin/activate
python3 app.py
```

---

## Cause 2: Port Already in Use ⚠️

**Symptom:** Terminal shows "Address already in use" or "Port 5001 is in use"

**Solution 1 - Kill existing process:**
```bash
# Find process using port 5001
lsof -ti:5001

# Kill it
lsof -ti:5001 | xargs kill -9

# Restart server
./run.sh
```

**Solution 2 - Use different port:**

Edit `app.py`, line ~214:
```python
app.run(debug=True, host='0.0.0.0', port=5002)  # Changed from 5001
```

Then access: `http://localhost:5002`

---

## Cause 3: Browser Cache Issues 🌐

**Symptom:** Server works with `curl` but not in browser

**Solution:**

1. **Hard refresh the page:**
   - **Chrome/Edge:** `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
   - **Firefox:** `Cmd+Shift+R` (Mac) or `Ctrl+F5` (Windows)
   - **Safari:** `Cmd+Option+R`

2. **Clear browser cache:**
   - Chrome: Settings → Privacy → Clear browsing data
   - Check "Cached images and files"
   - Time range: "Last hour"

3. **Try Incognito/Private window:**
   - Chrome: `Cmd+Shift+N`
   - Firefox: `Cmd+Shift+P`
   - Safari: `Cmd+Shift+N`

---

## Cause 4: CORS Issues (Cross-Origin) 🔒

**Symptom:** Browser console shows CORS error

**Check:** Open browser Developer Tools (F12) → Console tab

**Solution:**

Our app already has CORS enabled in `app.py`:
```python
from flask_cors import CORS
CORS(app)
```

If still having issues, check `app.py` line 23 has:
```python
CORS(app)
```

---

## Cause 5: File Size Too Large 📦

**Symptom:** Upload starts but fails immediately

**Our limit:** 500MB (set in `app.py`)

**Check file size:**
```bash
ls -lh your_video.mp4
```

**Solution:**
- Use videos under 500MB
- Or increase limit in `app.py` line 24:
```python
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 1GB
```

---

## Cause 6: Browser JavaScript Disabled ⚙️

**Solution:**
1. Check browser settings
2. Ensure JavaScript is enabled
3. Check for ad blockers that might block requests

---

## Cause 7: Firewall/Antivirus Blocking 🛡️

**macOS:**
```bash
# Allow Python through firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/python3
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/local/bin/python3
```

**Check if firewall is blocking:**
```bash
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
```

---

## Diagnostic Steps

### Step 1: Test Server Health

```bash
curl http://localhost:5001/api/status
```

**Expected:** JSON response with "status": "online"

### Step 2: Check Browser Console

1. Open browser (Chrome, Firefox, Safari)
2. Press `F12` or `Cmd+Option+I`
3. Click "Console" tab
4. Try uploading video
5. Look for error messages

**Common errors:**
- `ERR_CONNECTION_REFUSED` → Server not running
- `CORS policy` → CORS configuration issue
- `Failed to fetch` → Network/firewall issue

### Step 3: Check Server Logs

Server logs appear in terminal where you ran `./run.sh`

Look for:
- `Starting Flask server on http://127.0.0.1:5001` ✅ Good
- `Address already in use` ❌ Port conflict
- Error tracebacks ❌ Server errors

### Step 4: Test with curl

```bash
# Create test form data
curl -X POST http://localhost:5001/api/process \
  -F "drive_url=https://drive.google.com/file/d/YOUR_FILE_ID/view"
```

If curl works but browser doesn't → Browser issue
If curl fails too → Server issue

---

## Advanced Troubleshooting

### Check Python Process

```bash
# List Python processes
ps aux | grep python

# Should see: python3 app.py
```

### Check Network Listeners

```bash
# macOS/Linux
lsof -i :5001

# Should show Python listening on port 5001
```

### Test Different Browser

Try:
1. Chrome
2. Firefox
3. Safari
4. Brave

If works in one but not another → Browser-specific issue

### Check System Resources

```bash
# Check available memory
vm_stat

# Check disk space
df -h

# Ensure you have:
# - At least 2GB free RAM
# - At least 10GB free disk space
```

---

## Quick Fixes Checklist

- [ ] Server is running (`./run.sh`)
- [ ] Port 5001 is not in use
- [ ] Browser cache cleared
- [ ] Tried incognito/private window
- [ ] JavaScript enabled in browser
- [ ] No ad blockers interfering
- [ ] Firewall allows connections
- [ ] File size under 500MB
- [ ] Console shows no errors

---

## Still Not Working?

### Restart Everything

```bash
# 1. Stop server
pkill -f "python.*app.py"

# 2. Kill port if stuck
lsof -ti:5001 | xargs kill -9

# 3. Clear Python cache
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null

# 4. Restart server
./run.sh
```

### Test with Simple HTML

Create `test.html` in project root:

```html
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<button onclick="testAPI()">Test Server</button>
<pre id="result"></pre>
<script>
async function testAPI() {
  try {
    const response = await fetch('http://localhost:5001/api/status');
    const data = await response.json();
    document.getElementById('result').textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    document.getElementById('result').textContent = 'ERROR: ' + error.message;
  }
}
</script>
</body>
</html>
```

Open `test.html` in browser, click button. Should show status JSON.

---

## Error Messages Explained

### "Failed to fetch"
**Meaning:** Browser couldn't connect to server
**Check:** Server running? Correct URL? CORS enabled?

### "Connection refused"
**Meaning:** Nothing listening on that port
**Fix:** Start the server

### "Address already in use"
**Meaning:** Another process using port 5001
**Fix:** Kill that process or use different port

### "TypeError: Failed to fetch"
**Meaning:** Network request failed
**Common causes:** Server offline, CORS, firewall

### "413 Request Entity Too Large"
**Meaning:** File too big
**Fix:** Increase `MAX_CONTENT_LENGTH` in `app.py`

### "504 Gateway Timeout"
**Meaning:** Request took too long
**Note:** Video processing can take 10+ minutes for long videos

---

## Working Configuration Checklist

Ensure you have:

✅ **Python 3.8+** installed
✅ **FFmpeg** installed (`ffmpeg -version`)
✅ **Virtual environment** activated
✅ **Dependencies** installed (`pip install -r requirements.txt`)
✅ **Server running** on port 5001
✅ **Browser** at `http://localhost:5001`
✅ **No firewall** blocking
✅ **CORS enabled** in `app.py`

---

## Contact Info / Debug Info

If you need help, provide:

1. **Error message** from browser console (F12)
2. **Server logs** from terminal
3. **curl test result:**
   ```bash
   curl -v http://localhost:5001/api/status
   ```
4. **System info:**
   - OS: macOS / Windows / Linux
   - Browser: Chrome / Firefox / Safari
   - Python version: `python3 --version`
   - FFmpeg version: `ffmpeg -version`

---

## Known Working Setup

✅ **Tested and working on:**
- macOS 14+ (Sonoma)
- Python 3.12.8
- FFmpeg 8.0
- Chrome 120+
- Firefox 121+
- Safari 17+

---

**Last Updated:** October 21, 2025

