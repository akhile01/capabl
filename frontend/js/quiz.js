let currentQuestion = null;
let selectedOption = null;
let attemptCount = 1;
let sessionLog = JSON.parse(sessionStorage.getItem('quiz_session')) || [];
let loadingInterval = null;

document.addEventListener('DOMContentLoaded', () => {
  if (!API.checkAuth()) return;
  renderNav();
  
  if (sessionLog.length >= 10) {
    window.location.href = '/quiz/summary';
    return;
  }
  
  document.getElementById('retry-btn').addEventListener('click', loadNextQuestion);
  document.getElementById('submit-btn').addEventListener('click', submitAnswer);
  document.getElementById('next-btn').addEventListener('click', goToNext);
  
  setupKeyboard();
  loadNextQuestion();
});

function setupKeyboard() {
  document.addEventListener('keydown', (e) => {
    if (document.getElementById('view-loaded').classList.contains('active')) {
      const submitBtn = document.getElementById('submit-btn');
      const nextBtn = document.getElementById('next-btn');
      
      if (e.key === 'Enter') {
        if (submitBtn.style.display !== 'none' && !submitBtn.disabled) {
          submitAnswer();
        }
      } else if (e.key.toLowerCase() === 'n') {
        if (nextBtn.style.display !== 'none') {
          goToNext();
        }
      } else {
        // Map 1-4 or a-d to options
        const key = e.key.toLowerCase();
        let idx = -1;
        if (key === '1' || key === 'a') idx = 0;
        if (key === '2' || key === 'b') idx = 1;
        if (key === '3' || key === 'c') idx = 2;
        if (key === '4' || key === 'd') idx = 3;
        
        if (idx !== -1) {
          const btns = document.querySelectorAll('.option-btn:not(:disabled)');
          if (btns[idx]) btns[idx].click();
        }
      }
    }
  });
}

function startLoading() {
  switchState('container', 'loading'); // scope fix
  document.querySelector('.container').id = 'quiz-container';
  switchState('quiz-container', 'loading');
  
  const textEl = document.getElementById('loading-text');
  textEl.textContent = 'Checking your mastery...';
  
  let time = 0;
  clearInterval(loadingInterval);
  loadingInterval = setInterval(() => {
    time++;
    if (time === 3) textEl.textContent = 'Generating a grounded question...';
    if (time === 8) textEl.textContent = 'Self-critiquing it...';
    if (time >= 20) {
      clearInterval(loadingInterval);
      document.getElementById('error-msg').textContent = 'Generation took too long.';
      switchState('quiz-container', 'error');
    }
  }, 1000);
}

async function loadNextQuestion() {
  startLoading();
  attemptCount = 1;
  selectedOption = null;
  document.getElementById('feedback-container').innerHTML = '';
  document.getElementById('submit-btn').style.display = 'block';
  document.getElementById('submit-btn').disabled = true;
  document.getElementById('submit-btn').textContent = 'Submit Answer';
  document.getElementById('next-btn').style.display = 'none';
  
  try {
    const studentId = API.getStudentId();
    // Check if topic is in URL (from dashboard)
    const urlParams = new URLSearchParams(window.location.search);
    const specificTopic = urlParams.get('topic');
    let endpoint = `/next_question/${studentId}`;
    if (specificTopic) {
      const subject = API.getSubject();
      endpoint += `?subject=${encodeURIComponent(subject)}&topic=${encodeURIComponent(specificTopic)}`;
    }
    
    const res = await API.get(endpoint);
    clearInterval(loadingInterval);
    
    currentQuestion = res.question;
    renderQuestion(res);
    switchState('quiz-container', 'loaded');
  } catch (err) {
    clearInterval(loadingInterval);
    document.getElementById('error-msg').textContent = err.message;
    switchState('quiz-container', 'error');
  }
}

