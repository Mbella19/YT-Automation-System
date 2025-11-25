document.addEventListener('DOMContentLoaded', () => {
    const sections = {
        upload: document.getElementById('step-upload'),
        processing: document.getElementById('step-processing'),
        results: document.getElementById('step-results'),
    };

    const uploadForm = document.getElementById('uploadForm');
    const videoInput = document.getElementById('videoFile');
    const movieTitleInput = document.getElementById('movieTitle');
    const browseButton = document.getElementById('browseButton');
    const selectedFileName = document.getElementById('selectedFileName');
    const driveUrlInput = document.getElementById('driveUrl');
    const instructionsInput = document.getElementById('instructions');
    const submitBtn = document.getElementById('submitBtn');
    const uploadAlert = document.getElementById('uploadAlert');

    const processingSubtitle = document.getElementById('processingSubtitle');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const processingMovieTitle = document.getElementById('processingMovieTitle');
    const processingInputName = document.getElementById('processingInputName');
    const processingStage = document.getElementById('processingStage');
    const processingStartTime = document.getElementById('processingStartTime');
    const logContent = document.getElementById('logContent');
    const processingError = document.getElementById('processingError');
    const processingBackBtn = document.getElementById('processingBackBtn');

    const resultMovieTitle = document.getElementById('resultMovieTitle');
    const resultScenesCount = document.getElementById('resultScenesCount');
    const resultClipsCount = document.getElementById('resultClipsCount');
    const sceneList = document.getElementById('sceneList');
    const sceneMeta = document.getElementById('sceneMeta');
    const sceneTitle = document.getElementById('sceneTitle');
    const fullRecapScript = document.getElementById('fullRecapScript');
    const alignmentNotes = document.getElementById('alignmentNotes');
    const sceneNarration = document.getElementById('sceneNarration');
    const currentClipDownload = document.getElementById('currentClipDownload');
    const noClipMessage = document.getElementById('noClipMessage');
    const clipDownloads = document.getElementById('clipDownloads');
    const downloadScriptBtn = document.getElementById('downloadScriptBtn');
    const downloadScenesBtn = document.getElementById('downloadScenesBtn');
    const downloadFinalBtn = document.getElementById('downloadFinalBtn');
    const processAnotherBtn = document.getElementById('processAnotherBtn');

    const defaultSubmitMarkup = submitBtn ? submitBtn.innerHTML : '';

    const state = {
        result: null,
        currentSceneIndex: null,
        sessionId: null,
        logEventSource: null,
    };

    function showSection(target) {
        Object.keys(sections).forEach((key) => {
            if (sections[key]) {
                sections[key].classList.toggle('hidden', key !== target);
            }
        });
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function setSubmitDisabled(disabled) {
        if (!submitBtn) {
            return;
        }
        submitBtn.disabled = disabled;
        submitBtn.classList.toggle('opacity-60', disabled);
        submitBtn.classList.toggle('cursor-not-allowed', disabled);
    }

    function clearUploadAlert() {
        if (!uploadAlert) {
            return;
        }
        uploadAlert.classList.add('hidden');
        uploadAlert.textContent = '';
    }

    function showUploadAlert(message) {
        if (!uploadAlert) {
            return;
        }
        uploadAlert.textContent = message;
        uploadAlert.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function updateSelectedFileName(label) {
        if (selectedFileName) {
            selectedFileName.textContent = label || 'No file selected';
        }
    }

    function updateProgress(percent, text) {
        if (progressFill) {
            const width = Math.max(0, Math.min(percent, 100));
            progressFill.style.width = `${width}%`;
        }
        if (progressPercent) {
            progressPercent.textContent = `${Math.round(Math.max(0, Math.min(percent, 100)))}%`;
        }
        if (progressText) {
            progressText.textContent = text;
        }
    }

    function appendLogEntry(entry) {
        if (!logContent || !entry) {
            return;
        }
        const line = document.createElement('div');
        line.className = 'mb-1 text-xs text-gray-200 whitespace-pre-wrap';
        const level = (entry.level || 'INFO').toUpperCase();
        let color = '#93c5fd';
        if (level === 'ERROR') {
            color = '#fca5a5';
        } else if (level === 'WARNING') {
            color = '#fde68a';
        } else if (level === 'SUCCESS') {
            color = '#a7f3d0';
        }
        line.style.color = color;
        line.textContent = entry.formatted || entry.message || '';
        logContent.appendChild(line);
        logContent.scrollTop = logContent.scrollHeight;
    }

    function parseLogForProgress(entry) {
        const message = entry.message || entry.formatted || '';
        if (!message) return;

        // Step 2: Downloading
        if (message.includes('Step 2: Downloading video') || message.includes('Step 2: Saving uploaded video')) {
            updateProgress(10, 'Acquiring Video...');
            setStage('Acquiring Video');
        }
        // Step 3: Splitting
        else if (message.includes('Step 3: Splitting video')) {
            updateProgress(20, 'Splitting Video...');
            setStage('Splitting Video');
        }
        // Chunk Analysis
        else if (message.includes('Processing Chunk')) {
            const match = message.match(/Processing Chunk (\d+)\/(\d+)/);
            if (match) {
                const current = parseInt(match[1]);
                const total = parseInt(match[2]);
                const percentage = 20 + ((current / total) * 50); // Map 20-70%
                updateProgress(percentage, `Analyzing Chunk ${current}/${total}...`);
                setStage(`Analyzing Chunk ${current}/${total}`);
            }
        }
        // Step 4: Audio
        else if (message.includes('Step 4: Generating narration audio')) {
            updateProgress(75, 'Generating Narration...');
            setStage('Generating Audio');
        }
        // Step 5: Processing Clips
        else if (message.includes('Step 5: Processing video clips')) {
            updateProgress(85, 'Cutting Video Clips...');
            setStage('Processing Clips');
        }
        // Step 6: Concatenation
        else if (message.includes('Step 6: Creating final concatenated video')) {
            updateProgress(95, 'Rendering Final Video...');
            setStage('Finalizing');
        }
        // Completion
        else if (message.includes('VIDEO PROCESSING COMPLETED SUCCESSFULLY')) {
            updateProgress(100, 'Processing Complete!');
            setStage('Complete');
        }
    }

    function startLogStream(sessionId) {
        stopLogStream();
        if (!sessionId) {
            return;
        }
        const source = new EventSource(`/api/logs/stream?session_id=${encodeURIComponent(sessionId)}`);
        source.addEventListener('message', (event) => {
            try {
                const payload = JSON.parse(event.data);
                appendLogEntry(payload);
                parseLogForProgress(payload);
            } catch (error) {
                console.error('Failed to parse log payload', error);
            }
        });
        source.addEventListener('error', () => {
            appendLogEntry({
                formatted: '[Log Stream] Connection interrupted. Attempting to reconnect…',
                level: 'WARNING',
            });
        });
        state.logEventSource = source;
    }

    function stopLogStream() {
        if (state.logEventSource) {
            state.logEventSource.close();
            state.logEventSource = null;
        }
    }

    function generateSessionId() {
        const now = new Date();
        const pad = (value) => value.toString().padStart(2, '0');
        const datePart = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
        const timePart = `${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
        const randomPart = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
        return `${datePart}_${timePart}${randomPart}`;
    }

    function setStage(text) {
        if (processingStage) {
            processingStage.textContent = text;
        }
    }

    function resetProcessingView() {
        stopLogStream();
        updateProgress(0, 'Waiting to start…');
        setStage('Initializing...');
        if (processingInputName) {
            processingInputName.textContent = '—';
        }
        if (processingMovieTitle) {
            processingMovieTitle.textContent = '—';
        }
        if (processingStartTime) {
            processingStartTime.textContent = '—';
        }
        if (logContent) {
            logContent.innerHTML = '';
        }
        if (processingError) {
            processingError.classList.add('hidden');
            processingError.textContent = '';
        }
        if (processingBackBtn) {
            processingBackBtn.classList.add('hidden');
        }
        if (processingSubtitle) {
            processingSubtitle.textContent = 'We’re preparing your video. Hang tight—logs update in real time.';
        }
    }

    function resetSceneDetails(options = {}) {
        const { keepCounts = false } = options;
        if (sceneList) {
            sceneList.innerHTML = '<p class="text-sm text-gray-500 dark:text-gray-400">Scenes will appear once processing completes.</p>';
        }
        if (sceneMeta) {
            sceneMeta.textContent = 'No scene selected';
        }
        if (sceneTitle) {
            sceneTitle.textContent = 'Select a scene to begin';
        }
        if (sceneNarration) {
            sceneNarration.value = '';
            sceneNarration.placeholder = 'Narration for the selected scene will appear here.';
        }
        if (currentClipDownload) {
            currentClipDownload.classList.add('hidden');
        }
        if (noClipMessage) {
            noClipMessage.classList.add('hidden');
        }
        if (clipDownloads) {
            clipDownloads.innerHTML = '';
        }
        if (!keepCounts) {
            if (resultScenesCount) {
                resultScenesCount.textContent = '0';
            }
            if (resultClipsCount) {
                resultClipsCount.textContent = '0';
            }
        }
    }

    function resetScriptDetails() {
        if (fullRecapScript) {
            fullRecapScript.value = '';
        }
        if (alignmentNotes) {
            alignmentNotes.textContent = '';
            alignmentNotes.classList.add('hidden');
        }
        if (downloadScriptBtn) {
            downloadScriptBtn.classList.add('hidden');
            downloadScriptBtn.href = '#';
        }
        if (resultMovieTitle) {
            resultMovieTitle.textContent = '—';
        }
    }

    async function resetInterface() {
        if (state.sessionId) {
            try {
                await fetch('/api/cleanup', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ session_id: state.sessionId }),
                });
                console.log('Session cleaned up:', state.sessionId);
            } catch (error) {
                console.error('Failed to cleanup session:', error);
            }
        }

        if (uploadForm) {
            uploadForm.reset();
        }
        if (videoInput) {
            videoInput.value = '';
        }
        if (movieTitleInput) {
            movieTitleInput.value = '';
        }
        updateSelectedFileName('No file selected');
        clearUploadAlert();
        resetProcessingView();
        resetSceneDetails();
        resetScriptDetails();
        if (downloadScenesBtn) {
            downloadScenesBtn.classList.add('hidden');
            downloadScenesBtn.href = '#';
        }
        if (downloadFinalBtn) {
            downloadFinalBtn.classList.add('hidden');
            downloadFinalBtn.href = '#';
        }
        setSubmitDisabled(false);
        if (submitBtn) {
            submitBtn.innerHTML = defaultSubmitMarkup;
        }
        state.result = null;
        state.currentSceneIndex = null;
        state.sessionId = null;
        stopLogStream();
        showSection('upload');
    }

    function buildDownloadUrl(filePath) {
        if (!state.result || !state.result.session_id || !filePath) {
            return '#';
        }
        const parts = filePath.split(/[/\\]/);
        const filename = parts[parts.length - 1];
        return `/api/download/${encodeURIComponent(state.result.session_id)}/${encodeURIComponent(filename)}`;
    }

    function selectScene(index) {
        if (!state.result || !state.result.scenes || !state.result.scenes[index]) {
            return;
        }
        state.currentSceneIndex = index;
        const scene = state.result.scenes[index];

        if (sceneList) {
            const buttons = sceneList.querySelectorAll('button[data-scene-index]');
            buttons.forEach((button) => {
                const isActive = Number(button.dataset.sceneIndex) === index;
                button.classList.toggle('bg-primary/10', isActive);
                button.classList.toggle('border-primary', isActive);
                button.classList.toggle('text-primary', isActive);
                button.classList.toggle('border-transparent', !isActive);
            });
        }

        if (sceneMeta) {
            const durationText = scene.duration_seconds ? ` (${scene.duration_seconds}s)` : '';
            sceneMeta.textContent = `Scene ${scene.scene_number} • ${scene.start_time} → ${scene.end_time}${durationText}`;
        }
        if (sceneTitle) {
            const title = scene.title || scene.summary || `Scene ${scene.scene_number}`;
            sceneTitle.textContent = title;
        }
        if (sceneNarration) {
            const narration = scene.narration && scene.narration.trim()
                ? scene.narration.trim()
                : 'Narration not available for this scene.';
            sceneNarration.value = narration;
        }

        if (state.result && state.result.clips && currentClipDownload && noClipMessage) {
            const clip = state.result.clips.find((item) => item.scene_number === scene.scene_number);
            if (clip && clip.clip_path) {
                currentClipDownload.href = buildDownloadUrl(clip.clip_path);
                currentClipDownload.classList.remove('hidden');
                noClipMessage.classList.add('hidden');
            } else {
                currentClipDownload.classList.add('hidden');
                noClipMessage.classList.remove('hidden');
            }
        }
    }

    function renderSceneList() {
        if (!sceneList) {
            return;
        }
        sceneList.innerHTML = '';

        if (!state.result || !Array.isArray(state.result.scenes) || state.result.scenes.length === 0) {
            resetSceneDetails({ keepCounts: true });
            return;
        }

        state.result.scenes.forEach((scene, index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.dataset.sceneIndex = String(index);
            button.className = 'flex items-center gap-3 rounded-xl border border-transparent px-4 py-3 text-left transition hover:bg-gray-100 dark:hover:bg-white/5';
            const narrationPreview = scene.narration ? scene.narration.trim().slice(0, 80) : '';
            const truncatedNarration = narrationPreview && scene.narration.length > 80 ? `${narrationPreview}…` : narrationPreview;
            button.innerHTML = `
                <div class="flex size-10 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">${scene.scene_number}</div>
                <div class="flex flex-col">
                    <span class="text-sm font-semibold text-text-light dark:text-white">Scene ${scene.scene_number}</span>
                    <span class="text-xs text-gray-500 dark:text-gray-400">${scene.start_time} → ${scene.end_time}</span>
                    ${truncatedNarration ? `<span class="text-xs text-gray-400 dark:text-gray-500 mt-1">${truncatedNarration}</span>` : ''}
                </div>
            `;
            button.addEventListener('click', () => selectScene(index));
            sceneList.appendChild(button);
        });

        selectScene(0);
    }

    function renderClipDownloads() {
        if (!clipDownloads) {
            return;
        }
        clipDownloads.innerHTML = '';

        if (!state.result || !Array.isArray(state.result.clips) || state.result.clips.length === 0) {
            const empty = document.createElement('p');
            empty.className = 'text-sm text-gray-500 dark:text-gray-400';
            empty.textContent = 'No individual clips were generated.';
            clipDownloads.appendChild(empty);
            return;
        }

        state.result.clips.forEach((clip) => {
            const link = document.createElement('a');
            link.href = buildDownloadUrl(clip.clip_path);
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.className = 'flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm font-semibold text-text-light transition hover:border-primary hover:text-primary dark:border-gray-700 dark:bg-[#1a2227] dark:text-text-dark dark:hover:border-primary dark:hover:text-primary';
            link.innerHTML = `
                <span>Clip ${clip.scene_number} • ${clip.start_time} → ${clip.end_time}</span>
                <span class="material-symbols-outlined text-base">download</span>
            `;
            clipDownloads.appendChild(link);
        });
    }

    function displayResults(result) {
        stopLogStream();
        state.result = result;
        state.currentSceneIndex = null;

        setSubmitDisabled(false);
        if (submitBtn) {
            submitBtn.innerHTML = defaultSubmitMarkup;
        }

        if (resultScenesCount) {
            const count = result.scenes_count ?? result.scenes?.length ?? 0;
            resultScenesCount.textContent = String(count);
        }
        if (resultClipsCount) {
            resultClipsCount.textContent = String(result.clips?.length ?? 0);
        }
        if (resultMovieTitle) {
            resultMovieTitle.textContent = result.movie_title || '—';
        }
        if (fullRecapScript) {
            fullRecapScript.value = result.full_script || '';
        }
        if (downloadScriptBtn) {
            if (result.script_file) {
                downloadScriptBtn.href = buildDownloadUrl(result.script_file);
                downloadScriptBtn.classList.remove('hidden');
            } else {
                downloadScriptBtn.classList.add('hidden');
                downloadScriptBtn.href = '#';
            }
        }
        if (alignmentNotes) {
            const skippedCount = Number(result.skipped_scenes || 0);
            const skippedList = Array.isArray(result.skipped_scene_numbers) ? result.skipped_scene_numbers.filter(Boolean) : [];
            const skippedDetails = Array.isArray(result.skipped_scene_details) ? result.skipped_scene_details : [];
            if (result.alignment_notes) {
                alignmentNotes.textContent = result.alignment_notes;
                alignmentNotes.classList.remove('hidden');
            } else if (skippedCount > 0) {
                let detailLabel = '';
                if (skippedDetails.length) {
                    const formatted = skippedDetails.map((detail) => {
                        const numberLabel = detail.scene_number != null ? `Scene ${detail.scene_number}` : 'Scene';
                        const reasonLabel = detail.reason ? ` – ${detail.reason}` : '';
                        return `${numberLabel}${reasonLabel}`;
                    });
                    detailLabel = ` (${formatted.join('; ')})`;
                } else if (skippedList.length) {
                    detailLabel = ` (${skippedList.join(', ')})`;
                }
                alignmentNotes.textContent = `Skipped ${skippedCount} segment(s) flagged for manual review${detailLabel}.`;
                alignmentNotes.classList.remove('hidden');
            } else {
                alignmentNotes.textContent = '';
                alignmentNotes.classList.add('hidden');
            }
        }

        if (downloadScenesBtn) {
            const scenesFileName = result.scenes_file || 'scenes.json';
            downloadScenesBtn.href = buildDownloadUrl(scenesFileName);
            downloadScenesBtn.classList.remove('hidden');
        }

        if (downloadFinalBtn) {
            if (result.final_video) {
                downloadFinalBtn.href = buildDownloadUrl(result.final_video);
                downloadFinalBtn.classList.remove('hidden');
            } else {
                downloadFinalBtn.classList.add('hidden');
            }
        }

        renderClipDownloads();
        renderSceneList();
        setStage('Complete');
        updateProgress(100, 'Processing complete!');
        showSection('results');
    }

    function startProcessingUI({ videoSource, movieTitle, sessionId }) {
        state.sessionId = sessionId || null;
        setSubmitDisabled(true);
        if (submitBtn) {
            submitBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-base">progress_activity</span>Processing...';
        }
        if (processingMovieTitle) {
            processingMovieTitle.textContent = movieTitle || '—';
        }
        if (processingInputName) {
            processingInputName.textContent = videoSource || '—';
        }
        if (processingStartTime) {
            processingStartTime.textContent = new Date().toLocaleString();
        }
        if (processingSubtitle) {
            processingSubtitle.textContent = 'We’re preparing your video. Hang tight—logs update in real time.';
        }
        if (processingError) {
            processingError.classList.add('hidden');
            processingError.textContent = '';
        }
        if (processingBackBtn) {
            processingBackBtn.classList.add('hidden');
        }

        if (logContent) {
            logContent.innerHTML = '';
        }

        updateProgress(0, 'Initializing…');
        setStage('Initializing…');
        startLogStream(sessionId);
        showSection('processing');
    }

    function handleProcessingError(error) {
        stopLogStream();
        console.error('Processing error:', error);
        setSubmitDisabled(false);
        if (submitBtn) {
            submitBtn.innerHTML = defaultSubmitMarkup;
        }
        updateProgress(0, 'Error encountered');
        setStage('Error encountered');
        appendLogEntry({
            formatted: `[Client] ${error.message || 'Processing failed.'}`,
            level: 'ERROR',
        });

        if (processingSubtitle) {
            processingSubtitle.textContent = 'Something went wrong. Review the log and try again.';
        }
        if (processingError) {
            processingError.textContent = error.message || 'Processing failed. Please try again.';
            processingError.classList.remove('hidden');
        }
        if (processingBackBtn) {
            processingBackBtn.classList.remove('hidden');
        }
    }

    if (browseButton && videoInput) {
        browseButton.addEventListener('click', () => videoInput.click());
    }

    if (videoInput) {
        videoInput.addEventListener('change', () => {
            if (videoInput.files && videoInput.files.length > 0) {
                updateSelectedFileName(videoInput.files[0].name);
                if (driveUrlInput) {
                    driveUrlInput.value = '';
                }
            } else {
                updateSelectedFileName('No file selected');
            }
        });
    }

    if (driveUrlInput) {
        driveUrlInput.addEventListener('input', () => {
            if (driveUrlInput.value.trim() && videoInput) {
                videoInput.value = '';
                updateSelectedFileName('No file selected');
            }
        });
    }

    if (processingBackBtn) {
        processingBackBtn.addEventListener('click', () => {
            const message = processingError ? processingError.textContent : '';
            resetProcessingView();
            showSection('upload');
            if (message) {
                showUploadAlert(message);
            }
        });
    }

    if (processAnotherBtn) {
        processAnotherBtn.addEventListener('click', () => {
            resetInterface();
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            clearUploadAlert();

            const videoFile = videoInput && videoInput.files ? videoInput.files[0] : null;
            const driveUrl = driveUrlInput ? driveUrlInput.value.trim() : '';
            const instructions = instructionsInput ? instructionsInput.value.trim() : '';
            const movieTitle = movieTitleInput ? movieTitleInput.value.trim() : '';

            // Movie title is no longer required
            // if (!movieTitle) {
            //    showUploadAlert('Please provide the movie or series title.');
            //    return;
            // }

            if (!videoFile && !driveUrl) {
                showUploadAlert('Please upload a video or provide a Google Drive link.');
                return;
            }

            if (videoFile && driveUrl) {
                showUploadAlert('Choose only one input method: either upload a file or provide a Google Drive link.');
                return;
            }

            const sessionId = generateSessionId();
            const formData = new FormData();
            if (videoFile) {
                formData.append('video', videoFile);
            }
            if (driveUrl) {
                formData.append('drive_url', driveUrl);
            }
            if (instructions) {
                formData.append('instructions', instructions);
            }
            // Script text is now the main input
            const scriptText = instructionsInput ? instructionsInput.value.trim() : '';
            if (!scriptText) {
                showUploadAlert('Please paste the script text.');
                return;
            }
            formData.append('script_text', scriptText);
            formData.append('movie_title', movieTitle);
            formData.append('session_id', sessionId);

            resetScriptDetails();

            startProcessingUI({
                videoSource: videoFile ? videoFile.name : 'Google Drive link',
                movieTitle,
                sessionId,
            });

            setStage('Generating recap script');
            updateProgress(5, 'Generating recap script with Gemini…');

            try {
                updateProgress(20, 'Preparing video for alignment…');
                setStage('Aligning recap to video');

                const response = await fetch('/api/process', {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    let message = 'Processing failed. Please check your input and try again.';
                    try {
                        const errorData = await response.json();
                        if (errorData && errorData.error) {
                            message = errorData.error;
                        }
                    } catch (parseError) {
                        console.warn('Failed to parse error response', parseError);
                    }
                    throw new Error(message);
                }

                const result = await response.json();

                updateProgress(65, 'Recap aligned to video timeline…');

                updateProgress(78, 'Generating narration audio…');
                setStage('Generating narration audio');

                updateProgress(90, 'Processing video clips with FFmpeg…');
                setStage('Processing video clips');

                updateProgress(100, 'Processing complete!');
                setStage('Finalizing results');

                setTimeout(() => displayResults(result), 400);
            } catch (error) {
                handleProcessingError(error instanceof Error ? error : new Error('Unexpected error occurred.'));
            }
        });
    }

    resetProcessingView();
    resetSceneDetails();
    resetScriptDetails();
    showSection('upload');
});
