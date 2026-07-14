/* SiteGen AI — Builder Page JavaScript */

let currentProjectId = null;
let currentWebsiteId = null;

document.addEventListener('DOMContentLoaded', () => {
    const builderEl = document.getElementById('builder-app');
    if (builderEl) {
        currentProjectId = builderEl.dataset.projectId || null;
        currentWebsiteId = builderEl.dataset.websiteId || null;
    }

    // Tab switching
    document.querySelectorAll('.code-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.code-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.code-panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`panel-${tab.dataset.tab}`).classList.add('active');
        });
    });

    // Device buttons
    document.querySelectorAll('.device-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.device-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const frame = document.getElementById('preview-frame');
            if (frame) {
                frame.className = 'preview-frame';
                if (btn.dataset.device !== 'desktop') frame.classList.add(btn.dataset.device);
            }
        });
    });
});

// ─── API Helper (overrides global, surfaces real errors) ─────────────────────
async function apiCallWithFullError(url, options = {}) {
    const defaults = {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
    };
    const config = { ...defaults, ...options };
    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }

    console.log('[SiteGen] ─── HTTP REQUEST ───────────────────────');
    console.log('[SiteGen] URL:', url);
    console.log('[SiteGen] Method:', config.method || 'GET');
    console.log('[SiteGen] Body:', config.body);
    console.log('[SiteGen] ────────────────────────────────────────');

    const response = await fetch(url, config);

    console.log('[SiteGen] ─── HTTP RESPONSE ──────────────────────');
    console.log('[SiteGen] HTTP Status:', response.status);
    console.log('[SiteGen] Headers:', Object.fromEntries(response.headers.entries()));

    // Read body once as text
    const rawText = await response.text();
    console.log('[SiteGen] Raw Response Length:', rawText.length);
    console.log('[SiteGen] Raw Response (first 1000):', rawText.substring(0, 1000));
    console.log('[SiteGen] ────────────────────────────────────────');

    let data;
    try {
        data = JSON.parse(rawText);
        console.log('[SiteGen] Parsed JSON keys:', Object.keys(data));
    } catch (parseErr) {
        console.error('[SiteGen] JSON parse error:', parseErr);
        throw new Error(`Server returned non-JSON (status ${response.status}): ${rawText.substring(0, 300)}`);
    }

    if (!response.ok) {
        // Surface the EXACT error from the server
        const detail = data.detail || JSON.stringify(data);
        console.error('[SiteGen] ❌ API ERROR:', detail);
        throw new Error(detail);
    }

    return data;
}

