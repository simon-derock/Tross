"""
app/playground.py
─────────────────
Modern Dark-Mode Web Playground for Tross.

Single-file, ultra-responsive HTML5 / Tailwind CSS single-page application
served at root (`/`) for interactive testing, visual profile card previews,
and raw structured JSON inspection.
"""

from __future__ import annotations


def get_playground_html() -> str:
    """Return the complete HTML/JS/CSS string for the Web Playground SPA."""
    return """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tross — LinkedIn Reverse Profile API Playground</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace'],
                    },
                    colors: {
                        brand: {
                            50: '#f0fdf4',
                            500: '#10b981',
                            600: '#059669',
                            DEFAULT: '#10b981',
                        }
                    }
                }
            }
        }
    </script>
    <style>
        .glass-panel {
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .code-scroll::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        .code-scroll::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 3px;
        }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans antialiased selection:bg-emerald-500 selection:text-black">
    
    <!-- Background Glow -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div class="absolute -top-40 left-1/2 -translate-x-1/2 w-[700px] h-[500px] bg-emerald-600/15 rounded-full blur-[140px]"></div>
        <div class="absolute top-1/3 -right-40 w-[500px] h-[400px] bg-cyan-600/10 rounded-full blur-[120px]"></div>
    </div>

    <div class="relative z-10 max-w-6xl mx-auto px-4 py-8 sm:py-12">
        
        <!-- Header -->
        <header class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-8 border-b border-slate-800/80">
            <div>
                <div class="flex items-center gap-3">
                    <span class="text-2xl font-black tracking-tight text-white flex items-center gap-2">
                        <span class="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center text-slate-950 font-black text-lg shadow-lg shadow-emerald-500/20">⚡</span>
                        TROSS
                    </span>
                    <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800/60 flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                        Voyager Reverse Engine
                    </span>
                </div>
                <p class="text-xs sm:text-sm text-slate-400 mt-1">High-precision, pure reverse-engineered LinkedIn Profile Extraction API</p>
            </div>
            <div class="flex items-center gap-3">
                <a href="/docs" target="_blank" class="px-3.5 py-1.5 text-xs font-medium rounded-lg glass-panel hover:bg-slate-800 text-slate-300 hover:text-white transition flex items-center gap-1.5">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
                    Interactive Docs (/docs)
                </a>
                <a href="https://github.com/simon-derock/Tross" target="_blank" class="px-3.5 py-1.5 text-xs font-medium rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 transition flex items-center gap-1.5">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
                    GitHub Repo
                </a>
            </div>
        </header>

        <!-- Main Input Form -->
        <div class="mt-8 glass-panel rounded-2xl p-6 shadow-2xl">
            <form id="scrape-form" onsubmit="handleScrape(event)" class="space-y-4">
                <div class="flex flex-col sm:flex-row gap-3">
                    <div class="relative flex-1">
                        <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/></svg>
                        </div>
                        <input type="text" id="url-input" required placeholder="https://www.linkedin.com/in/satyanadella/ or satyanadella" value="https://www.linkedin.com/in/satyanadella/" class="w-full pl-11 pr-4 py-3 bg-slate-900/90 rounded-xl border border-slate-700/80 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 text-sm text-white placeholder-slate-500 outline-none transition">
                    </div>
                    <button type="submit" id="submit-btn" class="px-6 py-3 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm rounded-xl transition shadow-lg shadow-emerald-500/25 flex items-center justify-center gap-2 whitespace-nowrap">
                        <span id="btn-text">⚡ Scrape Profile</span>
                        <svg id="btn-spinner" class="hidden w-4 h-4 animate-spin text-slate-950" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                    </button>
                </div>

                <!-- Quick Samples -->
                <div class="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-400">
                    <span class="font-medium text-slate-500">Quick Samples:</span>
                    <button type="button" onclick="fillSample('satyanadella')" class="px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition">Satya Nadella</button>
                    <button type="button" onclick="fillSample('williamhgates')" class="px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition">Bill Gates</button>
                    <button type="button" onclick="fillSample('reidhoffman')" class="px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition">Reid Hoffman</button>
                    <button type="button" onclick="fillSample('sama')" class="px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition">Sam Altman</button>
                    <button type="button" onclick="fillSample('yann-lecun')" class="px-2.5 py-1 rounded-md bg-slate-800/80 hover:bg-slate-700 text-slate-300 transition">Yann LeCun</button>
                </div>

                <!-- Optional API Key accordion -->
                <details class="text-xs text-slate-400 pt-2">
                    <summary class="cursor-pointer hover:text-slate-300 transition select-none flex items-center gap-1">
                        <span>⚙️ Advanced: Custom Headers & API Key</span>
                    </summary>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 pt-3 border-t border-slate-800/60">
                        <input type="text" id="api-key-input" placeholder="X-API-Key (Optional if open)" class="px-3 py-2 bg-slate-900 rounded-lg border border-slate-800 text-xs text-slate-200 outline-none focus:border-emerald-500">
                        <input type="text" id="custom-li-at" placeholder="X-Li-At Override (Optional)" class="px-3 py-2 bg-slate-900 rounded-lg border border-slate-800 text-xs text-slate-200 outline-none focus:border-emerald-500">
                    </div>
                </details>
            </form>
        </div>

        <!-- Notification Banner -->
        <div id="toast" class="hidden mt-4 p-4 rounded-xl text-xs font-medium flex items-center justify-between transition-all">
            <span id="toast-msg"></span>
            <button onclick="hideToast()" class="opacity-70 hover:opacity-100">&times;</button>
        </div>

        <!-- Results Container -->
        <div id="results-area" class="hidden mt-8 space-y-6">
            <!-- Tabs & Metrics -->
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                <div class="flex items-center gap-2">
                    <button onclick="switchTab('visual')" id="tab-visual-btn" class="px-4 py-1.5 text-xs font-bold rounded-lg bg-emerald-500 text-slate-950 transition">Visual Profile Card</button>
                    <button onclick="switchTab('json')" id="tab-json-btn" class="px-4 py-1.5 text-xs font-bold rounded-lg glass-panel hover:bg-slate-800 text-slate-400 hover:text-white transition">Raw Structured JSON</button>
                </div>
                <div class="flex items-center gap-3 text-xs text-slate-400">
                    <span id="metric-time" class="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 font-mono text-emerald-400">⏱️ -- ms</span>
                    <span id="metric-trace" class="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 font-mono text-slate-500 truncate max-w-[140px]">🆔 --</span>
                    <button onclick="copyJson()" class="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded-md transition flex items-center gap-1">
                        <span id="copy-btn-text">📋 Copy JSON</span>
                    </button>
                </div>
            </div>

            <!-- Tab 1: Visual Card -->
            <div id="tab-visual" class="glass-panel rounded-2xl overflow-hidden shadow-2xl">
                <div id="card-banner" class="h-36 bg-gradient-to-r from-emerald-900/40 via-cyan-900/30 to-slate-900 bg-cover bg-center"></div>
                <div class="p-6 sm:p-8 -mt-16">
                    <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                        <div class="flex items-end gap-4">
                            <img id="card-avatar" class="w-24 h-24 sm:w-28 sm:h-28 rounded-2xl border-4 border-slate-950 bg-slate-900 object-cover shadow-2xl" src="" alt="Avatar" onerror="this.src='https://static.licdn.com/aero-v1/sc/h/1c5u578iilxfxfvdgahzah611'">
                            <div class="mb-1">
                                <h2 id="card-name" class="text-2xl sm:text-3xl font-extrabold text-white"></h2>
                                <p id="card-headline" class="text-xs sm:text-sm text-emerald-400 font-medium mt-0.5 line-clamp-2"></p>
                            </div>
                        </div>
                        <div id="card-badges" class="flex flex-wrap gap-2 text-xs"></div>
                    </div>

                    <p id="card-about" class="text-xs sm:text-sm text-slate-300 mt-6 leading-relaxed bg-slate-900/50 p-4 rounded-xl border border-slate-800/60"></p>

                    <!-- Experience Timeline -->
                    <div class="mt-8">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">Work Experience</h3>
                        <div id="card-experience" class="space-y-4 border-l-2 border-slate-800 ml-3 pl-5"></div>
                    </div>

                    <!-- Education Section -->
                    <div class="mt-8">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">Education</h3>
                        <div id="card-education" class="grid grid-cols-1 sm:grid-cols-2 gap-3"></div>
                    </div>

                    <!-- Skills Pills -->
                    <div class="mt-8">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500 mb-4">Skills</h3>
                        <div id="card-skills" class="flex flex-wrap gap-2"></div>
                    </div>
                </div>
            </div>

            <!-- Tab 2: JSON Viewer -->
            <div id="tab-json" class="hidden glass-panel rounded-2xl p-4 sm:p-6 overflow-hidden">
                <pre id="json-output" class="code-scroll font-mono text-xs sm:text-sm text-emerald-300 overflow-x-auto max-h-[600px] leading-relaxed select-all"></pre>
            </div>
        </div>

    </div>

    <script>
        let currentPayload = null;

        function fillSample(slug) {
            document.getElementById('url-input').value = `https://www.linkedin.com/in/${slug}/`;
            handleScrape(new Event('submit'));
        }

        function switchTab(tab) {
            const visualTab = document.getElementById('tab-visual');
            const jsonTab = document.getElementById('tab-json');
            const visualBtn = document.getElementById('tab-visual-btn');
            const jsonBtn = document.getElementById('tab-json-btn');

            if (tab === 'visual') {
                visualTab.classList.remove('hidden');
                jsonTab.classList.add('hidden');
                visualBtn.className = 'px-4 py-1.5 text-xs font-bold rounded-lg bg-emerald-500 text-slate-950 transition';
                jsonBtn.className = 'px-4 py-1.5 text-xs font-bold rounded-lg glass-panel hover:bg-slate-800 text-slate-400 hover:text-white transition';
            } else {
                visualTab.classList.add('hidden');
                jsonTab.classList.remove('hidden');
                jsonBtn.className = 'px-4 py-1.5 text-xs font-bold rounded-lg bg-emerald-500 text-slate-950 transition';
                visualBtn.className = 'px-4 py-1.5 text-xs font-bold rounded-lg glass-panel hover:bg-slate-800 text-slate-400 hover:text-white transition';
            }
        }

        function showToast(msg, isError = false) {
            const toast = document.getElementById('toast');
            const toastMsg = document.getElementById('toast-msg');
            toastMsg.innerText = msg;
            toast.className = `mt-4 p-4 rounded-xl text-xs font-medium flex items-center justify-between transition-all ${isError ? 'bg-red-950/80 border border-red-800 text-red-300' : 'bg-emerald-950/80 border border-emerald-800 text-emerald-300'}`;
            toast.classList.remove('hidden');
        }

        function hideToast() {
            document.getElementById('toast').classList.add('hidden');
        }

        function copyJson() {
            if (!currentPayload) return;
            navigator.clipboard.writeText(JSON.stringify(currentPayload, null, 2)).then(() => {
                const btnText = document.getElementById('copy-btn-text');
                btnText.innerText = '✅ Copied!';
                setTimeout(() => { btnText.innerText = '📋 Copy JSON'; }, 2000);
            });
        }

        async function handleScrape(e) {
            if (e) e.preventDefault();
            hideToast();

            const urlInput = document.getElementById('url-input').value.trim();
            const apiKey = document.getElementById('api-key-input').value.trim();
            const customLiAt = document.getElementById('custom-li-at').value.trim();

            if (!urlInput) {
                showToast('Please enter a LinkedIn profile URL or slug.', true);
                return;
            }

            const btnText = document.getElementById('btn-text');
            const btnSpinner = document.getElementById('btn-spinner');
            const submitBtn = document.getElementById('submit-btn');

            btnText.innerText = 'Extracting...';
            btnSpinner.classList.remove('hidden');
            submitBtn.disabled = true;

            const startTime = performance.now();

            try {
                const headers = { 'Content-Type': 'application/json' };
                if (apiKey) headers['X-API-Key'] = apiKey;
                if (customLiAt) headers['X-Li-At'] = customLiAt;

                const response = await fetch('/api/scrape', {
                    method: 'POST',
                    headers: headers,
                    body: JSON.stringify({ url: urlInput })
                });

                const duration = Math.round(performance.now() - startTime);
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.detail || `Server returned status ${response.status}`);
                }

                currentPayload = data;
                renderResults(data, duration);
                showToast(`Profile for '${data.full_name || data.profile_id}' extracted successfully in ${duration}ms!`);

            } catch (err) {
                showToast(err.message, true);
            } finally {
                btnText.innerText = '⚡ Scrape Profile';
                btnSpinner.classList.add('hidden');
                submitBtn.disabled = false;
            }
        }

        function renderResults(data, duration) {
            document.getElementById('metric-time').innerText = `⏱️ ${duration} ms`;
            document.getElementById('metric-trace').innerText = `🆔 ${data.trace_id ? data.trace_id.slice(0, 10) : 'local'}`;

            // Render Tab 1 (Visual)
            document.getElementById('card-name').innerText = data.full_name || data.profile_id || 'LinkedIn Member';
            document.getElementById('card-headline').innerText = data.headline || 'No headline available';
            
            const avatar = document.getElementById('card-avatar');
            avatar.src = data.profile_image_url || 'https://static.licdn.com/aero-v1/sc/h/1c5u578iilxfxfvdgahzah611';

            const banner = document.getElementById('card-banner');
            if (data.background_image_url) {
                banner.style.backgroundImage = `url('${data.background_image_url}')`;
            } else {
                banner.style.backgroundImage = 'none';
            }

            // Badges
            const badgesDiv = document.getElementById('card-badges');
            badgesDiv.innerHTML = '';
            if (data.location) {
                badgesDiv.innerHTML += `<span class="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300">📍 ${data.location}</span>`;
            }
            if (data.industry) {
                badgesDiv.innerHTML += `<span class="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300">🏢 ${data.industry}</span>`;
            }
            if (data.followers) {
                badgesDiv.innerHTML += `<span class="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-emerald-400 font-semibold">👥 ${Number(data.followers).toLocaleString()} followers</span>`;
            }

            // About
            const aboutEl = document.getElementById('card-about');
            if (data.about) {
                aboutEl.innerText = data.about;
                aboutEl.classList.remove('hidden');
            } else {
                aboutEl.classList.add('hidden');
            }

            // Experience
            const expDiv = document.getElementById('card-experience');
            expDiv.innerHTML = '';
            if (data.experience && data.experience.length > 0) {
                data.experience.forEach(exp => {
                    const start = exp.date_range ? exp.date_range.start_date || '' : '';
                    const end = exp.date_range ? exp.date_range.end_date || 'Present' : '';
                    const dateStr = (start || end) ? `${start} - ${end}` : '';
                    expDiv.innerHTML += `
                        <div class="relative group">
                            <div class="absolute -left-[27px] top-1.5 w-3 h-3 rounded-full bg-emerald-500 ring-4 ring-slate-950"></div>
                            <h4 class="text-sm font-bold text-white">${exp.title || 'Role'}</h4>
                            <p class="text-xs text-emerald-400 font-medium">${exp.company || 'Company'}</p>
                            ${dateStr ? `<p class="text-xs text-slate-500 mt-0.5">${dateStr}</p>` : ''}
                            ${exp.description ? `<p class="text-xs text-slate-400 mt-1 line-clamp-3">${exp.description}</p>` : ''}
                        </div>
                    `;
                });
            } else {
                expDiv.innerHTML = '<p class="text-xs text-slate-500 italic">No experience history listed.</p>';
            }

            // Education
            const eduDiv = document.getElementById('card-education');
            eduDiv.innerHTML = '';
            if (data.education && data.education.length > 0) {
                data.education.forEach(edu => {
                    eduDiv.innerHTML += `
                        <div class="p-3 bg-slate-900/60 rounded-xl border border-slate-800/80">
                            <h4 class="text-xs font-bold text-white">${edu.school || 'School'}</h4>
                            <p class="text-xs text-slate-400 mt-0.5">${edu.degree || ''} ${edu.field_of_study ? '• ' + edu.field_of_study : ''}</p>
                        </div>
                    `;
                });
            } else {
                eduDiv.innerHTML = '<p class="text-xs text-slate-500 italic col-span-2">No education listed.</p>';
            }

            // Skills
            const skillsDiv = document.getElementById('card-skills');
            skillsDiv.innerHTML = '';
            if (data.skills && data.skills.length > 0) {
                data.skills.forEach(skill => {
                    skillsDiv.innerHTML += `<span class="px-2.5 py-1 bg-slate-900 rounded-lg text-xs font-medium text-slate-300 border border-slate-800">${skill}</span>`;
                });
            } else {
                skillsDiv.innerHTML = '<p class="text-xs text-slate-500 italic">No skills listed.</p>';
            }

            // Render Tab 2 (JSON)
            document.getElementById('json-output').innerText = JSON.stringify(data, null, 2);

            // Show results area
            document.getElementById('results-area').classList.remove('hidden');
        }
    </script>
</body>
</html>"""
