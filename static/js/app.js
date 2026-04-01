// ============================================
// VIDEO DOWNLOADER - Frontend App
// ============================================

(function () {
    'use strict';

    // --- DOM Elements ---
    const elements = {
        // URL Section
        urlInput: document.getElementById('urlInput'),
        btnAnalyze: document.getElementById('btnAnalyze'),
        btnPaste: document.getElementById('btnPaste'),
        urlSection: document.getElementById('urlSection'),

        // Status
        statusContainer: document.getElementById('statusContainer'),
        statusCard: document.getElementById('statusCard'),
        statusIcon: document.getElementById('statusIcon'),
        statusMessage: document.getElementById('statusMessage'),

        // Video Info
        videoSection: document.getElementById('videoSection'),
        videoThumbnail: document.getElementById('videoThumbnail'),
        videoDuration: document.getElementById('videoDuration'),
        videoTitle: document.getElementById('videoTitle'),
        videoUploader: document.getElementById('videoUploader'),
        videoViews: document.getElementById('videoViews'),
        videoSource: document.getElementById('videoSource'),
        qualityGrid: document.getElementById('qualityGrid'),
        // Download Options
        btnDownload: document.getElementById('btnDownload'),
        btnAdvanced: document.getElementById('btnAdvanced'),
        advancedOptions: document.getElementById('advancedOptions'),
        formatGroupContainer: document.getElementById('formatGroupContainer'),
        audioQualityGroup: document.getElementById('audioQualityGroup'),
        subtitleLangGroup: document.getElementById('subtitleLangGroup'),
        thumbnailOption: document.getElementById('thumbnailOption'),
        subtitlesOption: document.getElementById('subtitlesOption'),

        // Playlist Selection
        playlistGroup: document.getElementById('playlistGroup'),
        playlistCount: document.getElementById('playlistCount'),
        playlistList: document.getElementById('playlistList'),
        btnSelectAllPlaylist: document.getElementById('btnSelectAllPlaylist'),
        btnSelectNonePlaylist: document.getElementById('btnSelectNonePlaylist'),

        // Progress
        progressSection: document.getElementById('progressSection'),
        progressTitle: document.getElementById('progressTitle'),
        progressFill: document.getElementById('progressFill'),
        progressGlow: document.getElementById('progressGlow'),
        progressPercentage: document.getElementById('progressPercentage'),
        detailSpeed: document.getElementById('detailSpeed'),
        detailSize: document.getElementById('detailSize'),
        detailETA: document.getElementById('detailETA'),
        progressStatus: document.getElementById('progressStatus'),
        btnCancel: document.getElementById('btnCancel'),

        // Complete
        completeSection: document.getElementById('completeSection'),
        completeInfo: document.getElementById('completeInfo'),
        btnSave: document.getElementById('btnSave'),
        btnNewDownload: document.getElementById('btnNewDownload'),

        // Recent Downloads
        recentSection: document.getElementById('recentSection'),
        recentList: document.getElementById('recentList'),

        // Saved Downloads
        savedSection: document.getElementById('savedSection'),
        savedList: document.getElementById('savedList'),

        // Users Modal (admin only)
        usersModal: document.getElementById('usersModal'),
        btnUsers: document.getElementById('btnUsers'),
        btnCloseModal: document.getElementById('btnCloseModal'),
        createUserForm: document.getElementById('createUserForm'),
        usersList: document.getElementById('usersList'),
        formMessage: document.getElementById('formMessage'),

        // Player
        playerOverlay: document.getElementById('playerOverlay'),
        playerTitle: document.getElementById('playerTitle'),
        playerClose: document.getElementById('playerClose'),
        playerVideo: document.getElementById('playerVideo'),
        playerAudio: document.getElementById('playerAudio'),
        playerQuickTags: document.getElementById('playerQuickTags'),
        playerTechPanel: document.getElementById('playerTechPanel'),
        playerTechToggle: document.getElementById('playerTechToggle'),
        playerTechBody: document.getElementById('playerTechBody'),
        playerDownloadBtn: document.getElementById('playerDownloadBtn'),
        playerPipBtn: document.getElementById('playerPipBtn'),
        playerBgPlayBtn: document.getElementById('playerBgPlayBtn'),
        playerBgStatus: document.getElementById('playerBgStatus'),
        playerBgStatusText: document.getElementById('playerBgStatusText'),
        playerResumeBadge: document.getElementById('playerResumeBadge'),
        playerAudioVisualizer: document.getElementById('playerAudioVisualizer'),
        playerLiveStats: document.getElementById('playerLiveStats'),
        playerShareBtn: document.getElementById('playerShareBtn'),
        playerOriginalBtn: document.getElementById('playerOriginalBtn'),
        playerVideoControls: document.getElementById('playerVideoControls'),
        fpVideoPlayBtn: document.getElementById('fpVideoPlayBtn'),
        fpVideoRwBtn: document.getElementById('fpVideoRwBtn'),
        fpVideoFfBtn: document.getElementById('fpVideoFfBtn'),
        fpVideoTime: document.getElementById('fpVideoTime'),
        fpVideoDuration: document.getElementById('fpVideoDuration'),
        fpVideoSeekInput: document.getElementById('fpVideoSeekInput'),
        fpVideoSeekProgress: document.getElementById('fpVideoSeekProgress'),
        fpVideoSeekBuffered: document.getElementById('fpVideoSeekBuffered'),
        fpVideoSeekThumb: document.getElementById('fpVideoSeekThumb'),
        fpVideoSeekPreview: document.getElementById('fpVideoSeekPreview'),
        fpVideoSeekWrap: document.getElementById('fpVideoSeekWrap'),
        fpVideoVolBtn: document.getElementById('fpVideoVolBtn'),
        fpVideoVolInput: document.getElementById('fpVideoVolInput'),
        fpVideoFsBtn: document.getElementById('fpVideoFsBtn'),
        playerAudioControls: document.getElementById('playerAudioControls'),
        fpAudioPlayBtn: document.getElementById('fpAudioPlayBtn'),
        fpAudioTime: document.getElementById('fpAudioTime'),
        fpAudioDuration: document.getElementById('fpAudioDuration'),
        fpAudioSeekInput: document.getElementById('fpAudioSeekInput'),
        fpAudioSeekProgress: document.getElementById('fpAudioSeekProgress'),
        fpAudioSeekBuffered: document.getElementById('fpAudioSeekBuffered'),
        fpAudioVolBtn: document.getElementById('fpAudioVolBtn'),
        fpAudioVolInput: document.getElementById('fpAudioVolInput'),

        // Quota
        navQuota: document.getElementById('navQuota'),
        quotaText: document.getElementById('quotaText'),

        // Queue
        queueSection: document.getElementById('queueSection'),
        queueList: document.getElementById('queueList'),
        queueCountBadge: document.getElementById('queueCountBadge'),
        btnClearQueue: document.getElementById('btnClearQueue'),
        navQueueIndicator: document.getElementById('navQueueIndicator'),
        navQueueCount: document.getElementById('navQueueCount'),

        // Trim Modal
        trimModal: document.getElementById('trimModal'),
        btnCloseTrimModal: document.getElementById('btnCloseTrimModal'),
        trimVideoPlayer: document.getElementById('trimVideoPlayer'),
        trimTimeline: document.getElementById('trimTimeline'),
        trimProgress: document.getElementById('trimProgress'),
        trimHandleStart: document.getElementById('trimHandleStart'),
        trimHandleEnd: document.getElementById('trimHandleEnd'),
        trimSelection: document.getElementById('trimSelection'),
        trimTooltipStart: document.getElementById('trimTooltipStart'),
        trimTooltipEnd: document.getElementById('trimTooltipEnd'),
        trimInputStart: document.getElementById('trimInputStart'),
        trimInputEnd: document.getElementById('trimInputEnd'),
        btnCancelTrim: document.getElementById('btnCancelTrim'),
        btnConfirmTrim: document.getElementById('btnConfirmTrim'),
        trimStatusText: document.getElementById('trimStatusText'),

        // Toast
        toastContainer: document.getElementById('toastContainer'),
    };

    // --- State ---
    let state = {
        currentDownloadId: null,
        activeDownloadId: null,
        selectedQuality: null,
        videoInfo: null,
        isDownloading: false,
        recentDownloads: [],
        savedDownloads: [],
        collections: [],
        activeCollection: null,
        editingCollectionId: null,
        recentTimer: null,
        countdownTimer: null,
        trimState: {
            activeId: null,
            duration: 0,
            start: 0,
            end: 0,
            isDragging: false,
            activeHandle: null,
        },
        disconnectTimer: null,
        queue: [],
        maxQueueSize: 5,
    };

    // --- Socket.IO ---
    const socket = io({
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 30000,
    });

    socket.on('connect', () => {
        console.log('WebSocket connected');
        if (state.disconnectTimer) {
            clearTimeout(state.disconnectTimer);
            state.disconnectTimer = null;
        }
    });

    socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        // Delay the lost connection toast by 3 seconds
        if (!state.disconnectTimer) {
            state.disconnectTimer = setTimeout(() => {
                showToast('Conexión perdida. Reconectando...', 'error');
                state.disconnectTimer = null;
            }, 3000);
        }
    });

    socket.on('reconnect', () => {
        if (state.disconnectTimer) {
            clearTimeout(state.disconnectTimer);
            state.disconnectTimer = null;
        } else {
            showToast('Reconectado exitosamente', 'success');
        }
    });

    // --- Auto-reconnect when app resumes from background ---
    // On mobile PWAs, after long idle the socket dies silently.
    // Force reconnection when the app comes back to foreground.
    function ensureSocketConnected() {
        if (!socket.connected) {
            console.log('App resumed - socket dead, forcing reconnect...');
            socket.connect();
        }
    }

    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            ensureSocketConnected();
        }
    });

    // pageshow fires when navigating back to a bfcache'd page (mobile browsers)
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) {
            ensureSocketConnected();
        }
    });

    // Also handle focus (some mobile browsers don't fire visibilitychange reliably)
    window.addEventListener('focus', ensureSocketConnected);

    // --- Socket Event Handlers ---
    socket.on('status', (data) => {
        const isSuccess = data.message.includes('✅');
        const isError = data.message.includes('❌') || data.message.includes('🚫');

        if (state.isDownloading || isSuccess || isError) {
            const type = isSuccess ? 'success' : (isError ? 'error' : 'info');
            showToast(data.message, type);
            if (isSuccess || isError) hideStatus();
        } else {
            showStatus(data.message);
        }
    });

    socket.on('error', (data) => {
        hideStatus();
        showToast(data.message, 'error');
        enableAnalyze();
    });

    socket.on('video_info', (data) => {
        hideStatus();
        displayVideoInfo(data);
    });

    socket.on('download_progress', (data) => {
        handleDownloadProgress(data);
    });

    socket.on('active_downloads_status', (data) => {
        if (data.downloads && data.downloads.length > 0) {
            console.log('Restoring active downloads:', data.downloads);
            // Show the first active download in the main progress section
            const activeDl = data.downloads[0];
            state.isDownloading = true;
            state.activeDownloadId = activeDl.download_id;

            // Keep the search section VISIBLE, but clear other UI states
            elements.videoSection.style.display = 'none';
            elements.completeSection.style.display = 'none';
            elements.progressSection.style.display = 'block';

            handleDownloadProgress(activeDl);
        }
    });

    socket.on('recent_downloads_update', () => {
        console.log('Recent downloads update received');
        loadRecentDownloads();
    });

    socket.on('saved_downloads_update', () => {
        console.log('Saved downloads update received');
        loadCollections();
        loadSavedDownloads();
        loadQuota();
    });

    socket.on('queue_updated', (data) => {
        state.queue = data.queue || [];
        state.maxQueueSize = data.max_queue_size;
        renderQueue();
    });

    // --- URL Analysis ---
    elements.btnAnalyze.addEventListener('click', analyzeUrl);

    elements.urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            analyzeUrl();
        }
    });

    elements.btnPaste.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            elements.urlInput.value = text;
            elements.urlInput.focus();
            showToast('Texto pegado desde el portapapeles', 'info');
        } catch (err) {
            showToast('No se pudo acceder al portapapeles', 'error');
        }
    });

    function analyzeUrl() {
        const url = elements.urlInput.value.trim();
        if (!url) {
            showToast('Por favor, introduce una URL', 'error');
            elements.urlInput.focus();
            return;
        }

        // If socket is dead, reconnect first then emit
        if (!socket.connected) {
            showToast('Reconectando...', 'info');
            socket.connect();
            socket.once('connect', () => {
                disableAnalyze();
                hideDynamicSections();
                showStatus('🔍 Analizando enlace...');
                socket.emit('analyze_url', { url: url });
            });
            return;
        }

        disableAnalyze();
        hideDynamicSections();
        showStatus('🔍 Analizando enlace...');

        socket.emit('analyze_url', { url: url });
    }

    function disableAnalyze() {
        elements.btnAnalyze.disabled = true;
        elements.btnAnalyze.innerHTML = '<div class="spinner small" style="width:18px;height:18px;border-width:2px;"></div> <span>Analizando...</span>';
    }

    function enableAnalyze() {
        elements.btnAnalyze.disabled = false;
        elements.btnAnalyze.innerHTML = '<i class="fas fa-search"></i> <span>Analizar</span>';
    }

    // --- Display Video Info ---
    function displayVideoInfo(info) {
        state.videoInfo = info;
        state.currentDownloadId = info.download_id;
        state.selectedQuality = null;

        enableAnalyze();

        // Set video details
        elements.videoTitle.textContent = info.title;
        elements.videoThumbnail.src = info.thumbnail || '';
        elements.videoThumbnail.onerror = function () {
            this.style.display = 'none';
        };
        elements.videoDuration.textContent = info.duration || '';
        elements.videoDuration.style.display = info.duration ? 'block' : 'none';

        // Meta info
        const uploaderSpan = elements.videoUploader.querySelector('span');
        uploaderSpan.textContent = info.uploader || 'Desconocido';
        elements.videoUploader.style.display = info.uploader ? 'flex' : 'none';

        const viewsSpan = elements.videoViews.querySelector('span');
        if (info.view_count) {
            viewsSpan.textContent = formatNumber(info.view_count) + ' vistas';
            elements.videoViews.style.display = 'flex';
        } else {
            elements.videoViews.style.display = 'none';
        }

        const sourceSpan = elements.videoSource.querySelector('span');
        sourceSpan.textContent = info.extractor || 'Web';
        elements.videoSource.style.display = 'flex';

        // Display playlist if available
        if (info.is_playlist && info.playlist_videos && info.playlist_videos.length > 0) {
            elements.playlistGroup.style.display = 'block';
            renderPlaylist(info.playlist_videos);
        } else {
            elements.playlistGroup.style.display = 'none';
        }

        // Build quality buttons
        buildQualityGrid(info);

        // Reset download button
        elements.btnDownload.disabled = true;
        elements.btnDownload.innerHTML = '<i class="fas fa-download"></i> <span>Selecciona una calidad</span>';

        // Show/hide advanced options based on video capabilities
        elements.thumbnailOption.style.display = info.has_thumbnail ? 'flex' : 'none';
        elements.subtitlesOption.style.display = info.has_subtitles ? 'flex' : 'none';
        elements.subtitleLangGroup.style.display = info.has_subtitles ? 'block' : 'none';
        // Reset format/audio groups to default state
        elements.formatGroupContainer.style.display = 'block';
        elements.audioQualityGroup.style.display = 'none';
        // Build audio quality options based on available bitrate
        buildAudioQualityOptions(info.max_audio_bitrate || 0);
        // Reset advanced options panel
        elements.advancedOptions.style.display = 'none';
        elements.btnAdvanced.classList.remove('open');

        // Show video section
        elements.videoSection.style.display = 'block';
        elements.videoSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function buildQualityGrid(info) {
        elements.qualityGrid.innerHTML = '';

        // Video qualities
        if (info.resolutions && info.resolutions.length > 0) {
            info.resolutions.forEach(res => {
                const btn = document.createElement('button');
                btn.className = 'quality-btn';
                btn.dataset.quality = res.label;

                let icon = '📺';
                if (res.height >= 2160) icon = '🎬';
                else if (res.height >= 1080) icon = '🔥';
                else if (res.height >= 720) icon = '✨';

                btn.innerHTML = `
                    <span class="quality-label"><span class="quality-icon">${icon}</span> ${res.label}</span>
                    ${res.size ? `<span class="quality-size">~${res.size}</span>` : ''}
                `;

                btn.addEventListener('click', () => selectQuality(btn, res.label));
                elements.qualityGrid.appendChild(btn);
            });
        }

        // Audio options
        if (info.has_audio) {
            const audioOriginal = document.createElement('button');
            audioOriginal.className = 'quality-btn audio-btn';
            audioOriginal.dataset.quality = 'audio_original';
            audioOriginal.innerHTML = '<span class="quality-label"><span class="quality-icon">🎵</span> Audio Original</span>';
            audioOriginal.addEventListener('click', () => selectQuality(audioOriginal, 'audio_original'));
            elements.qualityGrid.appendChild(audioOriginal);

            const audioMp3 = document.createElement('button');
            audioMp3.className = 'quality-btn audio-btn';
            audioMp3.dataset.quality = 'audio_mp3';
            audioMp3.innerHTML = '<span class="quality-label"><span class="quality-icon">🎵</span> Audio MP3</span>';
            audioMp3.addEventListener('click', () => selectQuality(audioMp3, 'audio_mp3'));
            elements.qualityGrid.appendChild(audioMp3);
        }

        // Best quality option
        const bestBtn = document.createElement('button');
        bestBtn.className = 'quality-btn';
        bestBtn.dataset.quality = 'best';
        bestBtn.innerHTML = '<span class="quality-label"><span class="quality-icon">⭐</span> Mejor calidad</span><span class="quality-size">Auto</span>';
        bestBtn.addEventListener('click', () => selectQuality(bestBtn, 'best'));
        elements.qualityGrid.appendChild(bestBtn);
    }

    function buildAudioQualityOptions(maxBitrate) {
        const select = document.getElementById('audioQuality');
        if (!select) return;

        const allOptions = [
            { value: '320', label: '320 kbps (Alta)', bitrate: 320 },
            { value: '256', label: '256 kbps', bitrate: 256 },
            { value: '192', label: '192 kbps (Estándar)', bitrate: 192 },
            { value: '128', label: '128 kbps (Baja)', bitrate: 128 },
        ];

        select.innerHTML = '';
        let firstAdded = null;

        allOptions.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.value;

            if (maxBitrate > 0 && opt.bitrate > maxBitrate) {
                // Bitrate exceeds source - show it but mark as unavailable
                option.label = `${opt.label} (fuente: ~${Math.round(maxBitrate)} kbps)`;
                option.textContent = option.label;
                option.disabled = true;
            } else {
                option.textContent = opt.label;
                if (!firstAdded) firstAdded = opt.value;
            }

            select.appendChild(option);
        });

        // Select the highest available option
        if (firstAdded) {
            select.value = firstAdded;
        }
    }

    function selectQuality(btn, quality) {
        document.querySelectorAll('.quality-btn').forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');

        state.selectedQuality = quality;

        const isAudio = quality.startsWith('audio');
        elements.btnDownload.disabled = false;
        elements.btnDownload.innerHTML = `<i class="fas fa-download"></i> <span>Descargar ${isAudio ? 'audio' : quality}</span>`;

        // Show/hide options based on selection
        elements.formatGroupContainer.style.display = isAudio ? 'none' : 'block';
        elements.audioQualityGroup.style.display = quality === 'audio_mp3' ? 'block' : 'none';

        // Subtitles only make sense for video
        const info = state.videoInfo;
        if (isAudio) {
            elements.subtitleLangGroup.style.display = 'none';
            elements.subtitlesOption.style.display = 'none';
        } else {
            elements.subtitleLangGroup.style.display = info && info.has_subtitles ? 'block' : 'none';
            elements.subtitlesOption.style.display = info && info.has_subtitles ? 'flex' : 'none';
        }

        updatePlaylistCount();
    }

    // --- Playlist Rendering ---
    function renderPlaylist(videos) {
        elements.playlistList.innerHTML = '';
        videos.forEach(v => {
            const item = document.createElement('label');
            item.className = 'playlist-item';
            item.style.cssText = 'display: flex; align-items: center; gap: 10px; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer;';
            item.innerHTML = `
                <input type="checkbox" class="playlist-checkbox" value="${v.index}" checked>
                <div style="width: 40px; height: 24px; border-radius: 4px; overflow: hidden; background: #000; flex-shrink: 0;">
                    ${v.thumbnail ? `<img src="${v.thumbnail}" style="width: 100%; height: 100%; object-fit: cover;">` : ''}
                </div>
                <div style="flex: 1; min-width: 0;">
                    <div style="font-size: 0.85rem; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${v.index}. ${escapeHtml(v.title)}</div>
                    ${v.duration ? `<div style="font-size: 0.7rem; color: #9ca3af;">${v.duration}</div>` : ''}
                </div>
            `;
            const checkbox = item.querySelector('.playlist-checkbox');
            checkbox.addEventListener('change', updatePlaylistCount);
            elements.playlistList.appendChild(item);
        });
        updatePlaylistCount();
    }

    function updatePlaylistCount() {
        if (!state.videoInfo || !state.videoInfo.is_playlist) return;
        const checked = elements.playlistList.querySelectorAll('.playlist-checkbox:checked').length;
        elements.playlistCount.textContent = checked;
        elements.btnDownload.disabled = (checked === 0 || !state.selectedQuality);
    }

    if (elements.btnSelectAllPlaylist) elements.btnSelectAllPlaylist.addEventListener('click', () => {
        elements.playlistList.querySelectorAll('.playlist-checkbox').forEach(cb => cb.checked = true);
        updatePlaylistCount();
    });

    if (elements.btnSelectNonePlaylist) elements.btnSelectNonePlaylist.addEventListener('click', () => {
        elements.playlistList.querySelectorAll('.playlist-checkbox').forEach(cb => cb.checked = false);
        updatePlaylistCount();
    });

    // --- Advanced Options ---
    elements.btnAdvanced.addEventListener('click', () => {
        const isOpen = elements.advancedOptions.style.display !== 'none';
        elements.advancedOptions.style.display = isOpen ? 'none' : 'block';
        elements.btnAdvanced.classList.toggle('open', !isOpen);
    });

    // --- Download ---
    elements.btnDownload.addEventListener('click', startDownload);

    function startDownload() {
        if (!state.currentDownloadId || !state.selectedQuality) return;

        const format = document.querySelector('input[name="format"]:checked')?.value || 'mp4';
        const audioQuality = document.getElementById('audioQuality')?.value || '192';
        const embedThumbnail = document.getElementById('embedThumbnail')?.checked || false;
        const embedSubtitles = document.getElementById('embedSubtitles')?.checked || false;
        const subtitleLang = document.getElementById('subtitleLang')?.value || 'es,en';

        let playlistItems = null;
        if (state.videoInfo && state.videoInfo.is_playlist) {
            const checkedBoxes = Array.from(elements.playlistList.querySelectorAll('.playlist-checkbox:checked'));
            if (checkedBoxes.length === 0) {
                showToast('Selecciona al menos un video de la lista', 'error');
                return;
            }
            playlistItems = checkedBoxes.map(cb => cb.value).join(',');
        }

        socket.emit('start_download', {
            download_id: state.currentDownloadId,
            quality: state.selectedQuality,
            format: format,
            audio_quality: audioQuality,
            embed_thumbnail: embedThumbnail,
            embed_subtitles: embedSubtitles,
            subtitle_lang: subtitleLang,
            playlist_items: playlistItems
        });

        // If no active download, show progress immediately; otherwise keep URL section visible
        if (!state.isDownloading) {
            state.isDownloading = true;
            state.activeDownloadId = state.currentDownloadId;
            elements.videoSection.style.display = 'none';
            elements.progressSection.style.display = 'block';
            resetProgress();
        } else {
            // Queued - hide video section, show toast, reset for new URL
            elements.videoSection.style.display = 'none';
            elements.statusContainer.style.display = 'none';
            showToast('Descarga añadida a la cola', 'success');
        }

        // Reset state for a new analysis
        state.currentDownloadId = null;
        state.selectedQuality = null;
        state.videoInfo = null;
        elements.urlInput.value = '';
        enableAnalyze();
    }

    function resetProgress() {
        elements.progressFill.style.width = '0%';
        elements.progressGlow.style.width = '0%';
        elements.progressPercentage.textContent = '0%';
        elements.detailSpeed.querySelector('span').textContent = 'Velocidad: --';
        elements.detailSize.querySelector('span').textContent = 'Tamaño: --';
        elements.detailETA.querySelector('span').textContent = 'ETA: --';
        elements.progressStatus.querySelector('span').textContent = 'Preparando descarga...';
        elements.progressTitle.innerHTML = '<i class="fas fa-download"></i> Descargando...';
        elements.btnCancel.style.display = 'flex';
    }

    // --- Handle Progress Updates ---
    function handleDownloadProgress(data) {
        if (data.orig_download_id) {
            if (state.activeDownloadId === data.orig_download_id) {
                state.activeDownloadId = data.download_id;
            }
            if (state.currentDownloadId === data.orig_download_id) {
                state.currentDownloadId = data.download_id;
            }
        }

        // If this is a 'starting' event for a new download (queue processing next item)
        if (data.phase === 'starting') {
            state.activeDownloadId = data.download_id;
            state.isDownloading = true;
            elements.videoSection.style.display = 'none';
            elements.completeSection.style.display = 'none';
            elements.progressSection.style.display = 'block';
            resetProgress();
        }

        if (data.download_id !== state.activeDownloadId) return;

        switch (data.phase) {
            case 'starting':
                elements.progressStatus.querySelector('span').textContent = data.message;
                break;

            case 'downloading':
                updateProgress(data);
                break;

            case 'processing':
                elements.progressTitle.innerHTML = '<i class="fas fa-cog fa-spin"></i> Procesando...';
                elements.progressFill.style.width = '100%';
                elements.progressGlow.style.width = '100%';
                elements.progressPercentage.textContent = '100%';
                elements.progressStatus.querySelector('span').textContent = data.message;
                break;

            case 'complete':
                showDownloadComplete(data);
                break;

            case 'error':
                showDownloadError(data.message);
                break;

            case 'cancelled':
                showDownloadCancelled();
                break;

            case 'cancelling':
                elements.progressStatus.querySelector('span').textContent = data.message;
                elements.btnCancel.style.display = 'none';
                break;
        }
    }

    function updateProgress(data) {
        const pct = Math.min(100, data.percentage || 0);
        elements.progressFill.style.width = pct + '%';
        elements.progressGlow.style.width = pct + '%';
        elements.progressPercentage.textContent = pct.toFixed(1) + '%';

        if (data.speed) {
            elements.detailSpeed.querySelector('span').textContent = `Velocidad: ${data.speed}`;
        }
        if (data.total) {
            elements.detailSize.querySelector('span').textContent = `${data.downloaded} / ${data.total}`;
        }
        if (data.eta) {
            elements.detailETA.querySelector('span').textContent = `ETA: ${data.eta}`;
        }

        elements.progressStatus.querySelector('span').textContent = data.message;
    }

    function showDownloadComplete(data) {
        // Check if there are more items queued - if so, don't show complete section
        // The next download's 'starting' event will take over the progress section
        const hasQueued = state.queue.some(q => q.status === 'queued');
        if (hasQueued) {
            // Brief toast, keep progress section visible for the next download
            showToast('¡Descarga completada! Siguiente en cola...', 'success');
            setTimeout(() => { loadRecentDownloads(); loadQuota(); }, 1000);
            return;
        }

        state.isDownloading = false;

        elements.progressSection.style.display = 'none';
        elements.completeSection.style.display = 'block';
        if (data.filename && data.filename.includes('videos descargados')) {
            elements.btnSave.style.display = 'none';
            elements.completeInfo.innerHTML = `${data.message}<br><small style="opacity:0.8; font-size: 0.85em;">Los videos están disponibles individualmente en la lista de "Descargas recientes" abajo.</small>`;
        } else {
            elements.btnSave.style.display = 'inline-flex';
            elements.btnSave.href = `/api/download-file/${state.activeDownloadId}`;
            elements.btnSave.download = data.filename || 'download';
            elements.completeInfo.textContent = `${data.filename || 'archivo'} - ${data.file_size || 'desconocido'}`;
        }

        showToast('¡Descarga completada!', 'success');

        // Refresh recent downloads and quota after a short delay
        setTimeout(() => {
            loadRecentDownloads();
            loadQuota();
        }, 1000);
    }

    function showDownloadError(message) {
        const hasQueued = state.queue.some(q => q.status === 'queued');
        if (hasQueued) {
            showToast(message || '❌ Error durante la descarga', 'error');
            return;
        }
        state.isDownloading = false;
        elements.progressSection.style.display = 'none';
        showToast(message || '❌ Error durante la descarga', 'error');
        enableAnalyze();
    }

    function showDownloadCancelled() {
        const hasQueued = state.queue.some(q => q.status === 'queued');
        if (hasQueued) {
            showToast('Descarga cancelada', 'info');
            return;
        }
        state.isDownloading = false;
        elements.progressSection.style.display = 'none';
        showToast('Descarga cancelada', 'info');
        enableAnalyze();
    }

    // --- Cancel Download ---
    elements.btnCancel.addEventListener('click', () => {
        if (state.activeDownloadId) {
            socket.emit('cancel_download', { download_id: state.activeDownloadId });
        }
    });

    // --- New Download ---
    elements.btnNewDownload.addEventListener('click', () => {
        elements.completeSection.style.display = 'none';
        elements.statusContainer.style.display = 'none';
        elements.videoSection.style.display = 'none';
        elements.urlInput.value = '';
        elements.urlInput.focus();
        state.currentDownloadId = null;
        state.activeDownloadId = null;
        state.selectedQuality = null;
        state.videoInfo = null;
        state.isDownloading = false;
        enableAnalyze();
        loadRecentDownloads();
    });

    // --- Recent Downloads ---
    async function loadRecentDownloads() {
        try {
            const response = await fetch('/api/recent-downloads');
            if (!response.ok) return;

            const downloads = await response.json();
            state.recentDownloads = downloads;

            if (downloads.length === 0) {
                elements.recentSection.style.display = 'none';
                return;
            }

            elements.recentSection.style.display = 'block';
            renderRecentDownloads(downloads);
            startCountdownTimer();
        } catch (err) {
            console.error('Error loading recent downloads:', err);
        }
    }

    function renderRecentDownloads(downloads) {
        const now = Date.now() / 1000;
        elements.recentList.innerHTML = '';

        if (downloads.length === 0) {
            elements.recentList.innerHTML = `
                <div class="recent-empty">
                    <i class="fas fa-inbox"></i>
                    No hay descargas recientes
                </div>`;
            return;
        }

        downloads.forEach(dl => {
            const remaining = Math.max(0, dl.expires_at - now);
            const totalDuration = 3600; // 1 hour
            const percentage = Math.max(0, (remaining / totalDuration) * 100);
            let barClass = '';
            if (percentage < 16) barClass = 'critical';
            else if (percentage < 40) barClass = 'expiring';

            const item = document.createElement('div');
            item.className = 'recent-item';
            item.dataset.downloadId = dl.id;
            item.dataset.expiresAt = dl.expires_at;

            const thumbHtml = dl.thumbnail
                ? `<div class="recent-thumb"><img src="${escapeHtml(dl.thumbnail)}" alt="" onerror="this.parentElement.style.display='none'"></div>`
                : '';

            item.innerHTML = `
                ${thumbHtml}
                <div class="recent-info">
                    <div class="recent-filename" title="${escapeHtml(dl.filename)}">${escapeHtml(dl.filename)}</div>
                    <div class="recent-meta">
                        <span><i class="fas fa-file"></i> ${dl.file_size_str}</span>
                        <span><i class="fas fa-tag"></i> ${escapeHtml(dl.quality)}</span>
                        <span class="recent-countdown" data-expires="${dl.expires_at}">
                            <i class="fas fa-clock"></i> ${formatRemainingTime(remaining)}
                        </span>
                    </div>
                    <div class="recent-expiry">
                        <div class="recent-expiry-bar ${barClass}" style="width: ${percentage}%"></div>
                    </div>
                </div>
                <div class="recent-actions">
                    ${isPlayable(dl.filename) ? `<button class="recent-play-btn" data-id="${dl.id}" title="Reproducir">
                        <i class="fas fa-play"></i>
                    </button>
                    ${['.mp4', '.mkv', '.webm', '.avi', '.mov', '.ts'].includes(getFileExt(dl.filename)) ? `<button class="recent-trim-btn" data-id="${dl.id}" data-filename="${escapeHtml(dl.filename)}" title="Recortar">
                        <i class="fas fa-cut"></i>
                    </button>` : ''}
                    ` : ''}
                    <a href="/api/download-file/${dl.id}" download="${escapeHtml(dl.filename)}"
                       class="recent-download-btn" title="Descargar">
                        <i class="fas fa-download"></i>
                    </a>
                    ${isPlayable(dl.filename) ? `<button class="recent-public-link-btn" data-id="${dl.id}" title="Enlace publico">
                        <i class="fas fa-link"></i>
                    </button>` : ''}
                    ${navigator.share ? `<button class="recent-share-btn" data-id="${dl.id}" data-filename="${escapeHtml(dl.filename)}" title="Compartir">
                        <i class="fas fa-share-alt"></i>
                    </button>` : ''}
                    <button class="recent-save-btn" data-id="${dl.id}" title="Guardar">
                        <i class="fas fa-bookmark"></i>
                    </button>
                    <button class="recent-delete-btn" data-id="${dl.id}" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;

            // Delete button handler
            const deleteBtn = item.querySelector('.recent-delete-btn');
            deleteBtn.addEventListener('click', () => deleteRecentDownload(dl.id));

            // Play button handler
            const playBtn = item.querySelector('.recent-play-btn');
            if (playBtn) {
                playBtn.addEventListener('click', (e) => openPlayer(dl.id, dl.filename, dl.video_title || dl.filename, dl.thumbnail, e));
            }

            // Trim button handler
            const trimBtn = item.querySelector('.recent-trim-btn');
            if (trimBtn) {
                trimBtn.addEventListener('click', () => openTrimModal(dl.id, dl.filename));
            }

            // Public link button handler
            const publicLinkBtn = item.querySelector('.recent-public-link-btn');
            if (publicLinkBtn) {
                publicLinkBtn.addEventListener('click', () => createPublicLink(dl.id, publicLinkBtn));
            }

            // Share button handler
            const shareBtn = item.querySelector('.recent-share-btn');
            if (shareBtn) {
                shareBtn.addEventListener('click', async () => {
                    const btn = shareBtn;
                    const origIcon = btn.innerHTML;
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                    btn.disabled = true;
                    try {
                        const title = dl.video_title || dl.filename;
                        const shareUrl = `${window.location.origin}/api/download-file/${dl.id}`;

                        // Limit direct file sharing to <= 50MB to prevent mobile browser crashes
                        const MAX_DIRECT_SHARE_SIZE = 50 * 1024 * 1024; // 50 MB

                        // Default to sharing link if file_size is missing, just to be safe
                        if (dl.file_size && dl.file_size <= MAX_DIRECT_SHARE_SIZE) {
                            // Small file: fetch and share directly
                            const response = await fetch(`/api/download-file/${dl.id}`);
                            const blob = await response.blob();
                            const file = new File([blob], dl.filename, { type: blob.type });
                            await navigator.share({
                                title: title,
                                files: [file]
                            });
                        } else {
                            // Large file: share a download link instead
                            await navigator.share({
                                title: title,
                                text: `Descarga "${title}" (${dl.file_size_str}):\n\n${shareUrl}`,
                                url: shareUrl
                            });
                        }
                    } catch (err) {
                        if (err.name !== 'AbortError') {
                            console.error('Share error:', err);
                            const shareUrl = `${window.location.origin}/api/download-file/${dl.id}`;
                            try {
                                await navigator.clipboard.writeText(shareUrl);
                                showToast('Enlace copiado al portapapeles', 'success');
                            } catch (clipErr) {
                                showToast('No se pudo compartir el archivo', 'error');
                            }
                        }
                    } finally {
                        btn.innerHTML = origIcon;
                        btn.disabled = false;
                    }
                });
            }

            // Save button handler
            const saveBtn = item.querySelector('.recent-save-btn');
            if (saveBtn) {
                saveBtn.addEventListener('click', () => saveDownload(dl.id));
            }

            elements.recentList.appendChild(item);
        });
    }

    function startCountdownTimer() {
        // Clear existing timer
        if (state.countdownTimer) clearInterval(state.countdownTimer);

        state.countdownTimer = setInterval(() => {
            const now = Date.now() / 1000;
            const countdowns = document.querySelectorAll('.recent-countdown');
            let anyActive = false;

            countdowns.forEach(el => {
                const expiresAt = parseFloat(el.dataset.expires);
                const remaining = Math.max(0, expiresAt - now);

                if (remaining <= 0) {
                    // Remove expired item
                    const item = el.closest('.recent-item');
                    if (item) {
                        item.style.opacity = '0.3';
                        setTimeout(() => item.remove(), 500);
                    }
                } else {
                    anyActive = true;
                    el.innerHTML = `<i class="fas fa-clock"></i> ${formatRemainingTime(remaining)}`;

                    // Update expiry bar
                    const item = el.closest('.recent-item');
                    if (item) {
                        const bar = item.querySelector('.recent-expiry-bar');
                        if (bar) {
                            const pct = (remaining / 3600) * 100;
                            bar.style.width = pct + '%';
                            bar.className = 'recent-expiry-bar';
                            if (pct < 16) bar.classList.add('critical');
                            else if (pct < 40) bar.classList.add('expiring');
                        }
                    }
                }
            });

            // If no active downloads, hide section and stop timer
            if (!anyActive) {
                elements.recentSection.style.display = 'none';
                clearInterval(state.countdownTimer);
                state.countdownTimer = null;
            }
        }, 1000);
    }

    async function deleteRecentDownload(downloadId) {
        try {
            const response = await fetch(`/api/delete-download/${downloadId}`, { method: 'POST' });
            if (response.ok) {
                showToast('Descarga eliminada', 'success');
                loadRecentDownloads();
                loadSavedDownloads();
                loadQuota();
            } else {
                const data = await response.json();
                showToast(data.error || 'Error al eliminar', 'error');
            }
        } catch (err) {
            showToast('Error de conexión', 'error');
        }
    }

    // --- Saved Downloads ---
    async function saveDownload(downloadId) {
        try {
            const response = await fetch(`/api/save-download/${downloadId}`, { method: 'POST' });
            if (response.ok) {
                const data = await response.json();
                showToast(data.message, 'success');
                loadRecentDownloads();
                loadSavedDownloads();
                loadQuota();
            } else {
                const data = await response.json();
                showToast(data.error || 'Error al guardar', 'error');
            }
        } catch (err) {
            showToast('Error de conexión', 'error');
        }
    }

    async function loadCollections() {
        try {
            const response = await fetch('/api/collections');
            if (!response.ok) return;
            state.collections = await response.json();
            renderCollectionTabs();
        } catch (err) {
            console.error('Error loading collections:', err);
        }
    }

    function renderCollectionTabs() {
        const container = document.getElementById('collectionTabs');
        if (!container) return;
        container.innerHTML = '';

        // "Todos" tab
        const allTab = document.createElement('button');
        allTab.className = `collection-tab${state.activeCollection === null ? ' active' : ''}`;
        allTab.innerHTML = `<i class="fas fa-layer-group" style="font-size:0.7rem;"></i> Todos`;
        allTab.addEventListener('click', () => { state.activeCollection = null; loadSavedDownloads(); renderCollectionTabs(); });
        container.appendChild(allTab);

        // Collection tabs
        state.collections.forEach(col => {
            const tab = document.createElement('button');
            tab.className = `collection-tab${state.activeCollection === col.id ? ' active' : ''}`;
            tab.innerHTML = `<span class="tab-dot" style="background:${escapeHtml(col.color)};"></span> ${escapeHtml(col.name)} <span class="tab-count">(${col.video_count})</span><span class="collection-tab-edit" title="Editar"><i class="fas fa-pen"></i></span>`;
            tab.addEventListener('click', (e) => {
                if (e.target.closest('.collection-tab-edit')) {
                    openCollectionModal(col);
                    return;
                }
                state.activeCollection = col.id;
                loadSavedDownloads();
                renderCollectionTabs();
            });
            container.appendChild(tab);
        });

        // Add button
        const addBtn = document.createElement('button');
        addBtn.className = 'collection-tab-add';
        addBtn.innerHTML = '<i class="fas fa-plus"></i>';
        addBtn.title = 'Nueva colección';
        addBtn.addEventListener('click', () => openCollectionModal(null));
        container.appendChild(addBtn);
    }

    function openCollectionModal(collection) {
        const modal = document.getElementById('collectionModal');
        const titleEl = document.getElementById('collectionModalTitle');
        const nameInput = document.getElementById('collectionNameInput');
        const deleteBtn = document.getElementById('btnDeleteCollection');
        const swatches = document.querySelectorAll('#colorPicker .color-swatch');

        state.editingCollectionId = collection ? collection.id : null;
        titleEl.innerHTML = collection
            ? '<i class="fas fa-folder-open"></i> Editar colección'
            : '<i class="fas fa-folder-plus"></i> Nueva colección';
        nameInput.value = collection ? collection.name : '';
        deleteBtn.style.display = collection ? 'block' : 'none';

        const activeColor = collection ? collection.color : '#8b5cf6';
        swatches.forEach(s => {
            s.classList.toggle('active', s.dataset.color === activeColor);
            s.style.borderColor = s.dataset.color === activeColor ? 'white' : 'transparent';
        });

        modal.style.display = 'flex';
        setTimeout(() => nameInput.focus(), 100);
    }

    function closeCollectionModal() {
        document.getElementById('collectionModal').style.display = 'none';
        state.editingCollectionId = null;
    }

    async function saveCollection() {
        const name = document.getElementById('collectionNameInput').value.trim();
        const activeSwatch = document.querySelector('#colorPicker .color-swatch.active');
        const color = activeSwatch ? activeSwatch.dataset.color : '#8b5cf6';
        if (!name) { showToast('Escribe un nombre', 'error'); return; }

        try {
            if (state.editingCollectionId) {
                await fetch(`/api/collections/${state.editingCollectionId}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, color})
                });
                showToast('Colección actualizada', 'success');
            } else {
                await fetch('/api/collections', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, color})
                });
                showToast('Colección creada', 'success');
            }
            closeCollectionModal();
            await loadCollections();
            loadSavedDownloads();
        } catch (err) {
            showToast('Error al guardar colección', 'error');
        }
    }

    async function deleteCollection(collectionId) {
        if (!confirm('¿Eliminar esta colección? Los videos no se borrarán.')) return;
        try {
            await fetch(`/api/collections/${collectionId}`, {method: 'DELETE'});
            showToast('Colección eliminada', 'success');
            if (state.activeCollection === collectionId) state.activeCollection = null;
            closeCollectionModal();
            await loadCollections();
            loadSavedDownloads();
        } catch (err) {
            showToast('Error al eliminar colección', 'error');
        }
    }

    async function toggleCollectionAssign(downloadId, collectionId, isAssigned) {
        try {
            if (isAssigned) {
                await fetch(`/api/collections/${collectionId}/remove/${downloadId}`, {method: 'DELETE'});
            } else {
                await fetch(`/api/collections/${collectionId}/add/${downloadId}`, {method: 'POST'});
            }
            await loadCollections();
            loadSavedDownloads();
        } catch (err) {
            showToast('Error al actualizar colección', 'error');
        }
    }

    async function loadSavedDownloads() {
        try {
            let url = '/api/saved-downloads';
            if (state.activeCollection) url += `?collection=${state.activeCollection}`;
            const response = await fetch(url);
            if (!response.ok) return;

            const downloads = await response.json();
            state.savedDownloads = downloads;

            if (downloads.length === 0 && !state.activeCollection && state.collections.length === 0) {
                elements.savedSection.style.display = 'none';
                return;
            }

            elements.savedSection.style.display = 'block';
            renderSavedDownloads(downloads);
        } catch (err) {
            console.error('Error loading saved downloads:', err);
        }
    }

    function renderSavedDownloads(downloads) {
        elements.savedList.innerHTML = '';

        if (downloads.length === 0) {
            elements.savedList.innerHTML = `
                <div class="recent-empty">
                    <i class="fas fa-${state.activeCollection ? 'folder-open' : 'bookmark'}"></i>
                    ${state.activeCollection ? 'No hay videos en esta colección' : 'No hay videos guardados'}
                </div>`;
            return;
        }

        downloads.forEach(dl => {
            const item = document.createElement('div');
            item.className = 'recent-item saved-item';
            item.dataset.downloadId = dl.id;

            const thumbHtml = dl.thumbnail
                ? `<div class="recent-thumb"><img src="${escapeHtml(dl.thumbnail)}" alt="" onerror="this.parentElement.style.display='none'"></div>`
                : '';

            const collectionBadges = (dl.collections && dl.collections.length > 0)
                ? `<div class="collection-badges">${dl.collections.map(c => `<span class="collection-mini-badge"><span class="dot" style="background:${escapeHtml(c.color)};"></span>${escapeHtml(c.name)}</span>`).join('')}</div>`
                : '';

            item.innerHTML = `
                ${thumbHtml}
                <div class="recent-info">
                    <div class="recent-filename" title="${escapeHtml(dl.filename)}">${escapeHtml(dl.filename)}</div>
                    <div class="recent-meta">
                        <span><i class="fas fa-file"></i> ${dl.file_size_str}</span>
                        <span><i class="fas fa-tag"></i> ${escapeHtml(dl.quality)}</span>
                        <span class="saved-badge"><i class="fas fa-bookmark"></i> Guardado</span>
                    </div>
                    ${collectionBadges}
                </div>
                <div class="recent-actions">
                    ${isPlayable(dl.filename) ? `<button class="recent-play-btn" data-id="${dl.id}" title="Reproducir">
                        <i class="fas fa-play"></i>
                    </button>
                    ${['.mp4', '.mkv', '.webm', '.avi', '.mov', '.ts'].includes(getFileExt(dl.filename)) ? `<button class="recent-trim-btn" data-id="${dl.id}" data-filename="${escapeHtml(dl.filename)}" title="Recortar">
                        <i class="fas fa-cut"></i>
                    </button>` : ''}
                    ` : ''}
                    <a href="/api/download-file/${dl.id}" download="${escapeHtml(dl.filename)}"
                       class="recent-download-btn" title="Descargar">
                        <i class="fas fa-download"></i>
                    </a>
                    ${isPlayable(dl.filename) ? `<button class="recent-public-link-btn" data-id="${dl.id}" title="Enlace publico">
                        <i class="fas fa-link"></i>
                    </button>` : ''}
                    ${navigator.share ? `<button class="recent-share-btn" data-id="${dl.id}" data-filename="${escapeHtml(dl.filename)}" title="Compartir">
                        <i class="fas fa-share-alt"></i>
                    </button>` : ''}
                    ${state.collections.length > 0 ? `<button class="collection-assign-btn" data-id="${dl.id}" title="Colecciones">
                        <i class="fas fa-folder"></i>
                    </button>` : ''}
                    <button class="recent-unsave-btn" data-id="${dl.id}" title="Quitar de guardados">
                        <i class="far fa-bookmark"></i>
                    </button>
                    <button class="recent-delete-btn" data-id="${dl.id}" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;

            // Delete button handler
            item.querySelector('.recent-delete-btn').addEventListener('click', () => deleteRecentDownload(dl.id));

            // Play button handler
            const playBtn = item.querySelector('.recent-play-btn');
            if (playBtn) {
                playBtn.addEventListener('click', (e) => openPlayer(dl.id, dl.filename, dl.video_title || dl.filename, dl.thumbnail, e));
            }

            // Trim button handler
            const trimBtn = item.querySelector('.recent-trim-btn');
            if (trimBtn) {
                trimBtn.addEventListener('click', () => openTrimModal(dl.id, dl.filename));
            }

            // Public link button handler
            const publicLinkBtn = item.querySelector('.recent-public-link-btn');
            if (publicLinkBtn) {
                publicLinkBtn.addEventListener('click', () => createPublicLink(dl.id, publicLinkBtn));
            }

            // Share button handler
            const shareBtn = item.querySelector('.recent-share-btn');
            if (shareBtn) {
                shareBtn.addEventListener('click', async () => {
                    const btn = shareBtn;
                    const origIcon = btn.innerHTML;
                    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                    btn.disabled = true;
                    try {
                        const title = dl.video_title || dl.filename;
                        const shareUrl = `${window.location.origin}/api/download-file/${dl.id}`;
                        const MAX_DIRECT_SHARE_SIZE = 50 * 1024 * 1024;
                        if (dl.file_size && dl.file_size <= MAX_DIRECT_SHARE_SIZE) {
                            const response = await fetch(`/api/download-file/${dl.id}`);
                            const blob = await response.blob();
                            const file = new File([blob], dl.filename, { type: blob.type });
                            await navigator.share({ title: title, files: [file] });
                        } else {
                            await navigator.share({
                                title: title,
                                text: `Descarga "${title}" (${dl.file_size_str}):\n\n${shareUrl}`,
                                url: shareUrl
                            });
                        }
                    } catch (err) {
                        if (err.name !== 'AbortError') {
                            const shareUrl = `${window.location.origin}/api/download-file/${dl.id}`;
                            try {
                                await navigator.clipboard.writeText(shareUrl);
                                showToast('Enlace copiado al portapapeles', 'success');
                            } catch (clipErr) {
                                showToast('No se pudo compartir el archivo', 'error');
                            }
                        }
                    } finally {
                        btn.innerHTML = origIcon;
                        btn.disabled = false;
                    }
                });
            }

            // Collection assign button handler
            const colBtn = item.querySelector('.collection-assign-btn');
            if (colBtn) {
                colBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    // Close any open dropdowns
                    document.querySelectorAll('.collection-dropdown').forEach(d => d.remove());
                    const dropdown = document.createElement('div');
                    dropdown.className = 'collection-dropdown';
                    const dlCollections = (dl.collections || []).map(c => c.id);
                    state.collections.forEach(col => {
                        const isAssigned = dlCollections.includes(col.id);
                        const dItem = document.createElement('button');
                        dItem.className = 'collection-dropdown-item';
                        dItem.innerHTML = `<span class="dot" style="background:${escapeHtml(col.color)};"></span> ${escapeHtml(col.name)} ${isAssigned ? '<span class="check"><i class="fas fa-check"></i></span>' : ''}`;
                        dItem.addEventListener('click', (ev) => {
                            ev.stopPropagation();
                            dropdown.remove();
                            toggleCollectionAssign(dl.id, col.id, isAssigned);
                        });
                        dropdown.appendChild(dItem);
                    });
                    colBtn.style.position = 'relative';
                    colBtn.appendChild(dropdown);
                    // Close on outside click
                    setTimeout(() => {
                        const closer = (ev) => { if (!dropdown.contains(ev.target)) { dropdown.remove(); document.removeEventListener('click', closer); } };
                        document.addEventListener('click', closer);
                    }, 10);
                });
            }

            // Unsave button handler
            item.querySelector('.recent-unsave-btn').addEventListener('click', () => saveDownload(dl.id));

            elements.savedList.appendChild(item);
        });
    }

    function formatRemainingTime(seconds) {
        if (seconds <= 0) return 'Expirado';
        seconds = Math.floor(seconds);
        if (seconds >= 3600) {
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            return `${h}h ${String(m).padStart(2, '0')}m`;
        } else if (seconds >= 60) {
            const m = Math.floor(seconds / 60);
            const s = seconds % 60;
            return `${m}m ${String(s).padStart(2, '0')}s`;
        } else {
            return `${seconds}s`;
        }
    }

    // --- Floating Player ---
    const playableVideoExts = ['.mp4', '.webm'];
    const playableAudioExts = ['.mp3', '.m4a', '.ogg', '.wav', '.aac'];

    function getFileExt(filename) {
        const dot = filename.lastIndexOf('.');
        return dot !== -1 ? filename.substring(dot).toLowerCase() : '';
    }

    function isPlayable(filename) {
        const ext = getFileExt(filename);
        return playableVideoExts.includes(ext) || playableAudioExts.includes(ext);
    }

    // === Fullscreen Player ===
    let fpWakeLock = null;
    let fpWakeLockEnabled = false;
    // AudioContext persists across open/close because createMediaElementSource can only be called once per element
    const fpAudioState = { ctx: null, videoSource: null, audioSource: null, analyser: null };
    let fpCurrentMedia = null;
    let fpCurrentDownloadId = null;
    let fpPlaybackSaveInterval = null;
    let fpStatsInterval = null;
    let fpVisualizerRAF = null;

    function formatDuration(secs) {
        if (!secs || secs <= 0) return null;
        const h = Math.floor(secs / 3600);
        const m = Math.floor((secs % 3600) / 60);
        const s = Math.floor(secs % 60);
        return h >= 1 ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}` : `${m}:${String(s).padStart(2,'0')}`;
    }

    function renderQuickTags(info, quality, fileSize) {
        let html = '';
        if (quality) html += `<span class="fp-quick-tag accent"><i class="fas fa-video"></i> ${quality}</span>`;
        if (fileSize) html += `<span class="fp-quick-tag cyan"><i class="fas fa-database"></i> ${fileSize}</span>`;
        const mi = info || {};
        const dur = formatDuration(mi.duration);
        if (dur) html += `<span class="fp-quick-tag pink"><i class="fas fa-clock"></i> ${dur}</span>`;
        if (mi.video_codec) html += `<span class="fp-quick-tag green"><i class="fas fa-microchip"></i> ${mi.video_codec}</span>`;
        if (mi.fps && mi.fps > 0) html += `<span class="fp-quick-tag warning"><i class="fas fa-film"></i> ${mi.fps} FPS</span>`;
        if (mi.audio_codec) html += `<span class="fp-quick-tag"><i class="fas fa-headphones"></i> ${mi.audio_codec}</span>`;
        return html;
    }

    function renderTechPanel(info, fileSizeBytes, filename) {
        const mi = info || {};
        let html = '<div class="fp-tech-grid">';

        if (mi.video_codec) {
            html += `<div class="fp-tech-section-label"><i class="fas fa-video"></i> Stream de Video</div>`;
            html += `<div class="fp-tech-item"><span class="fp-tech-label">Codec</span><span class="fp-tech-value highlight">${mi.video_codec}${mi.video_profile ? ' (' + mi.video_profile + ')' : ''}</span></div>`;
            if (mi.width && mi.height) html += `<div class="fp-tech-item"><span class="fp-tech-label">Resolucion</span><span class="fp-tech-value highlight">${mi.width}x${mi.height}</span></div>`;
            if (mi.fps && mi.fps > 0) html += `<div class="fp-tech-item"><span class="fp-tech-label">Framerate</span><span class="fp-tech-value">${mi.fps} fps</span></div>`;
            if (mi.video_bitrate && mi.video_bitrate > 0) html += `<div class="fp-tech-item"><span class="fp-tech-label">Bitrate Video</span><span class="fp-tech-value">${(mi.video_bitrate / 1000000).toFixed(1)} Mbps</span></div>`;
            if (mi.pix_fmt) html += `<div class="fp-tech-item"><span class="fp-tech-label">Pixel Format</span><span class="fp-tech-value">${mi.pix_fmt}</span></div>`;
            if (mi.color_space) html += `<div class="fp-tech-item"><span class="fp-tech-label">Color Space</span><span class="fp-tech-value">${mi.color_space}</span></div>`;
        }

        if (mi.audio_codec) {
            html += `<div class="fp-tech-separator"></div>`;
            html += `<div class="fp-tech-section-label"><i class="fas fa-headphones"></i> Stream de Audio</div>`;
            html += `<div class="fp-tech-item"><span class="fp-tech-label">Codec</span><span class="fp-tech-value pink">${mi.audio_codec}${mi.audio_profile ? ' (' + mi.audio_profile + ')' : ''}</span></div>`;
            if (mi.sample_rate && mi.sample_rate > 0) html += `<div class="fp-tech-item"><span class="fp-tech-label">Sample Rate</span><span class="fp-tech-value">${(mi.sample_rate / 1000).toFixed(1)} kHz</span></div>`;
            if (mi.channels) {
                const chStr = mi.channels === 2 ? 'Stereo' : mi.channels === 1 ? 'Mono' : mi.channels === 6 ? '5.1 Surround' : mi.channels + ' canales';
                html += `<div class="fp-tech-item"><span class="fp-tech-label">Canales</span><span class="fp-tech-value">${chStr}</span></div>`;
            }
            if (mi.audio_bitrate && mi.audio_bitrate > 0) html += `<div class="fp-tech-item"><span class="fp-tech-label">Bitrate Audio</span><span class="fp-tech-value">${Math.round(mi.audio_bitrate / 1000)} kbps</span></div>`;
        }

        html += `<div class="fp-tech-separator"></div>`;
        html += `<div class="fp-tech-section-label"><i class="fas fa-box"></i> Contenedor</div>`;
        if (mi.container) html += `<div class="fp-tech-item"><span class="fp-tech-label">Formato</span><span class="fp-tech-value">${mi.container.toUpperCase()}</span></div>`;
        if (mi.bitrate && mi.bitrate > 0) html += `<div class="fp-tech-item"><span class="fp-tech-label">Bitrate Total</span><span class="fp-tech-value">${(mi.bitrate / 1000000).toFixed(2)} Mbps</span></div>`;
        if (fileSizeBytes) html += `<div class="fp-tech-item"><span class="fp-tech-label">Tamano Archivo</span><span class="fp-tech-value">${Number(fileSizeBytes).toLocaleString()} bytes</span></div>`;
        if (filename) html += `<div class="fp-tech-item"><span class="fp-tech-label">Archivo</span><span class="fp-tech-value" style="font-size:0.7rem; word-break:break-all;">${filename}</span></div>`;

        html += '</div>';
        return html;
    }

    // --- Playback History (server-synced) ---
    function savePlaybackPosition() {
        if (fpCurrentMedia && fpCurrentDownloadId && fpCurrentMedia.currentTime > 5 && fpCurrentMedia.duration && fpCurrentMedia.currentTime < fpCurrentMedia.duration - 3) {
            const pos = Math.floor(fpCurrentMedia.currentTime);
            fetch(`/api/playback-position/${fpCurrentDownloadId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ position: pos })
            }).catch(() => {});
        }
    }
    async function getSavedPosition(downloadId) {
        try {
            const resp = await fetch(`/api/playback-position/${downloadId}`);
            if (!resp.ok) return 0;
            const data = await resp.json();
            return data.position || 0;
        } catch { return 0; }
    }
    function clearSavedPosition(downloadId) {
        fetch(`/api/playback-position/${downloadId}`, { method: 'DELETE' }).catch(() => {});
    }

    // --- Audio Visualizer ---
    function startAudioVisualizer() {
        const canvas = elements.playerAudioVisualizer;
        if (!canvas || !fpAudioState.analyser) return;
        canvas.style.display = 'block';
        const ctx = canvas.getContext('2d');
        const analyser = fpAudioState.analyser;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        function draw() {
            if (!fpCurrentMedia || fpCurrentMedia.paused) {
                fpVisualizerRAF = requestAnimationFrame(draw);
                return;
            }
            fpVisualizerRAF = requestAnimationFrame(draw);
            analyser.getByteFrequencyData(dataArray);

            const w = canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
            const h = canvas.height = canvas.offsetHeight * (window.devicePixelRatio || 1);
            ctx.clearRect(0, 0, w, h);

            const barCount = 64;
            const step = Math.floor(bufferLength / barCount);
            const barWidth = (w / barCount) * 0.7;
            const gap = (w / barCount) * 0.3;

            for (let i = 0; i < barCount; i++) {
                const value = dataArray[i * step] / 255;
                const barHeight = value * h * 0.85;
                const x = i * (barWidth + gap) + gap / 2;
                const gradient = ctx.createLinearGradient(0, h, 0, h - barHeight);
                gradient.addColorStop(0, '#6366f1');
                gradient.addColorStop(0.5, '#8b5cf6');
                gradient.addColorStop(1, '#ec4899');
                ctx.fillStyle = gradient;
                ctx.beginPath();
                ctx.roundRect(x, h - barHeight, barWidth, barHeight, 3);
                ctx.fill();
            }
        }
        draw();
    }
    function stopAudioVisualizer() {
        if (fpVisualizerRAF) { cancelAnimationFrame(fpVisualizerRAF); fpVisualizerRAF = null; }
        const canvas = elements.playerAudioVisualizer;
        if (canvas) { canvas.style.display = 'none'; }
    }

    // --- Live Stats ---
    function startLiveStats() {
        const el = elements.playerLiveStats;
        if (!el || !fpCurrentMedia) return;
        fpStatsInterval = setInterval(() => {
            if (!fpCurrentMedia) return;
            const media = fpCurrentMedia;
            let html = '';

            // Buffer health
            if (media.buffered && media.buffered.length > 0) {
                const buffEnd = media.buffered.end(media.buffered.length - 1);
                const ahead = Math.max(0, buffEnd - media.currentTime).toFixed(1);
                html += `<div><span class="fp-stat-label">Buffer</span><span class="fp-stat-value">${ahead}s</span></div>`;
            }

            // Dropped frames (video only)
            if (media.tagName === 'VIDEO' && media.getVideoPlaybackQuality) {
                const q = media.getVideoPlaybackQuality();
                html += `<div><span class="fp-stat-label">Dropped</span><span class="fp-stat-value">${q.droppedVideoFrames}/${q.totalVideoFrames}</span></div>`;
            }

            // Current time / duration
            if (media.duration && isFinite(media.duration)) {
                html += `<div><span class="fp-stat-label">Posicion</span><span class="fp-stat-value">${formatDuration(media.currentTime)} / ${formatDuration(media.duration)}</span></div>`;
            }

            // Resolution (video only)
            if (media.tagName === 'VIDEO' && media.videoWidth) {
                html += `<div><span class="fp-stat-label">Resolucion</span><span class="fp-stat-value">${media.videoWidth}x${media.videoHeight}</span></div>`;
            }

            // Playback rate
            html += `<div><span class="fp-stat-label">Velocidad</span><span class="fp-stat-value">${media.playbackRate}x</span></div>`;

            el.innerHTML = html;
        }, 1000);
    }
    function stopLiveStats() {
        if (fpStatsInterval) { clearInterval(fpStatsInterval); fpStatsInterval = null; }
        if (elements.playerLiveStats) elements.playerLiveStats.innerHTML = '';
    }

    function openPlayer(downloadId, filename, title, thumbnail, clickEvent) {
        const ext = getFileExt(filename);
        const isVideo = playableVideoExts.includes(ext);
        const streamUrl = `/api/stream/${downloadId}`;
        fpCurrentDownloadId = downloadId;

        // Reset both players
        elements.playerVideo.pause();
        elements.playerVideo.removeAttribute('src');
        elements.playerVideo.removeAttribute('poster');
        elements.playerVideo.style.display = 'none';
        elements.playerAudio.pause();
        elements.playerAudio.removeAttribute('src');
        elements.playerAudio.style.display = 'none';

        // Stop previous visualizer/stats
        stopAudioVisualizer();
        stopLiveStats();
        elements.playerLiveStats.style.display = 'none';

        // Configure the right player
        if (isVideo) {
            // Feature 1: Thumbnail as poster
            if (thumbnail) elements.playerVideo.poster = thumbnail;
            elements.playerVideo.src = streamUrl;
            elements.playerVideo.style.display = 'block';
            fpCurrentMedia = elements.playerVideo;
            // Show video controls, hide audio
            elements.playerVideoControls.style.display = 'block';
            elements.playerAudioControls.style.display = 'none';
            if (elements.playerAudioVisualizer) elements.playerAudioVisualizer.style.display = 'none';
            // Reset video controls state
            elements.fpVideoSeekProgress.style.width = '0%';
            elements.fpVideoSeekBuffered.style.width = '0%';
            elements.fpVideoSeekThumb.style.left = '0%';
            elements.fpVideoSeekInput.value = 0;
            elements.fpVideoTime.textContent = '0:00';
            elements.fpVideoDuration.textContent = '0:00';
            elements.fpVideoPlayBtn.innerHTML = '<i class="fas fa-pause"></i>';
        } else {
            elements.playerAudio.src = streamUrl;
            // Audio element stays hidden (no native controls), custom controls shown instead
            fpCurrentMedia = elements.playerAudio;
            elements.playerAudioControls.style.display = 'flex';
            elements.playerVideoControls.style.display = 'none';
            // Reset custom controls state
            elements.fpAudioSeekProgress.style.width = '0%';
            elements.fpAudioSeekBuffered.style.width = '0%';
            elements.fpAudioSeekInput.value = 0;
            elements.fpAudioTime.textContent = '0:00';
            elements.fpAudioDuration.textContent = '0:00';
            elements.fpAudioPlayBtn.innerHTML = '<i class="fas fa-pause"></i>';
        }

        elements.playerTitle.textContent = title || filename;
        elements.playerQuickTags.innerHTML = '';
        elements.playerTechPanel.style.display = 'none';
        elements.playerTechBody.innerHTML = '';
        elements.playerTechBody.classList.remove('open');
        elements.playerTechToggle.classList.remove('open');

        // Download button
        elements.playerDownloadBtn.href = `/api/download-file/${downloadId}`;
        elements.playerDownloadBtn.style.display = '';

        // PiP button
        if (isVideo && document.pictureInPictureEnabled) {
            elements.playerPipBtn.style.display = '';
        } else {
            elements.playerPipBtn.style.display = 'none';
        }

        // Stats button

        // Share timestamp button
        elements.playerShareBtn.style.display = '';

        // Original link button - hidden until we get the URL from media-info
        elements.playerOriginalBtn.style.display = 'none';

        // Reset wake lock state
        fpWakeLockEnabled = false;
        elements.playerBgPlayBtn.classList.remove('active');
        elements.playerBgPlayBtn.innerHTML = '<i class="fas fa-moon"></i> Pantalla activa';
        elements.playerBgStatus.classList.remove('visible');

        // Feature 2: Zoom animation from click position
        if (clickEvent && clickEvent.target) {
            const rect = clickEvent.target.closest('button').getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const ox = (cx / window.innerWidth * 100).toFixed(1);
            const oy = (cy / window.innerHeight * 100).toFixed(1);
            elements.playerOverlay.style.setProperty('--fp-origin-x', ox + '%');
            elements.playerOverlay.style.setProperty('--fp-origin-y', oy + '%');
        } else {
            elements.playerOverlay.style.setProperty('--fp-origin-x', '50%');
            elements.playerOverlay.style.setProperty('--fp-origin-y', '50%');
        }

        // Feature 3: Resume badge (async - fetches from server)
        const resumeBadge = elements.playerResumeBadge;
        resumeBadge.style.display = 'none';
        const mediaForResume = fpCurrentMedia;
        getSavedPosition(downloadId).then(savedPos => {
            if (savedPos > 5 && mediaForResume === fpCurrentMedia) {
                resumeBadge.innerHTML = `<i class="fas fa-history"></i> Continuar desde ${formatDuration(savedPos)}`;
                resumeBadge.style.display = 'flex';
                resumeBadge.onclick = () => {
                    if (fpCurrentMedia) fpCurrentMedia.currentTime = savedPos;
                    resumeBadge.style.display = 'none';
                };
                // Auto-seek on media load
                mediaForResume.addEventListener('loadedmetadata', () => {
                    if (savedPos > 0 && mediaForResume.duration && savedPos < mediaForResume.duration - 3) {
                        mediaForResume.currentTime = savedPos;
                    }
                    resumeBadge.style.display = 'none';
                }, { once: true });
            }
        });

        // Show overlay
        elements.playerOverlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Start saving playback position every 5 seconds
        if (fpPlaybackSaveInterval) clearInterval(fpPlaybackSaveInterval);
        fpPlaybackSaveInterval = setInterval(savePlaybackPosition, 5000);

        // Clear position when video ends
        fpCurrentMedia.addEventListener('ended', () => {
            clearSavedPosition(downloadId);
        }, { once: true });

        // Save on pause
        fpCurrentMedia.addEventListener('pause', savePlaybackPosition);

        // Fetch media info
        fetch(`/api/media-info/${downloadId}`)
            .then(r => r.json())
            .then(data => {
                if (data.media_info) {
                    elements.playerQuickTags.innerHTML = renderQuickTags(data.media_info, data.quality, data.file_size);
                    elements.playerTechBody.innerHTML = renderTechPanel(data.media_info, data.file_size_bytes, data.filename);
                    elements.playerTechPanel.style.display = '';
                }
                // Original link button
                if (data.video_url) {
                    elements.playerOriginalBtn.href = data.video_url;
                    elements.playerOriginalBtn.style.display = '';
                }
                // Media Session
                if ('mediaSession' in navigator) {
                    const art = (data.thumbnail || thumbnail) ? [{ src: data.thumbnail || thumbnail, sizes: '512x512', type: 'image/jpeg' }] : [];
                    navigator.mediaSession.metadata = new MediaMetadata({
                        title: title || filename,
                        artist: 'VideoDown by KiKoSo',
                        artwork: art
                    });
                }
            })
            .catch(() => {});

        // Setup Media Session handlers
        if ('mediaSession' in navigator) {
            navigator.mediaSession.setActionHandler('play', () => fpCurrentMedia && fpCurrentMedia.play());
            navigator.mediaSession.setActionHandler('pause', () => fpCurrentMedia && fpCurrentMedia.pause());
            navigator.mediaSession.setActionHandler('seekbackward', (d) => {
                if (fpCurrentMedia) fpCurrentMedia.currentTime = Math.max(0, fpCurrentMedia.currentTime - (d.seekOffset || 10));
            });
            navigator.mediaSession.setActionHandler('seekforward', (d) => {
                if (fpCurrentMedia) fpCurrentMedia.currentTime = Math.min(fpCurrentMedia.duration || 0, fpCurrentMedia.currentTime + (d.seekOffset || 10));
            });
            navigator.mediaSession.setActionHandler('seekto', (d) => {
                if (fpCurrentMedia) {
                    if (d.fastSeek && 'fastSeek' in fpCurrentMedia) fpCurrentMedia.fastSeek(d.seekTime);
                    else fpCurrentMedia.currentTime = d.seekTime;
                }
            });
        }

        // AudioContext + Analyser for visualizer and background audio
        // We use a persistent AudioContext because createMediaElementSource can only be called once per element
        fpCurrentMedia.addEventListener('play', function fpSetupAudio() {
            const sourceKey = isVideo ? 'videoSource' : 'audioSource';
            if (!fpAudioState.ctx) {
                try {
                    fpAudioState.ctx = new (window.AudioContext || window.webkitAudioContext)();
                    fpAudioState.analyser = fpAudioState.ctx.createAnalyser();
                    fpAudioState.analyser.fftSize = 256;
                    fpAudioState.analyser.connect(fpAudioState.ctx.destination);
                } catch(e) {}
            }
            // Connect this media element if not already connected
            if (fpAudioState.ctx && !fpAudioState[sourceKey]) {
                try {
                    fpAudioState[sourceKey] = fpAudioState.ctx.createMediaElementSource(fpCurrentMedia);
                    fpAudioState[sourceKey].connect(fpAudioState.analyser);
                } catch(e) {}
            }
            if (fpAudioState.ctx && fpAudioState.ctx.state === 'suspended') fpAudioState.ctx.resume();
            // Feature 4: Start visualizer for audio files
            if (!isVideo && fpAudioState.analyser) startAudioVisualizer();
        }, { once: true });
    }

    function closePlayer() {
        // Save playback position before closing
        savePlaybackPosition();

        // Release wake lock
        fpWakeLockEnabled = false;
        if (fpWakeLock) { fpWakeLock.release(); fpWakeLock = null; }

        // Stop intervals
        if (fpPlaybackSaveInterval) { clearInterval(fpPlaybackSaveInterval); fpPlaybackSaveInterval = null; }
        stopAudioVisualizer();
        stopLiveStats();

        // Stop media
        elements.playerVideo.pause();
        elements.playerVideo.removeAttribute('src');
        elements.playerVideo.removeAttribute('poster');
        elements.playerVideo.load();
        elements.playerAudio.pause();
        elements.playerAudio.removeAttribute('src');
        elements.playerAudio.load();

        // Exit PiP if active
        if (document.pictureInPictureElement) {
            document.exitPictureInPicture().catch(() => {});
        }

        fpCurrentMedia = null;
        fpCurrentDownloadId = null;
        // NOTE: fpAudioState persists - AudioContext and sources survive across open/close
        elements.playerOverlay.style.display = 'none';
        document.body.style.overflow = '';
    }

    elements.playerClose.addEventListener('click', closePlayer);

    // Close on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && elements.playerOverlay.style.display !== 'none') {
            closePlayer();
        }
    });

    // Tech panel toggle
    elements.playerTechToggle.addEventListener('click', () => {
        elements.playerTechToggle.classList.toggle('open');
        elements.playerTechBody.classList.toggle('open');
    });

    // PiP toggle
    elements.playerPipBtn.addEventListener('click', async () => {
        try {
            if (document.pictureInPictureElement) {
                await document.exitPictureInPicture();
            } else if (fpCurrentMedia && fpCurrentMedia.tagName === 'VIDEO') {
                await fpCurrentMedia.requestPictureInPicture();
            }
        } catch (e) { console.log('PiP failed:', e); }
    });

    elements.playerVideo.addEventListener('enterpictureinpicture', () => {
        elements.playerPipBtn.innerHTML = '<i class="fas fa-expand"></i> Salir PiP';
        elements.playerPipBtn.classList.add('active');
    });
    elements.playerVideo.addEventListener('leavepictureinpicture', () => {
        elements.playerPipBtn.innerHTML = '<i class="fas fa-compress"></i> PiP';
        elements.playerPipBtn.classList.remove('active');
    });

    // Feature 6: Share timestamp
    elements.playerShareBtn.addEventListener('click', async () => {
        if (!fpCurrentMedia || !fpCurrentDownloadId) return;
        const seconds = Math.floor(fpCurrentMedia.currentTime);
        try {
            // Create or get share link
            const resp = await fetch(`/api/share-link/${fpCurrentDownloadId}`, { method: 'POST' });
            if (!resp.ok) throw new Error('Failed to create share link');
            const data = await resp.json();
            const url = `${window.location.origin}/s/${data.token}?t=${seconds}`;
            await navigator.clipboard.writeText(url);
            showToast('Enlace copiado al portapapeles', 'success');
        } catch (e) {
            showToast('Error al compartir', 'error');
        }
    });

    // Wake Lock
    async function fpRequestWakeLock() {
        if (!('wakeLock' in navigator)) return false;
        try {
            fpWakeLock = await navigator.wakeLock.request('screen');
            fpWakeLock.addEventListener('release', () => {
                if (fpWakeLockEnabled && document.visibilityState === 'visible' && fpCurrentMedia && !fpCurrentMedia.paused) {
                    fpRequestWakeLock();
                }
            });
            return true;
        } catch (e) { return false; }
    }

    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible' && fpWakeLockEnabled && fpCurrentMedia && !fpCurrentMedia.paused) {
            fpRequestWakeLock();
        }
    });

    elements.playerBgPlayBtn.addEventListener('click', async () => {
        fpWakeLockEnabled = !fpWakeLockEnabled;
        if (fpWakeLockEnabled) {
            const ok = await fpRequestWakeLock();
            elements.playerBgPlayBtn.classList.add('active');
            elements.playerBgPlayBtn.innerHTML = '<i class="fas fa-sun"></i> Pantalla activa';
            elements.playerBgStatus.classList.add('visible');
            elements.playerBgStatusText.textContent = ok ? 'Pantalla activa — no se apagara durante la reproduccion' : 'Tu navegador no soporta Wake Lock';
        } else {
            if (fpWakeLock) { fpWakeLock.release(); fpWakeLock = null; }
            elements.playerBgPlayBtn.classList.remove('active');
            elements.playerBgPlayBtn.innerHTML = '<i class="fas fa-moon"></i> Pantalla activa';
            elements.playerBgStatus.classList.remove('visible');
        }
    });

    // --- Custom Audio Controls ---
    (function setupAudioControls() {
        const audio = elements.playerAudio;
        const playBtn = elements.fpAudioPlayBtn;
        const seekInput = elements.fpAudioSeekInput;
        const seekProgress = elements.fpAudioSeekProgress;
        const seekBuffered = elements.fpAudioSeekBuffered;
        const timeEl = elements.fpAudioTime;
        const durEl = elements.fpAudioDuration;
        const volBtn = elements.fpAudioVolBtn;
        const volInput = elements.fpAudioVolInput;
        let isSeeking = false;

        function fmtTime(s) {
            if (!s || !isFinite(s)) return '0:00';
            const m = Math.floor(s / 60);
            const sec = Math.floor(s % 60);
            return m + ':' + String(sec).padStart(2, '0');
        }

        // Play/Pause
        playBtn.addEventListener('click', () => {
            if (audio.paused) audio.play(); else audio.pause();
        });
        audio.addEventListener('play', () => {
            playBtn.innerHTML = '<i class="fas fa-pause"></i>';
        });
        audio.addEventListener('pause', () => {
            playBtn.innerHTML = '<i class="fas fa-play"></i>';
        });

        // Time update
        audio.addEventListener('timeupdate', () => {
            if (isSeeking) return;
            timeEl.textContent = fmtTime(audio.currentTime);
            if (audio.duration && isFinite(audio.duration)) {
                const pct = (audio.currentTime / audio.duration) * 1000;
                seekInput.value = pct;
                seekProgress.style.width = (pct / 10) + '%';
            }
        });
        audio.addEventListener('loadedmetadata', () => {
            durEl.textContent = fmtTime(audio.duration);
        });
        audio.addEventListener('durationchange', () => {
            durEl.textContent = fmtTime(audio.duration);
        });

        // Buffered
        audio.addEventListener('progress', () => {
            if (audio.buffered.length > 0 && audio.duration) {
                const buffEnd = audio.buffered.end(audio.buffered.length - 1);
                seekBuffered.style.width = (buffEnd / audio.duration * 100) + '%';
            }
        });

        // Seek
        seekInput.addEventListener('input', () => {
            isSeeking = true;
            const pct = seekInput.value / 1000;
            seekProgress.style.width = (pct * 100) + '%';
            if (audio.duration && isFinite(audio.duration)) {
                timeEl.textContent = fmtTime(pct * audio.duration);
            }
        });
        seekInput.addEventListener('change', () => {
            if (audio.duration && isFinite(audio.duration)) {
                audio.currentTime = (seekInput.value / 1000) * audio.duration;
            }
            isSeeking = false;
        });

        // Volume
        volInput.addEventListener('input', () => {
            audio.volume = volInput.value / 100;
            updateVolIcon();
        });
        volBtn.addEventListener('click', () => {
            audio.muted = !audio.muted;
            updateVolIcon();
        });
        function updateVolIcon() {
            const vol = audio.muted ? 0 : audio.volume;
            let icon = 'fa-volume-up';
            if (vol === 0) icon = 'fa-volume-mute';
            else if (vol < 0.5) icon = 'fa-volume-down';
            volBtn.innerHTML = `<i class="fas ${icon}"></i>`;
        }
    })();

    // --- Custom Video Controls ---
    (function setupVideoControls() {
        const video = elements.playerVideo;
        const playBtn = elements.fpVideoPlayBtn;
        const rwBtn = elements.fpVideoRwBtn;
        const ffBtn = elements.fpVideoFfBtn;
        const seekInput = elements.fpVideoSeekInput;
        const seekProgress = elements.fpVideoSeekProgress;
        const seekBuffered = elements.fpVideoSeekBuffered;
        const seekThumb = elements.fpVideoSeekThumb;
        const seekPreview = elements.fpVideoSeekPreview;
        const seekWrap = elements.fpVideoSeekWrap;
        const timeEl = elements.fpVideoTime;
        const durEl = elements.fpVideoDuration;
        const volBtn = elements.fpVideoVolBtn;
        const volInput = elements.fpVideoVolInput;
        const fsBtn = elements.fpVideoFsBtn;
        let isSeeking = false;
        let hideTimer = null;
        const controls = elements.playerVideoControls;

        function fmtTime(s) {
            if (!s || !isFinite(s)) return '0:00';
            const h = Math.floor(s / 3600);
            const m = Math.floor((s % 3600) / 60);
            const sec = Math.floor(s % 60);
            if (h > 0) return h + ':' + String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
            return m + ':' + String(sec).padStart(2, '0');
        }

        // Auto-hide controls
        function showControls() {
            controls.classList.add('fp-vc-visible');
            clearTimeout(hideTimer);
            hideTimer = setTimeout(() => {
                if (!video.paused && !isSeeking) controls.classList.remove('fp-vc-visible');
            }, 3000);
        }

        // Show on mouse move over media area
        const mediaArea = controls.parentElement;
        mediaArea.addEventListener('mousemove', showControls);
        mediaArea.addEventListener('mouseleave', () => {
            clearTimeout(hideTimer);
            if (!video.paused && !isSeeking) controls.classList.remove('fp-vc-visible');
        });
        mediaArea.addEventListener('touchstart', showControls, { passive: true });

        // Click on video to toggle play/pause
        video.addEventListener('click', () => {
            if (video.paused) video.play(); else video.pause();
        });

        // Play/Pause
        playBtn.addEventListener('click', () => {
            if (video.paused) video.play(); else video.pause();
        });
        video.addEventListener('play', () => {
            playBtn.innerHTML = '<i class="fas fa-pause"></i>';
            showControls();
        });
        video.addEventListener('pause', () => {
            playBtn.innerHTML = '<i class="fas fa-play"></i>';
            controls.classList.add('fp-vc-visible');
            clearTimeout(hideTimer);
        });

        // Rewind / FastForward
        rwBtn.addEventListener('click', () => {
            video.currentTime = Math.max(0, video.currentTime - 10);
        });
        ffBtn.addEventListener('click', () => {
            video.currentTime = Math.min(video.duration || 0, video.currentTime + 10);
        });

        // Time update
        video.addEventListener('timeupdate', () => {
            if (isSeeking) return;
            timeEl.textContent = fmtTime(video.currentTime);
            if (video.duration && isFinite(video.duration)) {
                const pct = (video.currentTime / video.duration) * 100;
                seekInput.value = pct * 10;
                seekProgress.style.width = pct + '%';
                seekThumb.style.left = pct + '%';
            }
        });
        video.addEventListener('loadedmetadata', () => {
            durEl.textContent = fmtTime(video.duration);
        });
        video.addEventListener('durationchange', () => {
            durEl.textContent = fmtTime(video.duration);
        });

        // Buffered
        video.addEventListener('progress', () => {
            if (video.buffered.length > 0 && video.duration) {
                const buffEnd = video.buffered.end(video.buffered.length - 1);
                seekBuffered.style.width = (buffEnd / video.duration * 100) + '%';
            }
        });

        // Seek
        seekInput.addEventListener('input', () => {
            isSeeking = true;
            const pct = seekInput.value / 10;
            seekProgress.style.width = pct + '%';
            seekThumb.style.left = pct + '%';
            if (video.duration && isFinite(video.duration)) {
                timeEl.textContent = fmtTime((pct / 100) * video.duration);
            }
        });
        seekInput.addEventListener('change', () => {
            if (video.duration && isFinite(video.duration)) {
                video.currentTime = (seekInput.value / 1000) * video.duration;
            }
            isSeeking = false;
        });

        // Seek preview tooltip on hover
        seekWrap.addEventListener('mousemove', (e) => {
            const rect = seekWrap.getBoundingClientRect();
            const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
            if (video.duration && isFinite(video.duration)) {
                seekPreview.textContent = fmtTime(pct * video.duration);
                seekPreview.style.left = (pct * 100) + '%';
                seekPreview.style.display = 'block';
            }
        });
        seekWrap.addEventListener('mouseleave', () => {
            seekPreview.style.display = 'none';
        });

        // Volume
        volInput.addEventListener('input', () => {
            video.volume = volInput.value / 100;
            updateVolIcon();
        });
        volBtn.addEventListener('click', () => {
            video.muted = !video.muted;
            updateVolIcon();
        });
        function updateVolIcon() {
            const vol = video.muted ? 0 : video.volume;
            let icon = 'fa-volume-up';
            if (vol === 0) icon = 'fa-volume-mute';
            else if (vol < 0.5) icon = 'fa-volume-down';
            volBtn.innerHTML = `<i class="fas ${icon}"></i>`;
        }

        // Fullscreen
        fsBtn.addEventListener('click', async () => {
            const container = mediaArea;
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                try {
                    await (container.requestFullscreen || container.webkitRequestFullscreen || container.msRequestFullscreen).call(container);
                    // Lock to landscape on mobile
                    if (screen.orientation && screen.orientation.lock) {
                        screen.orientation.lock('landscape').catch(() => {});
                    }
                } catch(e) {}
            }
        });
        document.addEventListener('fullscreenchange', () => {
            if (document.fullscreenElement) {
                fsBtn.innerHTML = '<i class="fas fa-compress"></i>';
            } else {
                fsBtn.innerHTML = '<i class="fas fa-expand"></i>';
                // Unlock orientation when exiting fullscreen
                if (screen.orientation && screen.orientation.unlock) {
                    screen.orientation.unlock();
                }
            }
        });

        // Keyboard shortcuts when player is open
        document.addEventListener('keydown', (e) => {
            if (elements.playerOverlay.style.display === 'none') return;
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            if (!fpCurrentMedia || fpCurrentMedia !== video) return;
            switch(e.key) {
                case ' ': e.preventDefault(); if (video.paused) video.play(); else video.pause(); break;
                case 'ArrowLeft': e.preventDefault(); video.currentTime = Math.max(0, video.currentTime - 10); showControls(); break;
                case 'ArrowRight': e.preventDefault(); video.currentTime = Math.min(video.duration || 0, video.currentTime + 10); showControls(); break;
                case 'ArrowUp': e.preventDefault(); video.volume = Math.min(1, video.volume + 0.1); volInput.value = video.volume * 100; updateVolIcon(); showControls(); break;
                case 'ArrowDown': e.preventDefault(); video.volume = Math.max(0, video.volume - 0.1); volInput.value = video.volume * 100; updateVolIcon(); showControls(); break;
                case 'm': video.muted = !video.muted; updateVolIcon(); showControls(); break;
                case 'f': fsBtn.click(); break;
            }
        });
    })();

    // --- Trim Modal Logic ---
    function formatTimeCode(seconds) {
        if (!seconds || isNaN(seconds)) return "00:00:00";
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
    }

    function openTrimModal(downloadId, filename) {
        closePlayer();
        state.trimState.activeId = downloadId;
        const streamUrl = `/api/stream/${downloadId}`;

        elements.trimVideoPlayer.src = streamUrl;

        // Reset state
        elements.trimStatusText.style.display = 'none';
        elements.btnConfirmTrim.disabled = true;

        elements.trimModal.style.display = 'flex';

        elements.trimVideoPlayer.onloadedmetadata = function () {
            state.trimState.duration = elements.trimVideoPlayer.duration;
            state.trimState.start = 0;
            state.trimState.end = state.trimState.duration;
            updateTrimUI();
            elements.btnConfirmTrim.disabled = false;
        };

        elements.trimVideoPlayer.ontimeupdate = function () {
            if (state.trimState.duration > 0) {
                const pct = (elements.trimVideoPlayer.currentTime / state.trimState.duration) * 100;
                elements.trimProgress.style.width = pct + '%';
            }
        };
    }

    function closeTrimModal() {
        if (elements.trimModal) {
            elements.trimModal.style.display = 'none';
        }
        if (elements.trimVideoPlayer) {
            elements.trimVideoPlayer.pause();
            elements.trimVideoPlayer.removeAttribute('src');
            elements.trimVideoPlayer.load();
        }
        state.trimState.activeId = null;
    }

    if (elements.btnCloseTrimModal) elements.btnCloseTrimModal.addEventListener('click', closeTrimModal);
    if (elements.btnCancelTrim) elements.btnCancelTrim.addEventListener('click', closeTrimModal);

    // Timeline logic
    function updateTrimUI() {
        const duration = state.trimState.duration;
        if (!duration) return;

        const start = state.trimState.start;
        const end = state.trimState.end;

        const startPct = Math.max(0, Math.min(100, (start / duration) * 100));
        const endPct = Math.max(0, Math.min(100, (end / duration) * 100));

        elements.trimHandleStart.style.left = startPct + '%';
        elements.trimHandleEnd.style.left = endPct + '%';

        elements.trimSelection.style.left = startPct + '%';
        elements.trimSelection.style.width = (endPct - startPct) + '%';

        elements.trimTooltipStart.textContent = formatTimeCode(start);
        elements.trimTooltipEnd.textContent = formatTimeCode(end);

        elements.trimInputStart.value = formatTimeCode(start);
        elements.trimInputEnd.value = formatTimeCode(end);
    }

    function handleTimelineInteraction(e) {
        if (!state.trimState.duration) return;

        const rect = elements.trimTimeline.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        let posX = clientX - rect.left;
        posX = Math.max(0, Math.min(rect.width, posX));

        const time = (posX / rect.width) * state.trimState.duration;

        if (state.trimState.isDragging && state.trimState.activeHandle) {
            if (state.trimState.activeHandle === 'start') {
                if (time < state.trimState.end - 1) { // Min 1 sec duration
                    state.trimState.start = time;
                }
            } else if (state.trimState.activeHandle === 'end') {
                if (time > state.trimState.start + 1) {
                    state.trimState.end = time;
                }
            }
            updateTrimUI();
            elements.trimVideoPlayer.currentTime = state.trimState.activeHandle === 'start' ? state.trimState.start : state.trimState.end;
        }
    }

    if (elements.trimHandleStart) {
        const startHandler = (e) => {
            state.trimState.isDragging = true;
            state.trimState.activeHandle = 'start';
            e.stopPropagation();
        };
        elements.trimHandleStart.addEventListener('mousedown', startHandler);
        elements.trimHandleStart.addEventListener('touchstart', startHandler, { passive: true });
    }

    if (elements.trimHandleEnd) {
        const endHandler = (e) => {
            state.trimState.isDragging = true;
            state.trimState.activeHandle = 'end';
            e.stopPropagation();
        };
        elements.trimHandleEnd.addEventListener('mousedown', endHandler);
        elements.trimHandleEnd.addEventListener('touchstart', endHandler, { passive: true });
    }

    document.addEventListener('mousemove', (e) => {
        if (state.trimState.isDragging) {
            handleTimelineInteraction(e);
        }
    });

    document.addEventListener('touchmove', (e) => {
        if (state.trimState.isDragging) {
            handleTimelineInteraction(e);
            if (e.cancelable) e.preventDefault();
        }
    }, { passive: false });

    const stopDragging = () => {
        state.trimState.isDragging = false;
        state.trimState.activeHandle = null;
    };
    document.addEventListener('mouseup', stopDragging);
    document.addEventListener('touchend', stopDragging);

    if (elements.trimTimeline) elements.trimTimeline.addEventListener('click', (e) => {
        if (!state.trimState.duration) return;
        const rect = elements.trimTimeline.getBoundingClientRect();
        let posX = e.clientX - rect.left;
        const time = (posX / rect.width) * state.trimState.duration;

        elements.trimVideoPlayer.currentTime = time;
    });

    if (elements.btnConfirmTrim) elements.btnConfirmTrim.addEventListener('click', () => {
        if (!state.trimState.activeId) return;

        elements.btnConfirmTrim.disabled = true;
        elements.trimStatusText.style.display = 'inline';

        socket.emit('trim_video', {
            download_id: state.trimState.activeId,
            start_time: parseFloat(state.trimState.start.toFixed(2)),
            end_time: parseFloat(state.trimState.end.toFixed(2))
        });

        closeTrimModal();
    });



    // --- Users Modal (admin only) ---
    if (elements.btnUsers) {
        elements.btnUsers.addEventListener('click', () => {
            elements.usersModal.style.display = 'flex';
            loadUsers();
        });
    }

    if (elements.btnCloseModal) {
        elements.btnCloseModal.addEventListener('click', () => {
            elements.usersModal.style.display = 'none';
        });
    }

    if (elements.usersModal) {
        elements.usersModal.addEventListener('click', (e) => {
            if (e.target === elements.usersModal) {
                elements.usersModal.style.display = 'none';
            }
        });
    }

    if (elements.createUserForm) {
        elements.createUserForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const username = document.getElementById('newUsername').value.trim();
            const password = document.getElementById('newPassword').value;
            const isAdmin = document.getElementById('newIsAdmin').checked;

            if (!username || !password) return;

            try {
                const response = await fetch('/api/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, is_admin: isAdmin })
                });

                const data = await response.json();

                if (response.ok) {
                    showFormMessage(data.message, 'success');
                    document.getElementById('newUsername').value = '';
                    document.getElementById('newPassword').value = '';
                    document.getElementById('newIsAdmin').checked = false;
                    loadUsers();
                } else {
                    showFormMessage(data.error, 'error');
                }
            } catch (err) {
                showFormMessage('Error de conexión', 'error');
            }
        });
    }

    async function loadUsers() {
        if (!elements.usersList) return;
        elements.usersList.innerHTML = '<div class="loading-users"><div class="spinner small"></div><span>Cargando usuarios...</span></div>';

        try {
            const response = await fetch('/api/users');
            const users = await response.json();

            elements.usersList.innerHTML = '';

            users.forEach(user => {
                const item = document.createElement('div');
                item.className = 'user-item-card';

                const initials = user.username.charAt(0).toUpperCase();
                const roleBadge = user.is_admin
                    ? '<span class="badge badge-admin">Admin</span>'
                    : '<span class="badge badge-user">Usuario</span>';

                const queueVal = user.is_admin ? '∞' : (user.max_queue_size || 5);
                const quotaVal = user.max_quota_gb || 50;

                item.innerHTML = `
                    <div class="user-item">
                        <div class="user-info">
                            <div class="user-avatar">${initials}</div>
                            <div class="user-details">
                                <div class="user-name">${escapeHtml(user.username)}</div>
                                <div class="user-role">${roleBadge}</div>
                            </div>
                        </div>
                        <button class="delete-user-btn" data-user-id="${user.id}" title="Eliminar usuario">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    ${!user.is_admin ? `
                    <div class="user-settings">
                        <div class="user-setting-field">
                            <label><i class="fas fa-layer-group"></i> Max cola</label>
                            <input type="number" min="1" max="100" value="${queueVal}" class="user-setting-input queue-size-input" data-user-id="${user.id}">
                        </div>
                        <div class="user-setting-field">
                            <label><i class="fas fa-hdd"></i> Cuota (GB)</label>
                            <input type="number" min="1" max="10000" step="0.1" value="${quotaVal}" class="user-setting-input quota-input" data-user-id="${user.id}">
                        </div>
                        <button class="user-setting-save" data-user-id="${user.id}" title="Guardar cambios">
                            <i class="fas fa-check"></i>
                        </button>
                    </div>
                    ` : ''}
                `;

                const deleteBtn = item.querySelector('.delete-user-btn');
                deleteBtn.addEventListener('click', () => deleteUser(user.id, user.username));

                const saveBtn = item.querySelector('.user-setting-save');
                if (saveBtn) {
                    saveBtn.addEventListener('click', async () => {
                        const queueInput = item.querySelector('.queue-size-input');
                        const quotaInput = item.querySelector('.quota-input');
                        try {
                            saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                            const response = await fetch(`/api/users/${user.id}`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    max_queue_size: parseInt(queueInput.value),
                                    max_quota_gb: parseFloat(quotaInput.value)
                                })
                            });
                            const data = await response.json();
                            if (response.ok) {
                                showToast('Configuración guardada', 'success');
                                saveBtn.innerHTML = '<i class="fas fa-check"></i>';
                                saveBtn.classList.add('saved');
                                setTimeout(() => saveBtn.classList.remove('saved'), 1500);
                            } else {
                                showToast(data.error || 'Error', 'error');
                                saveBtn.innerHTML = '<i class="fas fa-check"></i>';
                            }
                        } catch (err) {
                            showToast('Error al guardar', 'error');
                            saveBtn.innerHTML = '<i class="fas fa-check"></i>';
                        }
                    });
                }

                elements.usersList.appendChild(item);
            });
        } catch (err) {
            elements.usersList.innerHTML = '<div class="loading-users"><span>Error al cargar usuarios</span></div>';
        }
    }

    async function deleteUser(userId, username) {
        if (!confirm(`¿Estás seguro de eliminar al usuario "${username}"?`)) return;

        try {
            const response = await fetch(`/api/users/${userId}`, { method: 'DELETE' });
            const data = await response.json();

            if (response.ok) {
                showToast(`Usuario "${username}" eliminado`, 'success');
                loadUsers();
            } else {
                showToast(data.error, 'error');
            }
        } catch (err) {
            showToast('Error al eliminar usuario', 'error');
        }
    }

    function showFormMessage(message, type) {
        if (!elements.formMessage) return;
        elements.formMessage.textContent = message;
        elements.formMessage.className = `form-message ${type}`;
        elements.formMessage.style.display = 'block';

        setTimeout(() => {
            elements.formMessage.style.display = 'none';
        }, 4000);
    }

    // --- Download Quota ---
    async function loadQuota() {
        try {
            const response = await fetch('/api/quota');
            if (!response.ok) return;
            const data = await response.json();

            if (data.unlimited) {
                elements.quotaText.textContent = 'Ilimitado';
                elements.navQuota.title = 'Cuota de descarga: Sin limite (Admin)';
                elements.navQuota.classList.remove('quota-low', 'quota-critical');
            } else {
                elements.quotaText.textContent = data.remaining_str;
                const pct = (data.bytes_remaining / data.quota_total) * 100;
                elements.navQuota.title = `Disponible: ${data.remaining_str} de ${data.total_str} (Usado: ${data.used_str})`;
                elements.navQuota.classList.remove('quota-low', 'quota-critical');
                if (pct <= 10) elements.navQuota.classList.add('quota-critical');
                else if (pct <= 30) elements.navQuota.classList.add('quota-low');
            }
        } catch (err) {
            console.error('Error loading quota:', err);
        }
    }

    // --- Download Queue ---
    function renderQueue() {
        const queuedItems = state.queue.filter(q => q.status === 'queued');
        const totalInQueue = state.queue.length;

        // Update nav indicator
        if (elements.navQueueIndicator) {
            if (totalInQueue > 0) {
                elements.navQueueIndicator.style.display = 'flex';
                elements.navQueueCount.textContent = totalInQueue;
            } else {
                elements.navQueueIndicator.style.display = 'none';
            }
        }

        // Show/hide queue section
        if (queuedItems.length === 0) {
            if (elements.queueSection) elements.queueSection.style.display = 'none';
            return;
        }

        if (elements.queueSection) elements.queueSection.style.display = 'block';
        if (elements.queueCountBadge) elements.queueCountBadge.textContent = queuedItems.length;

        if (!elements.queueList) return;

        // Track existing items for animation
        const existingIds = new Set(
            Array.from(elements.queueList.querySelectorAll('.queue-item')).map(el => el.dataset.queueId)
        );

        elements.queueList.innerHTML = '';

        queuedItems.forEach((item, index) => {
            const el = document.createElement('div');
            el.className = 'queue-item';
            el.dataset.queueId = item.queue_id;
            if (!existingIds.has(item.queue_id)) {
                el.classList.add('queue-item-enter');
            }

            const thumbSrc = item.thumbnail || '';
            const thumbHtml = thumbSrc
                ? `<img src="${escapeHtml(thumbSrc)}" alt="" class="queue-item-thumb">`
                : `<div class="queue-item-thumb queue-item-thumb-placeholder"><i class="fas fa-video"></i></div>`;

            el.innerHTML = `
                <div class="queue-item-position">${index + 1}</div>
                ${thumbHtml}
                <div class="queue-item-info">
                    <div class="queue-item-title">${escapeHtml(item.title || 'Sin título')}</div>
                    <div class="queue-item-quality">${escapeHtml(item.quality || '')}</div>
                </div>
                <button class="queue-item-cancel" title="Quitar de la cola">
                    <i class="fas fa-times"></i>
                </button>
            `;

            el.querySelector('.queue-item-cancel').addEventListener('click', () => {
                el.classList.add('queue-item-exit');
                el.addEventListener('animationend', () => {
                    socket.emit('cancel_download', { queue_id: item.queue_id });
                }, { once: true });
            });

            elements.queueList.appendChild(el);
        });
    }

    if (elements.btnClearQueue) {
        elements.btnClearQueue.addEventListener('click', () => {
            socket.emit('clear_queue');
        });
    }

    // --- Utility Functions ---
    function hideDynamicSections() {
        elements.statusContainer.style.display = 'none';
        elements.videoSection.style.display = 'none';
        // Don't hide progress section if a download is active
        if (!state.isDownloading) {
            elements.progressSection.style.display = 'none';
        }
        elements.completeSection.style.display = 'none';
        // Note: recentSection and queueSection are NOT hidden here - they stay visible
    }

    function showStatus(message) {
        elements.statusContainer.style.display = 'block';
        elements.statusMessage.textContent = message;
        elements.statusIcon.innerHTML = '<div class="spinner"></div>';
    }

    function hideStatus() {
        elements.statusContainer.style.display = 'none';
    }

    async function createPublicLink(downloadId, btn) {
        const origIcon = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        btn.disabled = true;
        try {
            const response = await fetch(`/api/share-link/${downloadId}`, { method: 'POST' });
            const data = await response.json();
            if (response.ok && data.url) {
                try {
                    await navigator.clipboard.writeText(data.url);
                    showToast('Enlace publico copiado al portapapeles', 'success');
                } catch (clipErr) {
                    // Fallback: show the URL in a toast so user can copy it
                    showToast('Enlace: ' + data.url, 'success');
                }
                btn.innerHTML = '<i class="fas fa-check"></i>';
                btn.style.color = '#22c55e';
                setTimeout(() => {
                    btn.innerHTML = origIcon;
                    btn.style.color = '';
                    btn.disabled = false;
                }, 2000);
                return;
            } else {
                showToast(data.error || 'Error al crear enlace', 'error');
            }
        } catch (err) {
            console.error('Public link error:', err);
            showToast('Error al crear enlace publico', 'error');
        }
        btn.innerHTML = origIcon;
        btn.disabled = false;
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        let icon = 'fa-info-circle';
        if (type === 'success') icon = 'fa-check-circle';
        if (type === 'error') icon = 'fa-exclamation-circle';

        toast.innerHTML = `<i class="fas ${icon}"></i><span>${escapeHtml(message)}</span>`;
        elements.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    function formatNumber(num) {
        if (!num) return '0';
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // --- Navbar scroll effect ---
    window.addEventListener('scroll', () => {
        const navbar = document.getElementById('navbar');
        if (navbar) {
            navbar.classList.toggle('scrolled', window.scrollY > 20);
        }
    });

    // --- Keyboard shortcut: Ctrl+V to focus URL input ---
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'v' && document.activeElement !== elements.urlInput) {
            if (!elements.usersModal || elements.usersModal.style.display === 'none') {
                elements.urlInput.focus();
            }
        }
    });

    // --- Initialize ---
    // Handle Share Target: detect shared URL from query params
    const _urlParams = new URLSearchParams(window.location.search);
    const _sharedUrl = _urlParams.get('shared_url');
    if (_sharedUrl) {
        elements.urlInput.value = _sharedUrl;
        // Clean URL bar to remove query params
        window.history.replaceState({}, '', '/');
        // Auto-analyze after socket connects
        if (socket.connected) {
            setTimeout(analyzeUrl, 300);
        } else {
            socket.once('connect', () => setTimeout(analyzeUrl, 300));
        }
    } else {
        // Auto-focus URL input on load (only if not auto-analyzing)
        setTimeout(() => {
            if (elements.urlInput) elements.urlInput.focus();
        }, 500);
    }

    // Collection modal event listeners
    const btnCloseCollectionModal = document.getElementById('btnCloseCollectionModal');
    const btnSaveCollection = document.getElementById('btnSaveCollection');
    const btnDeleteCollection = document.getElementById('btnDeleteCollection');
    const collectionModal = document.getElementById('collectionModal');
    const colorPicker = document.getElementById('colorPicker');

    if (btnCloseCollectionModal) btnCloseCollectionModal.addEventListener('click', closeCollectionModal);
    if (btnSaveCollection) btnSaveCollection.addEventListener('click', saveCollection);
    if (btnDeleteCollection) btnDeleteCollection.addEventListener('click', () => deleteCollection(state.editingCollectionId));
    if (collectionModal) collectionModal.addEventListener('click', (e) => { if (e.target === collectionModal) closeCollectionModal(); });
    if (colorPicker) colorPicker.addEventListener('click', (e) => {
        const swatch = e.target.closest('.color-swatch');
        if (!swatch) return;
        colorPicker.querySelectorAll('.color-swatch').forEach(s => { s.classList.remove('active'); s.style.borderColor = 'transparent'; });
        swatch.classList.add('active');
        swatch.style.borderColor = 'white';
    });
    // Enter key in collection name input
    const collectionNameInput = document.getElementById('collectionNameInput');
    if (collectionNameInput) collectionNameInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') saveCollection(); });

    // Load recent downloads, saved downloads, collections, and quota on page load
    loadCollections();
    loadRecentDownloads();
    loadSavedDownloads();
    loadQuota();

    // Refresh recent downloads and saved downloads every 30 seconds, quota every 30 seconds
    state.recentTimer = setInterval(() => {
        loadRecentDownloads();
        loadSavedDownloads();
    }, 30000);
    setInterval(loadQuota, 30000);

})();
