// library.js — Knowledge Library page.
// Talks to the real backend: GET /api/documents for the list, POST /api/ingest for uploads.

let libraryDocs = [];
let pendingFile = null; // file chosen before a subject was entered

document.addEventListener('DOMContentLoaded', () => {
    initLibrary();
    setupDropZone();
    const search = document.getElementById('lib-search');
    if (search) search.addEventListener('input', renderLibrary);
});

async function initLibrary() {
    try {
        const res = await fetch(`${API_BASE}/documents`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        libraryDocs = data.documents || [];
    } catch (e) {
        console.error('Failed to load library', e);
        libraryDocs = [];
        if (window.showToast) window.showToast('LIBRARY UNAVAILABLE', 'Could not load your documents from the server.', 'error');
    }
    renderLibrary();
}

function renderLibrary() {
    const query = (document.getElementById('lib-search')?.value || '').trim().toLowerCase();
    const visible = libraryDocs.filter(d =>
        !query ||
        (d.filename || '').toLowerCase().includes(query) ||
        (d.subject || '').toLowerCase().includes(query) ||
        (d.chapters || '').toLowerCase().includes(query)
    );

    // Stats are over the whole library, not the filtered view
    const subjects = new Set(libraryDocs.map(d => d.subject).filter(Boolean));
    const ready = libraryDocs.filter(d => d.status === 'completed').length;
    document.getElementById('stat-materials').textContent = libraryDocs.length;
    document.getElementById('stat-ready').textContent = ready;
    document.getElementById('stat-subjects').textContent = subjects.size;
    document.getElementById('stat-processing').textContent = libraryDocs.length - ready;

    const empty = document.getElementById('empty-state');
    const list = document.getElementById('document-list');
    const subjectsSection = document.getElementById('subjects-section');

    if (libraryDocs.length === 0) {
        empty.classList.remove('hidden');
        list.classList.add('hidden');
        subjectsSection.classList.add('hidden');
        return;
    }

    empty.classList.add('hidden');
    list.classList.remove('hidden');

    const rows = document.getElementById('doc-rows');
    rows.innerHTML = '';
    if (visible.length === 0) {
        rows.innerHTML = '<div class="doc-row doc-row-empty">No material matches your search.</div>';
    }
    visible.forEach(doc => {
        const row = document.createElement('div');
        row.className = 'doc-row';
        const status = (doc.status || 'processing').toUpperCase();
        const statusClass = doc.status === 'completed' ? 'strong' : 'weak';
        row.innerHTML = `
            <div class="d-col d-name">${escapeHtml(doc.filename)}${doc.chapters ? `<span class="d-sub">${escapeHtml(doc.chapters)}</span>` : ''}</div>
            <div class="d-col d-subj">${escapeHtml(doc.subject || '—')}</div>
            <div class="d-col d-stat"><span class="row-status ${statusClass}">${status}</span></div>
            <div class="d-col d-date">${formatDate(doc.created_at)}</div>
            <div class="d-col d-act"><button class="row-action" type="button">PRACTICE &rarr;</button></div>
        `;
        row.querySelector('.row-action').onclick = () => startPracticeForSubject(doc.subject);
        rows.appendChild(row);
    });

    // Subject cards
    const grid = document.getElementById('subject-grid');
    grid.innerHTML = '';
    if (subjects.size > 0) {
        subjectsSection.classList.remove('hidden');
        subjects.forEach(subject => {
            const count = libraryDocs.filter(d => d.subject === subject).length;
            const card = document.createElement('div');
            card.className = 'subject-card';
            card.setAttribute('role', 'button');
            card.tabIndex = 0;
            card.innerHTML = `
                <div class="subject-name">${escapeHtml(subject)}</div>
                <div class="subject-meta">${count} ${count === 1 ? 'document' : 'documents'}</div>
                <div class="subject-cta">PRACTICE &rarr;</div>
            `;
            card.onclick = () => startPracticeForSubject(subject);
            card.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); card.onclick(); } };
            grid.appendChild(card);
        });
    } else {
        subjectsSection.classList.add('hidden');
    }
}

function startPracticeForSubject(subject) {
    if (subject) localStorage.setItem('subject', subject);
    window.location.href = '/quiz';
}

function formatDate(value) {
    if (!value) return '—';
    const d = new Date(value.replace(' ', 'T') + (value.endsWith('Z') ? '' : 'Z'));
    if (isNaN(d.getTime())) return value;
    return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }).toUpperCase();
}

// ---------- Upload modal ----------
function openUploadModal() {
    document.getElementById('upload-modal').classList.remove('hidden');
    resetUpload();
    const subjectInput = document.getElementById('upload-subject');
    if (subjectInput && !subjectInput.value) {
        const saved = localStorage.getItem('subject');
        if (saved && saved !== 'Unknown') subjectInput.value = saved;
    }
}

