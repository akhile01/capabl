document.addEventListener('DOMContentLoaded', () => {
    initLibrary();
});

async function initLibrary() {
    let studentId = localStorage.getItem('student_id');
    if (!studentId) {
        // Just in case they land here directly
        return;
    }
    
    // We attempt to fetch from a hypothetic endpoint. Since it doesn't exist, it will fail
    // and we gracefully default to empty state as instructed ("do not fabricate").
    try {
        const res = await fetch(`${API_BASE}/library/${studentId}`);
        if (!res.ok) throw new Error("Endpoint unavailable");
        const data = await res.json();
        
        if (data.materials && data.materials.length > 0) {
            renderLibrary(data);
        } else {
            showEmptyState();
        }
    } catch (e) {
        console.warn("Library API not yet implemented on backend, showing empty state.", e);
        showEmptyState();
    }
}

function showEmptyState() {
    document.getElementById('empty-state').classList.remove('hidden');
    document.getElementById('document-list').classList.add('hidden');
    document.getElementById('subjects-section').classList.add('hidden');
    
    document.getElementById('stat-materials').textContent = '0';
    document.getElementById('stat-ready').textContent = '0';
    document.getElementById('stat-subjects').textContent = '0';
    document.getElementById('stat-processing').textContent = '0';
}

function renderLibrary(data) {
    // Left as placeholder for when the backend is connected
    const list = document.getElementById('document-list');
    const empty = document.getElementById('empty-state');
    
    empty.classList.add('hidden');
    list.classList.remove('hidden');
    // ... render rows
}

// Modal Logic
function openUploadModal() {
    document.getElementById('upload-modal').classList.remove('hidden');
    resetUpload();
}

function closeUploadModal() {
    document.getElementById('upload-modal').classList.add('hidden');
}

function resetUpload() {
    document.getElementById('drop-zone').classList.remove('hidden');
    document.getElementById('upload-state').classList.add('hidden');
    document.getElementById('upload-error').classList.add('hidden');
    document.getElementById('file-input').value = '';
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    document.getElementById('drop-zone').classList.add('hidden');
    document.getElementById('upload-state').classList.remove('hidden');
    document.getElementById('up-filename').textContent = file.name;
    document.getElementById('up-status').textContent = 'EXTRACTING CONTENT...';
    
    // Simulate processing delay, then fail since we have no backend upload endpoint
    setTimeout(() => {
        closeUploadModal();
        if (window.showToast) {
            window.showToast("UPLOAD FAILED", "Backend endpoint unavailable.", "error");
        }
    }, 2000);
}

function retryUpload() {
    resetUpload();
}
