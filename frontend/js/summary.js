document.addEventListener('DOMContentLoaded', async () => {
  if (!API.checkAuth()) return;
  renderNav();
  
  const sessionLog = JSON.parse(sessionStorage.getItem('quiz_session')) || [];
  
  document.getElementById('practice-again').addEventListener('click', () => {
    sessionStorage.removeItem('quiz_session');
    window.location.href = '/quiz';
  });
  
  if (sessionLog.length === 0) {
    document.getElementById('score-stat').innerHTML = `<span>0</span> / 0`;
    switchState('container', 'loaded'); // scope fix
    document.querySelector('.container').id = 'summary-container';
    switchState('summary-container', 'loaded');
    return;
  }
  
  const total = sessionLog.length;
  const correct = sessionLog.filter(x => x.correct).length;
  
  document.getElementById('score-stat').innerHTML = `<span>${correct}</span> / ${total} correct`;
  
  // Group by topic
  const topics = {};
  sessionLog.forEach(log => {
    if (!topics[log.topic]) {
      topics[log.topic] = { count: 0, correct: 0, hints: 0 };
    }
    topics[log.topic].count++;
    if (log.correct) topics[log.topic].correct++;
    if (log.hint_used) topics[log.topic].hints++;
  });
  
  // Fetch analytics for current mastery
  try {
    const studentId = API.getStudentId();
    const analytics = await API.get(`/analytics/${studentId}`);
    const masteryMap = {};
    (analytics.mastery || []).forEach(m => {
      masteryMap[m.topic] = Math.round(m.mastery_level * 100) + '%';
    });
    
    const tbody = document.getElementById('summary-tbody');
    Object.keys(topics).forEach(topicName => {
      const t = topics[topicName];
      const tr = document.createElement('tr');
      
      const tdTopic = document.createElement('td');
      tdTopic.textContent = topicName;
      tdTopic.style.fontWeight = '600';
      
      const tdCount = document.createElement('td');
      tdCount.textContent = t.count;
      
      const tdCorrect = document.createElement('td');
      tdCorrect.textContent = t.correct;
      
      const tdHints = document.createElement('td');
      tdHints.textContent = t.hints;
      
      const tdMastery = document.createElement('td');
      tdMastery.className = 'mono-num';
      tdMastery.textContent = masteryMap[topicName] || '0%';
      
      tr.appendChild(tdTopic);
      tr.appendChild(tdCount);
      tr.appendChild(tdCorrect);
      tr.appendChild(tdHints);
      tr.appendChild(tdMastery);
      tbody.appendChild(tr);
    });
    
    // Clear session so it's fresh next time
    sessionStorage.removeItem('quiz_session');
    
    document.querySelector('.container').id = 'summary-container';
    switchState('summary-container', 'loaded');
  } catch(err) {
    console.error(err);
    document.querySelector('.container').id = 'summary-container';
    switchState('summary-container', 'loaded');
  }
});
