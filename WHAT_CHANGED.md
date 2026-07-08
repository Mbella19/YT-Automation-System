# What Changed — Review Fixes & Autonomy Upgrade

This pass fixed the bugs found in review, hardened the app, and added a fully
autonomous mode (no manual script paste required). Every changed code path was
verified locally (endpoints, TTS, and the FFmpeg pipeline with a real video).

## 🔑 Keys & model
- New AI Studio key wired via `.env` (`GEMINI_API_KEY` / `GEMINI_TTS_API_KEY`).
  **Tested against the live API before switching** — it authenticates for the LLM
  and for native TTS.
- Model changed to **`gemini-3.5-flash`** at **`thinking_level: high`** (verified
  the model exists and accepts high thinking).
- ⚠️ The two **old keys are still in git history** (`config.py` in early commits).
  Revoke them in Google Cloud — removing them from the current file is not enough.

## 🔊 TTS migration (was broken with the new key)
- The old code called **Google Cloud TTS** (`texttospeech.googleapis.com`), which
  **rejects API keys** (needs OAuth2). Your new key returned 401 there.
- `utils/gemini_tts.py` now uses **Gemini's native TTS** over the same API the key
  works on. PCM output is wrapped into a **WAV** file (readable by ffprobe/ffmpeg).
  This also matches the original `GEMINI_TTS_MODEL` config intent.

## 🐛 Bugs fixed
1. **Retry logic never caught real API errors** — `_execute_with_retry` only caught
   `httpx` errors, but the SDK raises `google.genai.errors.APIError`. Now retries on
   429/5xx, raises immediately on 400/401/403/404. (Unit-tested.)
2. **Script sent twice** — the frontend sent the script as both `script_text` **and**
   `instructions`, double-injecting it into the prompt. Fixed.
3. **Duplicate scenes on failed split** — when script-trimming failed on the final
   retry, the next chunk re-processed the same script. Now the script is advanced by
   the approximate consumed length so chunks don't overlap.
4. **Timestamps not clamped** — hallucinated timestamps beyond a chunk could push a
   clip past EOF. Now clamped to the chunk bounds; inverted/out-of-bounds scenes are
   dropped. (Unit-tested.)
5. **`adelay` truncated narration** — with a start delay, the clip length didn't
   include the delay, cutting off the narration tail. Now `duration = audio + delay`.
   (Verified with a real clip: 4.49s audio + 0.2s delay → 4.7s clip.)
6. **`.gitignore` had merge-conflict markers** (`=======` / `>>>>>>>`) and dupes —
   cleaned up.
7. **Dead no-op in the split matcher** removed; switched to a forward search so
   repeated phrases don't over-trim the script. (Unit-tested.)

## 🔒 Security & robustness
- `debug`, `host`, `port` now come from config; **default is `127.0.0.1` with debug
  off** (was `debug=True, host=0.0.0.0` — a remote-code-execution surface).
- **Upload size cap** enforced (`MAX_UPLOAD_MB`, default 2 GB) — was disabled.
- **CORS** restricted to configured origins (`CORS_ORIGINS`).
- **Download endpoint** uses `send_from_directory` (path-traversal safe); a missing
  file now returns 404, not 500. (Tested with encoded `../` payloads.)
- **Temp cleanup**: the source video + chunks are deleted after clips render, and
  **uploaded Gemini files are deleted** after each chunk to avoid quota buildup.

## ⚙️ Config that was silently ignored — now honored
- `GEMINI_TEMPERATURE` / `GEMINI_TIMESTAMP_TEMPERATURE` (were overridden by a
  hardcoded `0.0`).
- `GEMINI_THINKING_LEVEL` (was never sent).
- `USE_AUDIO_BASED_TIMING` (now actually toggles timing mode).
- `CLIP_DURATION_MIN/MAX` (now drive the prompt instead of hardcoded "5–20s").
- Removed the dead `GEMINI_TWO_PASS_ANALYSIS` flag and misleading comments.

## 🤖 Autonomy (the main goal)
- New `GeminiVideoAnalyzer.generate_scenes_from_video()` — Gemini watches the video
  and **writes** the recap narration with timestamps, in movie-recap style.
