document.addEventListener('DOMContentLoaded', () => {
    // Tab Switching
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    let sourceType = 'upload'; // 'upload' or 'youtube'
    let selectedFile = null;

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const target = btn.getAttribute('data-target');
            document.getElementById(target).classList.add('active');
            sourceType = target === 'upload-tab' ? 'upload' : 'youtube';
        });
    });

    // Drag and Drop Logic
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        if (file.type === 'video/mp4' || file.type === 'video/quicktime') {
            selectedFile = file;
            const dropText = dropZone.querySelector('.drop-text');
            dropText.innerHTML = `<i class="fa-solid fa-file-video text-accent"></i> ${file.name}`;
            const dropSubtext = dropZone.querySelector('.drop-subtext');
            dropSubtext.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB - Ready to upload`;
        } else {
            alert('Please select a valid MP4 or MOV video file.');
        }
    }

    // Dynamic Timestamps
    const addTimeBtn = document.getElementById('add-timestamp-btn');
    const timestampsContainer = document.getElementById('timestamps-container');

    // Add remove listener to initial row
    function attachRemoveListener(btn, row) {
        btn.addEventListener('click', () => {
            row.remove();
            updateRemoveButtons();
        });
    }

    const initialRow = timestampsContainer.querySelector('.timestamp-row');
    if (initialRow) attachRemoveListener(initialRow.querySelector('.remove-btn'), initialRow);

    addTimeBtn.addEventListener('click', () => {
        const row = document.createElement('div');
        row.className = 'timestamp-row';
        row.innerHTML = `
            <div class="input-group">
                <label>Start</label>
                <input type="text" class="time-start" placeholder="e.g. 1:20 or 80" required>
            </div>
            <div class="input-group">
                <label>End</label>
                <input type="text" class="time-end" placeholder="e.g. 1:45 or 105" required>
            </div>
            <button class="icon-btn remove-btn"><i class="fa-solid fa-trash"></i></button>
        `;
        timestampsContainer.appendChild(row);

        // Add remove listener
        attachRemoveListener(row.querySelector('.remove-btn'), row);
        updateRemoveButtons();
    });

    function updateRemoveButtons() {
        const rows = timestampsContainer.querySelectorAll('.timestamp-row');
        const firstRemoveBtn = rows[0].querySelector('.remove-btn');
        if (rows.length === 1) {
            firstRemoveBtn.classList.add('disabled');
        } else {
            firstRemoveBtn.classList.remove('disabled');
        }
    }

    // Processing Logic
    const generateBtn = document.getElementById('generate-btn');
    const statusPanel = document.getElementById('status-panel');
    const statusTitle = document.getElementById('status-title');
    const statusMessage = document.getElementById('status-message');
    const resultActions = document.getElementById('result-actions');
    const statusContent = document.querySelector('.status-content');
    const downloadBtn = document.getElementById('download-btn');
    const resetBtn = document.getElementById('reset-btn');

    generateBtn.addEventListener('click', async () => {
        // Helper to convert "MM:SS" or "SS" to pure seconds
        function parseTime(timeStr) {
            if (!timeStr) return null;
            if (timeStr.includes(':')) {
                const parts = timeStr.split(':');
                if (parts.length === 2) {
                    return parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
                }
            }
            return parseFloat(timeStr);
        }

        // Collect Timestamps
        const ranges = [];
        let validRanges = true;
        document.querySelectorAll('.timestamp-row').forEach(row => {
            const startRaw = row.querySelector('.time-start').value;
            const endRaw = row.querySelector('.time-end').value;

            if (startRaw === '' || endRaw === '') {
                validRanges = false;
            } else {
                ranges.push({
                    start: parseTime(startRaw),
                    end: parseTime(endRaw)
                });
            }
        });

        if (!validRanges) {
            alert("Please fill out all start and end timestamps.");
            return;
        }

        // Collect Settings
        const voiceLang = document.getElementById('voice-lang').value;
        const subLang = document.getElementById('sub-lang').value;
        const gender = document.getElementById('gender').value;

        // Show panel
        statusPanel.classList.remove('hidden');
        statusContent.style.display = 'block';
        resultActions.classList.add('hidden');
        statusTitle.textContent = 'Preparing Source...';
        statusMessage.textContent = 'Uploading / Downloading video source...';

        let filepath = null;

        try {
            // STEP 1: Upload / YT Download
            const formData = new FormData();
            if (sourceType === 'upload') {
                if (!selectedFile) throw new Error("Please select a file to upload.");
                formData.append('file', selectedFile);
            } else {
                const ytUrl = document.getElementById('youtube-url').value;
                if (!ytUrl) throw new Error("Please enter a YouTube URL.");
                formData.append('youtube_url', ytUrl);
            }

            const uploadResp = await fetch('/upload', { method: 'POST', body: formData });
            const uploadData = await uploadResp.json();

            if (!uploadData.success) {
                throw new Error(uploadData.error || "Failed to handle source file");
            }
            filepath = uploadData.filepath;

            // STEP 2: Queue Processing
            statusTitle.textContent = 'Queued in AI Engine';
            statusMessage.textContent = 'Initializing the pipeline...';

            const payload = { filepath, ranges, voice_lang: voiceLang, sub_lang: subLang, gender };
            const procResp = await fetch('/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const procData = await procResp.json();

            if (!procData.success) {
                throw new Error(procData.error || "Failed to queue processing tasks");
            }

            const taskId = procData.task_id;

            // STEP 3: Poll status
            const pollInterval = setInterval(async () => {
                const statResp = await fetch(`/status/${taskId}`);
                const statData = await statResp.json();

                if (statData.status === 'Processing') {
                    statusTitle.textContent = 'AI Converting...';
                    statusMessage.textContent = statData.message || 'Processing frames...';
                } else if (statData.status === 'Done') {
                    clearInterval(pollInterval);
                    showSuccess(taskId);
                } else if (statData.status === 'Error') {
                    clearInterval(pollInterval);
                    showError(statData.message || "Unknown processing error");
                }
            }, 3000);

        } catch (error) {
            showError(error.message);
        }
    });

    function showSuccess(taskId) {
        statusContent.style.display = 'none';
        resultActions.classList.remove('hidden');
        const dlUrl = `/download/${taskId}`;
        downloadBtn.href = dlUrl;

        // Setup video preview
        const videoPlayer = document.getElementById('final-video-player');
        videoPlayer.src = dlUrl;
        videoPlayer.load();
    }

    function showError(msg) {
        statusTitle.textContent = 'Error';
        statusTitle.style.background = 'linear-gradient(135deg, #ef4444, #b91c1c)';
        statusTitle.style.webkitBackgroundClip = 'text';
        statusMessage.textContent = msg;

        setTimeout(() => {
            statusPanel.classList.add('hidden');
            // Reset title style
            statusTitle.style.background = 'linear-gradient(135deg, var(--text-main), var(--accent))';
            statusTitle.style.webkitBackgroundClip = 'text';
        }, 5000);
    }

    resetBtn.addEventListener('click', () => {
        statusPanel.classList.add('hidden');
        // Optionally clear inputs
        selectedFile = null;
        document.getElementById('file-input').value = '';
        document.querySelector('.drop-text').textContent = 'Drag & Drop your video here';
        document.querySelector('.drop-subtext').textContent = 'or click to browse files (MP4, MOV)';
        document.getElementById('youtube-url').value = '';
    });
});
