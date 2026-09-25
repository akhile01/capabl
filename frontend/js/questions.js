document.addEventListener('DOMContentLoaded', () => {
  if (!API.checkAuth()) return;
  renderNav();
  
  // Set filters from URL if from Library
  const urlParams = new URLSearchParams(window.location.search);
  const doc = urlParams.get('doc');
  // API doesn't filter by doc currently, but normally we would. We'll set subject from active.
  document.getElementById('filt-subject').value = API.getSubject();
  
  document.getElementById('apply-filters').addEventListener('click', loadQuestions);
  
  setupModal();
  loadQuestions();
});

function setupModal() {
  const modal = document.getElementById('gen-modal');
  const btn = document.getElementById('open-gen-modal');
  const close = document.getElementById('close-modal');
  const form = document.getElementById('gen-form');
  
  btn.addEventListener('click', () => { modal.style.display = 'flex'; });
  close.addEventListener('click', () => { modal.style.display = 'none'; });
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const topic = document.getElementById('gen-topic').value;
    const diff = document.getElementById('gen-diff').value;
    const count = parseInt(document.getElementById('gen-count').value, 10);
    
    const submitBtn = document.getElementById('submit-gen');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Generating...';
    
    try {
      const subj = API.getSubject();
      await API.post('/questions/generate', { topic, difficulty: diff, count, subject: subj });
      modal.style.display = 'none';
      submitBtn.disabled = false;
      submitBtn.textContent = 'Generate';
      document.getElementById('filt-topic').value = topic; // auto filter to it
      loadQuestions();
    } catch (err) {
      alert('Failed: ' + err.message);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Generate';
    }
  });
}

async function loadQuestions() {
  switchState('questions-container', 'loading');
  
  const subj = document.getElementById('filt-subject').value;
  const topic = document.getElementById('filt-topic').value;
  const diff = document.getElementById('filt-difficulty').value;
  
  let url = '/questions?';
  const params = new URLSearchParams();
  if (subj) params.append('subject', subj);
  if (topic) params.append('topic', topic);
  if (diff) params.append('difficulty', diff);
  
  try {
    const data = await API.get(`/questions?${params.toString()}`);
    const qs = data.questions || [];
    
    if (qs.length === 0) {
      switchState('questions-container', 'empty');
      return;
    }
    
    const list = document.getElementById('q-list');
    list.innerHTML = '';
    
    qs.forEach(q => {
      const card = document.createElement('div');
      card.className = 'card question-card';
      
      const meta = document.createElement('div');
      meta.className = 'q-meta';
      
      const subjBadge = document.createElement('span');
      subjBadge.className = 'badge badge-accent';
      subjBadge.textContent = q.subject;
      meta.appendChild(subjBadge);
      
      const topicBadge = document.createElement('span');
      topicBadge.className = 'badge badge-accent';
      topicBadge.textContent = q.topic;
      meta.appendChild(topicBadge);
      
      const diffBadge = document.createElement('span');
      diffBadge.className = 'badge badge-warning';
      diffBadge.textContent = q.difficulty;
      meta.appendChild(diffBadge);
      
      if (q.bloom_level) {
        const bloomBadge = document.createElement('span');
        bloomBadge.className = 'badge badge-accent';
        bloomBadge.textContent = q.bloom_level;
        meta.appendChild(bloomBadge);
      }
      
      const qd = typeof q.question_data === 'string' ? JSON.parse(q.question_data) : q.question_data;
      
      const text = document.createElement('div');
      text.className = 'q-text';
      text.textContent = qd.question_text || q.question_text;
      
      card.appendChild(meta);
      card.appendChild(text);
      
      const opts = qd.options || [];
      opts.forEach(o => {
        const odiv = document.createElement('div');
        odiv.className = 'q-option';
        odiv.textContent = o;
        if (o === qd.correct_answer) odiv.classList.add('is-correct');
        card.appendChild(odiv);
      });
      
      const details = document.createElement('div');
      details.className = 'q-details';
      const detEl = document.createElement('details');
      const sumEl = document.createElement('summary');
      sumEl.style.cursor = 'pointer';
      sumEl.style.fontWeight = '600';
      sumEl.style.color = 'var(--muted)';
      sumEl.style.marginBottom = '8px';
      sumEl.textContent = 'Explanation';
      
      const expP = document.createElement('p');
      expP.textContent = qd.explanation || 'None';
      
      detEl.appendChild(sumEl);
      detEl.appendChild(expP);
      details.appendChild(detEl);
      
      if (q.validation_score !== undefined) {
        const d = document.createElement('div');
        d.style.marginTop = '8px';
        d.style.color = 'var(--muted)';
        
        let colorClass = 'fill-accent';
        if (q.validation_score < 0.8) colorClass = 'fill-warning';
        
        d.innerHTML = `
          Validation: ${q.validation_score} 
          <div class="score-meter"><div class="score-fill ${colorClass}" style="width: ${q.validation_score * 100}%"></div></div>
          &nbsp;&nbsp; | &nbsp;&nbsp; Passed on attempt: ${q.generation_version || 1}
        `;
        details.appendChild(d);
      }
      
      const actions = document.createElement('div');
      actions.className = 'actions';
      
      const previewBtn = document.createElement('a');
      previewBtn.href = `/quiz?topic=${encodeURIComponent(q.topic)}`;
      previewBtn.className = 'btn btn-ghost btn-ghost-small';
      previewBtn.textContent = 'Preview as student';
      
      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'btn btn-ghost btn-ghost-small';
      deleteBtn.style.color = 'var(--error)';
      deleteBtn.textContent = 'Delete';
      deleteBtn.onclick = () => alert('Delete not fully implemented yet');
      
      actions.appendChild(previewBtn);
      actions.appendChild(deleteBtn);
      
      card.appendChild(details);
      card.appendChild(actions);
      list.appendChild(card);
    });
    
    switchState('questions-container', 'loaded');
  } catch(err) {
    console.error(err);
  }
}