- `app.py` makes `script_text` **optional**: blank script → autonomous generation
  (controlled by `AUTO_GENERATE_SCRIPT`, default on). Pasting a script still aligns
  it exactly as before.
- Frontend: script box is now optional with "leave blank to auto-generate" guidance.

## ▶️ How to run
```bash
cp .env.example .env      # then paste your key (already done in this repo's .env)
pip install -r requirements.txt
python app.py             # serves http://127.0.0.1:5001
```

## 🧵 Phase 2 — Background jobs + YouTube upload (now done)

### Background job queue (`utils/job_manager.py`)
- Processing no longer blocks the HTTP request. `POST /api/process` saves the input
  and returns **`202`** with a `job_id` immediately.
- A single background worker runs jobs FIFO; state is persisted to
  `outputs/<job_id>/job.json`, so results **survive a page refresh or server
  restart**.
- New endpoints: `GET /api/jobs/<job_id>` (status/stage/result),
  `GET /api/jobs` (list). The frontend now **polls** the job and no longer shows
  fake progress; the SSE log stream still drives the live terminal.
- Verified end-to-end over real HTTP: enqueue → running → completed → download.

### YouTube auto-upload (`utils/youtube_uploader.py`)
- Optional: tick "Auto-upload to YouTube" and pick privacy (defaults to **private**
  so nothing publishes unexpectedly).
- Uploads use **OAuth2** (the Data API can't upload with an API key). One-time
  sign-in: `python -m utils.youtube_uploader` (needs an OAuth *client* secrets file
  from Google Cloud, saved as `client_secrets.json`). The token is cached in
  `youtube_token.json` and auto-refreshes. Both files are **gitignored**.
- Title/description/tags are generated by Gemini from the recap script
  (`generate_youtube_metadata`, live-tested). A failed upload is **non-fatal** —
  the video is still produced and downloadable.
- `GET /api/youtube/status` tells the UI whether upload is available.

### One-time YouTube setup
1. Google Cloud Console → enable **YouTube Data API v3**.
2. Create an **OAuth client ID → Desktop app**, download JSON to `client_secrets.json`.
3. Run `python -m utils.youtube_uploader` once and complete consent.
4. The "Auto-upload to YouTube" toggle in the UI becomes enabled.

## 🎬 Phase 3 — Real-movie test (Weapons 2025) + TTS 429 fix

Ran the full pipeline on a 12-minute excerpt of a real 1080p film in autonomous
mode (no script). Results:
- Split into 2 chunks; **Gemini generated 15 coherent recap scenes** with correct
  character names, plot beats, 5–20s durations, ~10s gaps, and correct cross-chunk
  timestamp offset. The autonomous mode works on real footage.
- The test caught a real bug: **the TTS path had no rate-limit handling**, so a
  free-tier 429 (the TTS model allows ~3 requests/min) failed the whole job.

### Fix: TTS retry + rate-limit resilience
- Retries 429/5xx honoring the server's suggested `retryDelay` ("Please retry in Ns").
- `GEMINI_TTS_MAX_WAIT_SECONDS` cap: a longer delay means a daily-quota window, so it
  stops retrying instead of blocking the job for minutes/hours.
- `GEMINI_TTS_SKIP_FAILED_SCENES` (default on): a scene that still fails is skipped
  (its clip is omitted) rather than failing the whole recap; only fails if *no*
  scene produced audio.
- Optional proactive pacing via `GEMINI_TTS_DELAY_SECONDS`.
- Verified: recovered a scene after a real free-tier 429.

### ⚠️ Practical note: enable billing
The provided key is on the **Gemini free tier**, whose TTS quota (~3 req/min, plus a
low daily cap) makes a full-length recap slow and prone to hitting daily limits.
For real use, enable billing on the Google Cloud project so TTS isn't throttled.

## 🔭 Still open (nice-to-have)
- Auto-generated **thumbnails** (Gemini image model + `thumbnails.set`).
- Multiple concurrent workers if you outgrow one (currently intentional FIFO).
