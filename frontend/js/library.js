document.addEventListener('DOMContentLoaded', () => {
  if (!API.checkAuth()) return;
  renderNav();
  
  const subjInput = document.getElementById('subj-input');
  subjInput.value = API.getSubject();
  
  setupUpload();
  loadDocuments();
});

let selectedFile = null;

function setupUpload() {
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');
  const form = document.getElementById('upload-form');
  
  zone.addEventListener('click', () => input.click());
  
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
  });
  
  input.addEventListener('change', () => {
    if (input.files.length) handleFile(input.files[0]);
  });
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!selectedFile) return;
    
    const subj = document.getElementById('subj-input').value;
    const chap = document.getElementById('chap-input').value;
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('subject', subj);
    if (chap) formData.append('chapter', chap);
    
    document.getElementById('upload-btn').disabled = true;
    startPipeline();
    
    try {
      const res = await fetch('/api/ingest', {
        method: 'POST',
        body: formData // no json headers for multipart
      });
      if (!res.ok) {
        let msg = "Upload failed";
        try { const j = await res.json(); msg = j.detail || msg; } catch(e){}
        throw new Error(msg);
      }
      finishPipeline();
      setTimeout(() => {
        resetUpload();
        loadDocuments();
      }, 1000);
    } catch(err) {
      alert(err.message);
      resetUpload();
    }
  });
}

function handleFile(file) {
  if (file.type !== 'application/pdf') return alert('Please upload a PDF.');
  if (file.size > 25 * 1024 * 1024) return alert('File exceeds 25 MB.');
  
  selectedFile = file;
  document.getElementById('selected-file').textContent = file.name;
  document.getElementById('upload-form').style.display = 'block';
}

let pipeInterval;
function startPipeline() {
  const pipe = document.getElementById('pipeline');
  pipe.style.display = 'flex';
  
  let currentStep = 1;
  const update = () => {
    if (currentStep > 4) return;
    document.querySelectorAll('.pipeline-step').forEach(el => {
      el.classList.remove('active');
    });
    const el = document.getElementById(`step-${currentStep}`);
    if (el) el.classList.add('active');
    
    // mark previous done
    for(let i=1; i<currentStep; i++) {
      document.getElementById(`step-${i}`).classList.add('done');
    }
  };
  
  update();
  pipeInterval = setInterval(() => {
    if (currentStep < 4) { currentStep++; update(); }
  }, 3000);
}

function finishPipeline() {
  clearInterval(pipeInterval);
  document.querySelectorAll('.pipeline-step').forEach(el => {
    el.classList.remove('active');
    el.classList.add('done');
  });
}

function resetUpload() {
  clearInterval(pipeInterval);
  document.getElementById('pipeline').style.display = 'none';
  document.getElementById('upload-form').style.display = 'none';
  document.getElementById('upload-btn').disabled = false;
  document.querySelectorAll('.pipeline-step').forEach(el => {
    el.classList.remove('active', 'done');
  });
  document.getElementById('step-1').classList.add('active');
  selectedFile = null;
  document.getElementById('selected-file').textContent = '';
  document.getElementById('file-input').value = '';
}

async function loadDocuments() {
  try {
    const data = await API.get('/documents');
    const tbody = document.getElementById('docs-tbody');
    tbody.innerHTML = '';
    
    (data.documents || []).forEach(doc => {
      const tr = document.createElement('tr');
      
      const tdName = document.createElement('td');
      tdName.textContent = doc.filename;
      tdName.style.fontWeight = '600';
      
      const tdSubj = document.createElement('td');
      tdSubj.textContent = doc.subject;
      
      const tdTop = document.createElement('td');
      let topics = [];
      try { topics = JSON.parse(doc.extracted_topics) || []; } catch(e){}
      tdTop.textContent = topics.length > 0 ? topics.join(', ') : '-';
      
      const tdDate = document.createElement('td');
      tdDate.textContent = doc.created_at.split(' ')[0];
      
      const tdStatus = document.createElement('td');
      const badge = document.createElement('span');
      badge.className = 'badge ' + (doc.status === 'completed' ? 'badge-success' : 'badge-warning');
      badge.textContent = doc.status;
      tdStatus.appendChild(badge);
      
      const tdAct = document.createElement('td');
      tdAct.innerHTML = `<a href="/questions?doc=${encodeURIComponent(doc.filename)}" class="btn btn-ghost btn-ghost-small" style="padding:0">View questions</a>`;
      
      tr.appendChild(tdName);
      tr.appendChild(tdSubj);
      tr.appendChild(tdTop);
      tr.appendChild(tdDate);
      tr.appendChild(tdStatus);
      tr.appendChild(tdAct);
      tbody.appendChild(tr);
    });
  } catch(err) {
    console.error(err);
  }
}
