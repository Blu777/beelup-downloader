/**
 * Chala Cup Club - Video & Clips Gallery Widget
 * 
 * Embeddable Vanilla JS widget with glassmorphism UI, camera switcher and highlights list.
 * Connects directly to Beelup Downloader public CORS API (/api/public/catalog).
 */

(function() {
    const STYLES = `
        .chala-gallery-root {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            color: #f1f5f9;
            background: #090d16;
            min-height: 100vh;
            padding: 2rem;
            box-sizing: border-box;
        }
        .chala-header {
            text-align: center;
            margin-bottom: 3rem;
        }
        .chala-title {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0 0 0.5rem 0;
            letter-spacing: -0.025em;
        }
        .chala-subtitle {
            color: #94a3b8;
            font-size: 1.1rem;
            margin: 0;
        }
        .chala-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 1.5rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        .chala-card {
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            display: flex;
            flex-direction: column;
        }
        .chala-card:hover {
            transform: translateY(-6px);
            border-color: rgba(16, 185, 129, 0.4);
            box-shadow: 0 20px 30px -10px rgba(0, 0, 0, 0.5), 0 0 20px rgba(16, 185, 129, 0.15);
        }
        .chala-card-thumb {
            height: 180px;
            background: #1e293b;
            position: relative;
            background-size: cover;
            background-position: center;
        }
        .chala-card-badge {
            position: absolute;
            top: 12px;
            right: 12px;
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(8px);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }
        .chala-card-content {
            padding: 1.25rem;
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .chala-card-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: #f8fafc;
            margin: 0 0 0.5rem 0;
            line-height: 1.4;
        }
        .chala-card-meta {
            display: flex;
            gap: 1rem;
            font-size: 0.85rem;
            color: #64748b;
        }
        .chala-card-stats {
            margin-top: 1rem;
            padding-top: 0.75rem;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            color: #10b981;
            font-weight: 600;
        }

        /* Modal */
        .chala-modal-backdrop {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(3, 7, 18, 0.85);
            backdrop-filter: blur(8px);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.25s ease;
            padding: 1rem;
        }
        .chala-modal-backdrop.active {
            opacity: 1;
            pointer-events: auto;
        }
        .chala-modal {
            background: #0f172a;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            width: 100%;
            max-width: 1100px;
            max-height: 90vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8);
            animation: modalPop 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes modalPop {
            0% { transform: scale(0.95); opacity: 0; }
            100% { transform: scale(1); opacity: 1; }
        }
        .chala-modal-header {
            padding: 1rem 1.5rem;
            background: #1e293b;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .chala-modal-close {
            background: transparent;
            border: none;
            color: #94a3b8;
            font-size: 1.5rem;
            cursor: pointer;
            transition: color 0.2s;
        }
        .chala-modal-close:hover { color: #f1f5f9; }
        .chala-modal-body {
            display: grid;
            grid-template-columns: 2fr 1fr;
            flex: 1;
            overflow: hidden;
        }
        @media (max-width: 850px) {
            .chala-modal-body { grid-template-columns: 1fr; overflow-y: auto; }
        }
        .chala-player-area {
            background: #000;
            display: flex;
            flex-direction: column;
        }
        .chala-video-el {
            width: 100%;
            max-height: 500px;
            background: #050505;
        }
        .chala-cam-tabs {
            padding: 0.75rem 1rem;
            background: #0f172a;
            display: flex;
            gap: 0.5rem;
            overflow-x: auto;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }
        .chala-cam-tab {
            background: #1e293b;
            border: 1px solid rgba(255, 255, 255, 0.05);
            color: #cbd5e1;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 0.8rem;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.2s;
        }
        .chala-cam-tab.active {
            background: #10b981;
            color: #022c22;
            font-weight: 700;
            border-color: #34d399;
        }
        .chala-clips-sidebar {
            background: #0f172a;
            border-left: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            max-height: 600px;
        }
        .chala-clips-title {
            padding: 1rem;
            font-size: 0.9rem;
            font-weight: 700;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            margin: 0;
            background: #131d33;
        }
        .chala-clip-item {
            padding: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .chala-clip-item:hover { background: rgba(255, 255, 255, 0.03); }
        .chala-clip-item.active { background: rgba(16, 185, 129, 0.1); border-left: 3px solid #10b981; }
        .chala-clip-icon { font-size: 1.25rem; }
        .chala-clip-info h4 { margin: 0 0 4px 0; font-size: 0.9rem; color: #e2e8f0; font-weight: 600; }
        .chala-clip-info span { font-size: 0.75rem; color: #64748b; }
    `;

    class ChalaVideoGallery {
        constructor(containerEl, beelupBaseUrl) {
            this.container = containerEl;
            this.baseUrl = beelupBaseUrl.replace(/\/$/, '');
            this.catalog = null;
            this.activeMatch = null;
            this.init();
        }

        async fetchApi(endpoint) {
            const targetUrl = `${this.baseUrl}${endpoint}`;
            try {
                const res = await fetch(targetUrl);
                if (res.ok) return await res.json();
                throw new Error("HTTP " + res.status);
            } catch (err) {
                // Si el servidor en producción aún no tiene desplegado el nuevo app.py con cabeceras CORS, usamos proxy /get encapsulado
                const proxyUrl = `https://api.allorigins.win/get?url=${encodeURIComponent(targetUrl)}`;
                const resProxy = await fetch(proxyUrl);
                if (resProxy.ok) {
                    const data = await resProxy.json();
                    if (data && data.contents) {
                        return typeof data.contents === 'string' ? JSON.parse(data.contents) : data.contents;
                    }
                }
                throw err;
            }
        }

        async init() {
            this.injectStyles();
            this.container.innerHTML = `<div style="text-align:center;padding:4rem;color:#64748b">⚡ Cargando videoteca cannabica...</div>`;
            try {
                let catalogData = null;
                try {
                    catalogData = await this.fetchApi("/api/public/catalog");
                } catch (e) {
                    // Fallback automático para la versión activa en beelup.tiagonatale.com
                    const [vidsJson, clipsJson] = await Promise.all([
                        this.fetchApi("/api/videos"),
                        this.fetchApi("/api/clips").catch(() => ({ groups: [] }))
                    ]);

                    const clipsMap = {};
                    (clipsJson.groups || []).forEach(g => {
                        clipsMap[g.match_id] = (g.clips || []).map(c => ({
                            clip_id: c.filename,
                            name: c.name,
                            stream_url: `/api/clips/stream/${c.filename}`,
                            duration_seconds: Math.round((c.end || 0) - (c.start || 0))
                        }));
                    });

                    const matchesList = (vidsJson.matches || []).map(m => ({
                        match_id: m.id,
                        title: m.title,
                        date: m.date,
                        complejo: m.complejo,
                        cancha: m.cancha,
                        cover_url: m.cover_url,
                        full_videos: (m.cameras || []).map(cam => ({
                            cam_id: cam.cam_id,
                            label: cam.label,
                            stream_url: `/api/stream/${cam.filename}`
                        })),
                        clips: clipsMap[m.id] || []
                    }));

                    catalogData = { matches: matchesList };
                }

                this.catalog = catalogData;
                this.renderGrid();
                this.setupModal();
            } catch (err) {
                this.container.innerHTML = `
                    <div style="text-align:center;padding:3rem;background:#1e1b4b;border-radius:12px;color:#fca5a5">
                        ⚠️ No se pudo conectar con el servidor de videos (${this.baseUrl}).<br>
                        <small style="color:#cbd5e1">Detalle del error: ${err.message}</small>
                    </div>`;
            }
        }

        injectStyles() {
            if (document.getElementById('chala-gallery-styles')) return;
            const style = document.createElement('style');
            style.id = 'chala-gallery-styles';
            style.textContent = STYLES;
            document.head.appendChild(style);
        }

        renderGrid() {
            const matches = this.catalog.matches || [];
            if (matches.length === 0) {
                this.container.innerHTML = `<div style="text-align:center;padding:4rem;color:#94a3b8">No hay partidos descargados en la biblioteca aún.</div>`;
                return;
            }

            let html = `
                <div class="chala-gallery-root">
                    <div class="chala-header">
                        <h2 class="chala-title">CHALA CUP REPLAYS</h2>
                        <p class="chala-subtitle">Revive los domingos de gloria, patadas y clips falopa</p>
                    </div>
                    <div class="chala-grid">
            `;

            matches.forEach((m, idx) => {
                const cover = m.cover_url || 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=600&q=80';
                const camCount = m.full_videos.length;
                const clipCount = m.clips.length;
                
                html += `
                    <div class="chala-card" data-idx="${idx}">
                        <div class="chala-card-thumb" style="background-image: url('${cover}')">
                            <span class="chala-card-badge">${m.date || 'DOMINGO'}</span>
                        </div>
                        <div class="chala-card-content">
                            <div>
                                <h3 class="chala-card-title">${m.title}</h3>
                                <div class="chala-card-meta">
                                    <span>📍 ${m.complejo || 'MEGAFUTBOL'}</span>
                                    ${m.cancha ? `<span>⚽ ${m.cancha}</span>` : ''}
                                </div>
                            </div>
                            <div class="chala-card-stats">
                                <span>🎥 ${camCount} Cámaras</span>
                                <span>⚡ ${clipCount} Clips</span>
                            </div>
                        </div>
                    </div>
                `;
            });

            html += `</div></div>`;
            this.container.innerHTML = html;

            // Bind click events
            this.container.querySelectorAll('.chala-card').forEach(el => {
                el.addEventListener('click', () => {
                    const idx = el.getAttribute('data-idx');
                    this.openModal(this.catalog.matches[idx]);
                });
            });
        }

        setupModal() {
            if (document.getElementById('chala-video-modal')) return;
            const modalEl = document.createElement('div');
            modalEl.id = 'chala-video-modal';
            modalEl.className = 'chala-modal-backdrop';
            modalEl.innerHTML = `
                <div class="chala-modal">
                    <div class="chala-modal-header">
                        <h3 id="chala-modal-title" style="margin:0;font-size:1.1rem;color:#f8fafc">Partido</h3>
                        <button class="chala-modal-close">&times;</button>
                    </div>
                    <div class="chala-modal-body">
                        <div class="chala-player-area">
                            <video id="chala-main-player" class="chala-video-el" controls playsinline></video>
                            <div id="chala-cam-tabs" class="chala-cam-tabs"></div>
                        </div>
                        <div id="chala-clips-sidebar" class="chala-clips-sidebar">
                            <h4 class="chala-clips-title">⚡ Jugadas Destacadas</h4>
                            <div id="chala-clips-list"></div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modalEl);

            modalEl.querySelector('.chala-modal-close').addEventListener('click', () => this.closeModal());
            modalEl.addEventListener('click', (e) => {
                if (e.target === modalEl) this.closeModal();
            });
        }

        openModal(match) {
            this.activeMatch = match;
            const modal = document.getElementById('chala-video-modal');
            const player = document.getElementById('chala-main-player');
            const title = document.getElementById('chala-modal-title');
            const camTabs = document.getElementById('chala-cam-tabs');
            const clipsList = document.getElementById('chala-clips-list');

            title.textContent = `${match.title} (${match.date})`;

            // Render camera tabs
            camTabs.innerHTML = match.full_videos.map((cam, i) => `
                <button class="chala-cam-tab ${i === 0 ? 'active' : ''}" data-url="${this.baseUrl}${cam.stream_url}">
                    🎥 ${cam.label}
                </button>
            `).join('');

            // Render clips
            if (match.clips.length === 0) {
                clipsList.innerHTML = `<div style="padding:2rem 1rem;color:#64748b;font-size:0.85rem;text-align:center">No hay clips cortados para este partido.</div>`;
            } else {
                clipsList.innerHTML = match.clips.map((clip, i) => `
                    <div class="chala-clip-item" data-url="${this.baseUrl}${clip.stream_url}">
                        <span class="chala-clip-icon">⚡</span>
                        <div class="chala-clip-info">
                            <h4>${clip.name}</h4>
                            <span>⏱️ ${clip.duration_seconds}s</span>
                        </div>
                    </div>
                `).join('');
            }

            // Bind camera click
            camTabs.querySelectorAll('.chala-cam-tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    camTabs.querySelectorAll('.chala-cam-tab').forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                    player.src = tab.getAttribute('data-url');
                    player.play();
                });
            });

            // Bind clip click
            clipsList.querySelectorAll('.chala-clip-item').forEach(item => {
                item.addEventListener('click', () => {
                    clipsList.querySelectorAll('.chala-clip-item').forEach(c => c.classList.remove('active'));
                    item.classList.add('active');
                    player.src = item.getAttribute('data-url');
                    player.play();
                });
            });

            // Load first video or first clip
            if (match.full_videos.length > 0) {
                player.src = `${this.baseUrl}${match.full_videos[0].stream_url}`;
            } else if (match.clips.length > 0) {
                player.src = `${this.baseUrl}${match.clips[0].stream_url}`;
            }

            modal.classList.add('active');
        }

        closeModal() {
            const modal = document.getElementById('chala-video-modal');
            const player = document.getElementById('chala-main-player');
            player.pause();
            player.src = '';
            modal.classList.remove('active');
        }
    }

    // Expose globally
    window.ChalaVideoGallery = ChalaVideoGallery;
})();
