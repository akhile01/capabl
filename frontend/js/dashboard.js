document.addEventListener('DOMContentLoaded', () => {
  if (!API.checkAuth()) return;
  renderNav();
  
  const name = API.getStudentName();
  document.getElementById('greeting').textContent = `Hello, ${name}`;
  
  const subjectInput = document.getElementById('subject-input');
  subjectInput.value = API.getSubject();
  
  document.getElementById('subject-update-btn').addEventListener('click', () => {
    const subj = subjectInput.value.trim();
    if (subj) {
      API.setStudent(API.getStudentId(), name, subj);
      loadDashboard();
    }
  });

  loadDashboard();
});

async function loadDashboard() {
  switchState('dashboard-content', 'loading'); // actually switch global state
  const container = document.querySelector('.container');
  // Hack for switchState scope
  container.id = 'dashboard-container';
  switchState('dashboard-container', 'loading');

  try {
    const studentId = API.getStudentId();
    const [revData, analyticsData] = await Promise.all([
      API.get(`/revision/${studentId}`),
      API.get(`/analytics/${studentId}`)
    ]);

    const revision = revData.revision || [];
    const mastery = analyticsData.mastery || [];
    const recent = analyticsData.recent_performance || [];

    if (mastery.length === 0 && revision.length === 0) {
      switchState('dashboard-container', 'empty');
      return;
    }

    // Calc Stats
    const masteredCount = mastery.filter(m => m.mastery_level > 0.8).length;
    const dueCount = revision.filter(r => r.is_due).length;
    let accuracy = 0;
    if (recent.length > 0) {
      const correct = recent.filter(r => r.correct).length;
      accuracy = Math.round((correct / recent.length) * 100);
    }

    document.getElementById('stat-mastered').textContent = masteredCount;
    document.getElementById('stat-due').textContent = dueCount;
    document.getElementById('stat-accuracy').textContent = `${accuracy}%`;

    renderRevision(revision);
    renderMastery(mastery);
    renderActivity(recent);

    switchState('dashboard-container', 'loaded');
  } catch (err) {
    document.getElementById('error-msg').textContent = err.message;
    switchState('dashboard-container', 'error');
  }
}

function renderRevision(revisionList) {
  const container = document.getElementById('revision-list');
  container.innerHTML = '';
  
  // Show up to 5
  const items = revisionList.slice(0, 5);
  
  items.forEach(item => {
    const row = document.createElement('div');
    row.className = 'list-row';
    
    const left = document.createElement('div');
    left.className = 'row-left';
    
    const title = document.createElement('div');
    title.className = 'topic-name';
    title.textContent = item.topic;
    
    const tag = document.createElement('div');
    tag.className = 'badge';
    if (item.is_due) {
      tag.classList.add('badge-accent');
      tag.textContent = 'Due';
    } else if (item.is_weak) {
      tag.classList.add('badge-warning');
      tag.textContent = 'Weak';
    } else {
      tag.classList.add('badge-success');
      tag.textContent = 'Strong';
    }
    
    left.appendChild(title);
    left.appendChild(tag);
    
    const right = document.createElement('div');
    right.className = 'row-right';
    
    const pct = document.createElement('div');
    pct.className = 'mono-num';
    pct.textContent = `${Math.round(item.mastery_level * 100)}%`;
    
    const btn = document.createElement('a');
    btn.className = 'btn btn-ghost btn-ghost-small';
    btn.href = `/quiz?topic=${encodeURIComponent(item.topic)}`;
    btn.textContent = 'Review';
    
    right.appendChild(pct);
    right.appendChild(btn);
    
    row.appendChild(left);
    row.appendChild(right);
    container.appendChild(row);
  });
}

function renderMastery(masteryList) {
  const container = document.getElementById('mastery-list');
  container.innerHTML = '';
  
  masteryList.forEach(item => {
    const wrap = document.createElement('div');
    wrap.style.marginBottom = '16px';
    
    const header = document.createElement('div');
    header.style.display = 'flex';
    header.style.justifyContent = 'space-between';
    header.style.fontSize = '14px';
    
    const name = document.createElement('span');
    name.textContent = item.topic;
    
    const pct = document.createElement('span');
    pct.className = 'mono-num';
    const val = Math.round(item.mastery_level * 100);
    pct.textContent = `${val}%`;
    
    header.appendChild(name);
    header.appendChild(pct);
    
    const barBg = document.createElement('div');
    barBg.className = 'progress-bar-bg';
    
    const barFill = document.createElement('div');
    barFill.className = 'progress-bar-fill';
    barFill.style.width = `${val}%`;
    
    if (item.mastery_level < 0.4) barFill.classList.add('fill-warning');
    else if (item.mastery_level > 0.8) barFill.classList.add('fill-success');
    else barFill.classList.add('fill-accent');
    
    barBg.appendChild(barFill);
    wrap.appendChild(header);
    wrap.appendChild(barBg);
    container.appendChild(wrap);
  });
}

function renderActivity(recentList) {
  const container = document.getElementById('activity-list');
  container.innerHTML = '';
  
  const items = recentList.slice(0, 5);
  
  items.forEach(item => {
    const row = document.createElement('div');
    row.className = 'list-row';
    
    const left = document.createElement('div');
    left.className = 'row-left';
    
    const icon = document.createElement('div');
    icon.className = 'activity-icon ' + (item.correct ? 'icon-correct' : 'icon-wrong');
    icon.textContent = item.correct ? '✓' : '✗';
    
    const title = document.createElement('div');
    title.textContent = item.topic;
    title.style.fontSize = '14px';
    
    left.appendChild(icon);
    left.appendChild(title);
    
    const right = document.createElement('div');
    right.className = 'row-right';
    
    const diffTag = document.createElement('div');
    diffTag.className = 'badge badge-accent';
    diffTag.textContent = item.difficulty;
    right.appendChild(diffTag);
    
    if (item.hint_used) {
      const hintTag = document.createElement('div');
      hintTag.className = 'badge badge-warning';
      hintTag.textContent = 'Hint used';
      right.appendChild(hintTag);
    }
    
    row.appendChild(left);
    row.appendChild(right);
    container.appendChild(row);
  });
}