// ─── Generate website ─────────────────────────────────────────────────────────
async function generateWebsite() {
    const promptEl = document.getElementById('prompt-input');
    const prompt = promptEl ? promptEl.value.trim() : '';

    if (!prompt) {
        showToast('Please describe your website first', 'warning');
        return;
    }

    // ── PRE-REQUEST LOG ──
    console.log('[SiteGen] ═══════════════════════════════════════');
    console.log('[SiteGen] Generate triggered');
    console.log('[SiteGen] Prompt:', prompt);
    console.log('[SiteGen] Prompt length:', prompt.length);
    console.log('[SiteGen] Current Project ID:', currentProjectId);
    console.log('[SiteGen] ═══════════════════════════════════════');

    const generateBtn = document.getElementById('generate-btn');
    if (generateBtn) {
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px;"></div> Generating...';
    }

    const progressSection = document.getElementById('progress-section');
    if (progressSection) {
        progressSection.classList.add('active');
        updateProgress(0);
    }

    const requestBody = { prompt, project_id: currentProjectId };

    try {
        updateProgress(1);
        await new Promise(r => setTimeout(r, 300));
        updateProgress(2);

        const startTime = Date.now();
        const result = await apiCallWithFullError('/api/generate', {
            method: 'POST',
            body: requestBody,
        });
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

        // ── POST-REQUEST LOG ──
        console.log('[SiteGen] ═══════════════════════════════════════');
        console.log('[SiteGen] SUCCESS in', elapsed + 's');
        console.log('[SiteGen] website_type:', result.website_type);
        console.log('[SiteGen] detected_language:', result.detected_language);
        console.log('[SiteGen] fallback_used:', result.fallback_used);
        console.log('[SiteGen] HTML length:', (result.html || '').length);
        console.log('[SiteGen] CSS length:', (result.css || '').length);
        console.log('[SiteGen] JS length:', (result.js || '').length);
        console.log('[SiteGen] HTML first 500 chars:', (result.html || '').substring(0, 500));
        console.log('[SiteGen] ═══════════════════════════════════════');

        updateProgress(3);
        await new Promise(r => setTimeout(r, 200));
        updateProgress(4);

        currentProjectId = result.project_id;
        currentWebsiteId = result.website_id;

        // ── Render preview ──
        let frame = document.getElementById('preview-frame');
        const emptyPreview = document.getElementById('empty-preview');
        if (emptyPreview) emptyPreview.remove();
        if (!frame) {
            frame = document.createElement('iframe');
            frame.id = 'preview-frame';
            frame.className = 'preview-frame';
            const container = document.querySelector('.preview-container');
            if (container) container.appendChild(frame);
        }

        console.log('[SiteGen] Injecting HTML into iframe srcdoc');
        frame.srcdoc = result.html;

        // ── Update code panels ──
        const codeHtml = document.getElementById('code-html');
        const codeCss  = document.getElementById('code-css');
        const codeJs   = document.getElementById('code-js');
        if (codeHtml) codeHtml.textContent = result.html || '';
        if (codeCss)  codeCss.textContent  = result.css  || '';
        if (codeJs)   codeJs.textContent   = result.js   || '';

        // ── Update URL ──
        if (result.project_id) {
            window.history.replaceState({}, '', `/builder/${result.project_id}`);
        }

        // ── User notification ──
        if (result.fallback_used) {
            showToast(
                '⚠️ Gemini API quota exhausted — template fallback was used. ' +
                'Enable billing at console.cloud.google.com/billing then get a new key at aistudio.google.com/app/apikey.',
                'warning'
            );
        } else {
            showToast('✅ Website generated by Gemini AI!', 'success');
        }

    } catch (error) {
        // ── Full error display ──
        console.error('[SiteGen] ═══════════════════════════════════════');
        console.error('[SiteGen] GENERATION FAILED');
        console.error('[SiteGen] Error:', error.message);
        console.error('[SiteGen] Stack:', error.stack);
        console.error('[SiteGen] ═══════════════════════════════════════');

        // Show the exact error in a visible toast
        showToast(error.message || 'Generation failed — check browser console for details', 'error');

    } finally {
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fas fa-magic"></i> Generate';
        }
        if (progressSection) {
            setTimeout(() => progressSection.classList.remove('active'), 2000);
        }
    }
}

function updateProgress(step) {
    const steps = document.querySelectorAll('.step');
    const fill  = document.getElementById('progress-fill');
    steps.forEach((s, i) => {
        s.classList.remove('active', 'completed');
        if (i < step) s.classList.add('completed');
        else if (i === step) s.classList.add('active');
    });
    if (fill) fill.style.width = `${(step / Math.max(steps.length - 1, 1)) * 100}%`;
}

// ─── Download ─────────────────────────────────────────────────────────────────
async function downloadWebsite() {
    if (!currentProjectId) { showToast('Generate a website first', 'warning'); return; }
    window.open(`/api/projects/${currentProjectId}/download`, '_blank');
}

// ─── Full preview ─────────────────────────────────────────────────────────────
function openFullPreview() {
    if (!currentProjectId) { showToast('Generate a website first', 'warning'); return; }
    window.open(`/preview/${currentProjectId}`, '_blank');
}
