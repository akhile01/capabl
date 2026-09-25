let fullLogs = [];
let filteredLogs = [];
let currentPage = 1;
const PER_PAGE = 20;

let masteryData = [];
let sortMasteryAsc = false;

document.addEventListener('DOMContentLoaded', async () => {
  if (!API.checkAuth()) return;
  renderNav();
  
  document.getElementById('sort-mastery').addEventListener('click', () => {
    sortMasteryAsc = !sortMasteryAsc;
    document.getElementById('sort-mastery').textContent = sortMasteryAsc ? 'Sort A-Z' : 'Sort by Mastery';
    renderMasteryChart();
  });
  
  document.querySelectorAll('.filter-pill').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
      applyFilter(e.target.dataset.filter);
    });
  });
  
  document.getElementById('prev-page').addEventListener('click', () => {
    if (currentPage > 1) { currentPage--; renderTable(); }
  });
  document.getElementById('next-page').addEventListener('click', () => {
    if (currentPage * PER_PAGE < filteredLogs.length) { currentPage++; renderTable(); }
  });
  
  document.getElementById('export-csv').addEventListener('click', exportCSV);
  
  await loadProgress();
});

async function loadProgress() {
  switchState('progress-container', 'loading');
  try {
    const studentId = API.getStudentId();
    const data = await API.get(`/analytics/${studentId}`);
    
    masteryData = data.mastery || [];
    fullLogs = data.recent_performance || [];
    filteredLogs = [...fullLogs];
    
    computeStats();
    renderMasteryChart();
    renderTable();
    
    switchState('progress-container', 'loaded');
  } catch(err) {
    document.getElementById('error-msg').textContent = err.message;
    switchState('progress-container', 'error');
  }
}

function computeStats() {
  let easy = { total: 0, correct: 0 };
  let med = { total: 0, correct: 0 };
  let hard = { total: 0, correct: 0 };
  let hints = 0;
  
  fullLogs.forEach(l => {
    if (l.difficulty === 'easy') { easy.total++; if (l.correct) easy.correct++; }
    if (l.difficulty === 'medium') { med.total++; if (l.correct) med.correct++; }
    if (l.difficulty === 'hard') { hard.total++; if (l.correct) hard.correct++; }
    if (l.hint_used) hints++;
  });
  
  const calc = (s) => s.total ? Math.round((s.correct / s.total) * 100) + '%' : '-';
  
  document.getElementById('acc-easy').textContent = calc(easy);
  document.getElementById('acc-med').textContent = calc(med);
  document.getElementById('acc-hard').textContent = calc(hard);
  
  document.getElementById('hint-rate').textContent = fullLogs.length ? Math.round((hints / fullLogs.length) * 100) + '%' : '-';
}

function renderMasteryChart() {
  const container = document.getElementById('mastery-chart');
  container.innerHTML = '';
  
  let data = [...masteryData];
  if (sortMasteryAsc) {
    data.sort((a,b) => a.mastery_level - b.mastery_level);
  } else {
    data.sort((a,b) => a.topic.localeCompare(b.topic));
  }
  
  data.forEach(item => {
    const row = document.createElement('div');
    row.className = 'mastery-row';
    
    const name = document.createElement('div');
    name.textContent = item.topic;
    name.style.fontSize = '14px';
    
    const barBg = document.createElement('div');
    barBg.className = 'progress-bar-bg';
    const barFill = document.createElement('div');
    barFill.className = 'progress-bar-fill';
    
    const val = Math.round(item.mastery_level * 100);
    barFill.style.width = `${val}%`;
    if (item.mastery_level < 0.4) barFill.classList.add('fill-warning');
    else if (item.mastery_level > 0.8) barFill.classList.add('fill-success');
    else barFill.classList.add('fill-accent');
    barBg.appendChild(barFill);
    
    const pct = document.createElement('div');
    pct.className = 'mono-num';
    pct.textContent = `${val}%`;
    pct.style.textAlign = 'right';
    
    row.appendChild(name);
    row.appendChild(barBg);
    row.appendChild(pct);
    container.appendChild(row);
  });
}

function applyFilter(f) {
  if (f === 'all') filteredLogs = [...fullLogs];
  else if (f === 'correct') filteredLogs = fullLogs.filter(l => l.correct);
  else if (f === 'incorrect') filteredLogs = fullLogs.filter(l => !l.correct);
  
  currentPage = 1;
  renderTable();
}

function renderTable() {
  const tbody = document.getElementById('activity-tbody');
  tbody.innerHTML = '';
  
  const start = (currentPage - 1) * PER_PAGE;
  const pageItems = filteredLogs.slice(start, start + PER_PAGE);
  
  pageItems.forEach(item => {
    const tr = document.createElement('tr');
    
    const tTime = document.createElement('td');
    const d = new Date(item.timestamp + 'Z'); // sqlite timestamp usually UTC
    tTime.textContent = isNaN(d) ? item.timestamp : d.toLocaleString();
    tTime.style.color = 'var(--muted)';
    tTime.style.fontSize = '12px';
    
    const tTopic = document.createElement('td');
    tTopic.textContent = item.topic;
    tTopic.style.fontWeight = '600';
    
    const tDiff = document.createElement('td');
    tDiff.innerHTML = `<span class="badge badge-accent">${item.difficulty}</span>`;
    
    const tRes = document.createElement('td');
    tRes.innerHTML = item.correct ? '<span style="color:var(--success)">✓ Correct</span>' : '<span style="color:var(--error)">✗ Incorrect</span>';
    
    const tHint = document.createElement('td');
    if (item.hint_used) tHint.innerHTML = '<span class="badge badge-warning">Used</span>';
    
    const tAct = document.createElement('td');
    tAct.innerHTML = `<a href="/quiz?topic=${encodeURIComponent(item.topic)}" class="btn btn-ghost btn-ghost-small" style="padding:0">Practice</a>`;
    
    tr.appendChild(tTime);
    tr.appendChild(tTopic);
    tr.appendChild(tDiff);
    tr.appendChild(tRes);
    tr.appendChild(tHint);
    tr.appendChild(tAct);
    tbody.appendChild(tr);
  });
  
  document.getElementById('prev-page').disabled = currentPage === 1;
  document.getElementById('next-page').disabled = currentPage * PER_PAGE >= filteredLogs.length;
  
  const totalPages = Math.ceil(filteredLogs.length / PER_PAGE) || 1;
  document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
}

function exportCSV() {
  if (fullLogs.length === 0) return;
  const headers = ['Timestamp', 'Topic', 'Difficulty', 'Correct', 'Hint Used'];
  const rows = fullLogs.map(l => [
    l.timestamp,
    `"${l.topic.replace(/"/g, '""')}"`,
    l.difficulty,
    l.correct ? 'Yes' : 'No',
    l.hint_used ? 'Yes' : 'No'
  ].join(','));
  
  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'activity_log.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}