function renderQuestion(data) {
  const q = data.question;
  
  document.getElementById('topic-badge').textContent = q.topic;
  document.getElementById('difficulty-badge').textContent = q.difficulty;
  document.getElementById('q-counter').textContent = `Q ${sessionLog.length + 1} / 10`;
  document.getElementById('attempt-counter').textContent = `Attempt ${attemptCount} of 3`;
  
  document.getElementById('reason-strip').textContent = data.reason || 'Selected based on your mastery.';
  
  document.getElementById('question-text').textContent = q.question_text;
  
  const bloomBadge = document.getElementById('bloom-badge');
  bloomBadge.innerHTML = '';
  if (q.bloom_level) {
    const span = document.createElement('span');
    span.className = 'badge badge-accent';
    span.textContent = q.bloom_level;
    bloomBadge.appendChild(span);
  }
  
  const optsContainer = document.getElementById('options-container');
  optsContainer.innerHTML = '';
  
  const labels = ['A', 'B', 'C', 'D'];
  (q.options || []).forEach((opt, idx) => {
    const btn = document.createElement('button');
    btn.className = 'option-btn';
    btn.dataset.value = opt;
    
    const letter = document.createElement('span');
    letter.className = 'option-letter';
    letter.textContent = labels[idx];
    
    const text = document.createElement('span');
    text.textContent = opt;
    
    btn.appendChild(letter);
    btn.appendChild(text);
    
    btn.addEventListener('click', () => {
      if (btn.disabled) return;
      document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      selectedOption = opt;
      document.getElementById('submit-btn').disabled = false;
    });
    
    optsContainer.appendChild(btn);
  });
}

async function submitAnswer() {
  if (!selectedOption) return;
  
  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  btn.textContent = 'Evaluating...';
  
  document.querySelectorAll('.option-btn').forEach(b => b.disabled = true);
  
  try {
    const studentId = API.getStudentId();
    const res = await API.post(`/answer/${studentId}`, {
      question_id: currentQuestion.id,
      answer: selectedOption,
      attempt_count: attemptCount
    });
    
    handleFeedback(res);
  } catch(err) {
    alert('Error submitting answer: ' + err.message);
    btn.disabled = false;
    btn.textContent = 'Submit Answer';
    document.querySelectorAll('.option-btn:not(.locked-wrong)').forEach(b => b.disabled = false);
  }
}

function handleFeedback(res) {
  const fbContainer = document.getElementById('feedback-container');
  const btn = document.getElementById('submit-btn');
  const nextBtn = document.getElementById('next-btn');
  
  const panel = document.createElement('div');
  panel.className = 'feedback-panel';
  
  const title = document.createElement('div');
  title.className = 'feedback-title';
  
  const body = document.createElement('div');
  body.textContent = res.feedback || res.explanation;
  
  if (res.status === 'retry') {
    panel.classList.add('panel-retry');
    title.textContent = 'Think about this';
    
    // Lock wrong
    const selectedBtn = document.querySelector('.option-btn.selected');
    if (selectedBtn) {
      selectedBtn.classList.remove('selected');
      selectedBtn.classList.add('locked-wrong');
    }
    
    selectedOption = null;
    attemptCount++;
    document.getElementById('attempt-counter').textContent = `Attempt ${attemptCount} of 3`;
    
    // Re-enable others
    document.querySelectorAll('.option-btn:not(.locked-wrong)').forEach(b => b.disabled = false);
    btn.textContent = 'Submit Answer';
    
  } else if (res.status === 'completed') {
    btn.style.display = 'none';
    nextBtn.style.display = 'block';
    nextBtn.focus();
    
    // Log to session
    sessionLog.push({
      topic: currentQuestion.topic,
      correct: res.is_correct,
      attempts: attemptCount,
      hint_used: attemptCount > 1
    });
    sessionStorage.setItem('quiz_session', JSON.stringify(sessionLog));
    
    if (res.is_correct) {
      panel.classList.add('panel-success');
      title.textContent = 'Correct';
      const selectedBtn = document.querySelector('.option-btn.selected');
      if (selectedBtn) selectedBtn.classList.add('correct');
    } else {
      panel.classList.add('panel-error');
      title.textContent = "Here's the idea";
      // Lock picked
      const selectedBtn = document.querySelector('.option-btn.selected');
      if (selectedBtn) selectedBtn.classList.add('locked-wrong');
      // Highlight correct (if returned, but API doesn't return correct option directly in response, 
      // however it might be possible to deduce if we have the full object. Wait, API doesn't return correct answer to client)
    }
  }
  
  panel.appendChild(title);
  panel.appendChild(body);
  fbContainer.innerHTML = '';
  fbContainer.appendChild(panel);
}

function goToNext() {
  if (sessionLog.length >= 10) {
    window.location.href = '/quiz/summary';
  } else {
    // Remove specific topic filter to allow orchestrator to pick next
    const url = new URL(window.location);
    url.searchParams.delete('topic');
    window.history.replaceState({}, '', url);
    
    loadNextQuestion();
  }
}