function closeUploadModal() {
    document.getElementById('upload-modal').classList.add('hidden');
}

function resetUpload() {
    document.getElementById('upload-form').classList.remove('hidden');
    document.getElementById('upload-state').classList.add('hidden');
    document.getElementById('upload-error').classList.add('hidden');
    document.getElementById('file-input').value = '';
    setPendingFile(null);
}

function setPendingFile(file) {
    pendingFile = file;
    const text = document.querySelector('#drop-zone .drop-text');
    const sub = document.querySelector('#drop-zone .drop-sub');
    if (!text || !sub) return;
    if (file) {
        text.textContent = `SELECTED: ${file.name}`;
        sub.textContent = 'Enter a subject above and press Enter to upload';
    } else {
        text.textContent = 'DROP YOUR MATERIAL HERE';
        sub.textContent = 'or choose a file';
    }
}

function setupDropZone() {
    const zone = document.getElementById('drop-zone');
    if (!zone) return;
    ['dragenter', 'dragover'].forEach(evt => zone.addEventListener(evt, e => {
        e.preventDefault();
        zone.classList.add('dragover');
    }));
    ['dragleave', 'drop'].forEach(evt => zone.addEventListener(evt, e => {
        e.preventDefault();
        zone.classList.remove('dragover');
    }));
    zone.addEventListener('drop', e => {
        const file = e.dataTransfer?.files?.[0];
        if (file) uploadFile(file);
    });
    // A file picked before the subject was filled in uploads once the subject is confirmed
    const subjectInput = document.getElementById('upload-subject');
    if (subjectInput) {
        subjectInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') { e.preventDefault(); if (pendingFile) uploadFile(pendingFile); }
        });
        subjectInput.addEventListener('change', () => { if (pendingFile && subjectInput.value.trim()) uploadFile(pendingFile); });
    }
    // Close the modal when clicking the dark backdrop or pressing Escape
    const modal = document.getElementById('upload-modal');
    modal.addEventListener('click', e => { if (e.target === modal) closeUploadModal(); });
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) closeUploadModal();
    });
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) uploadFile(file);
}

async function uploadFile(file) {
    const subjectInput = document.getElementById('upload-subject');
    const chapterInput = document.getElementById('upload-chapter');
    const subject = (subjectInput?.value || '').trim();

    if (!subject) {
        // Keep the file; the browser won't fire another change event for the same selection
        setPendingFile(file);
        document.getElementById('file-input').value = '';
        subjectInput.classList.add('input-error');
        subjectInput.focus();
        if (window.showToast) window.showToast('SUBJECT REQUIRED', 'Enter the subject this material belongs to, then press Enter.', 'warning');
        return;
    }
    subjectInput.classList.remove('input-error');
    setPendingFile(null);

    if (!file.name.toLowerCase().endsWith('.pdf')) {
        showUploadError('Only PDF files are supported by the content ingestion agent right now.');
        return;
    }
    if (file.size > 25 * 1024 * 1024) {
        showUploadError('File too large. The maximum size is 25 MB.');
        return;
    }

    document.getElementById('upload-form').classList.add('hidden');
    document.getElementById('upload-error').classList.add('hidden');
    document.getElementById('upload-state').classList.remove('hidden');
    document.getElementById('up-filename').textContent = file.name;
    document.getElementById('up-status').textContent = 'UPLOADING & EXTRACTING CONTENT...';

    const form = new FormData();
    form.append('file', file);
    form.append('subject', subject);
    if (chapterInput && chapterInput.value.trim()) form.append('chapter', chapterInput.value.trim());

    try {
        const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: form });
        let data = {};
        try { data = await res.json(); } catch (_) {}
        if (!res.ok) throw new Error(data.detail || `Upload failed (HTTP ${res.status})`);

        localStorage.setItem('subject', subject);
        closeUploadModal();
        if (window.showToast) {
            const chunks = data.chunks_stored != null ? ` ${data.chunks_stored} chunks indexed.` : '';
            window.showToast('MATERIAL READY', `${file.name} was processed.${chunks}`, 'success');
        }
        await initLibrary();
    } catch (e) {
        console.error(e);
        showUploadError(e.message);
    }
}

function showUploadError(message) {
    document.getElementById('upload-form').classList.add('hidden');
    document.getElementById('upload-state').classList.add('hidden');
    document.getElementById('upload-error').classList.remove('hidden');
    const desc = document.getElementById('upload-error-desc');
    if (desc) desc.textContent = message || "AdaptEd couldn't prepare this material.";
}

function retryUpload() {
    resetUpload();
}
