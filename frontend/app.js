const API_BASE = '/api';

// For MVP, we auto-create/fetch a default student
let currentUser = null;

async function getOrCreateStudent() {
    let studentId = localStorage.getItem('student_id');
    if (!studentId) {
        const res = await fetch(`${API_BASE}/students`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: 'Demo Student' })
        });
        const data = await res.json();
        studentId = data.student_id;
        localStorage.setItem('student_id', studentId);
    }
    currentUser = studentId;
    return studentId;
}

// DASHBOARD LOGIC
async function initDashboard() {
    const studentId = await getOrCreateStudent();
    
    // Load Revision
    try {
        const revRes = await fetch(`${API_BASE}/revision/${studentId}`);
        const revData = await revRes.json();
        renderRevision(revData.revision);
    } catch (e) {
        console.error(e);
        document.getElementById('revision-list').innerHTML = '<p class="error-text">Failed to load revision data.</p>';
    }
    
    // Load Analytics
    try {
        const anRes = await fetch(`${API_BASE}/analytics/${studentId}`);
        const anData = await anRes.json();
        renderAnalytics(anData);
    } catch (e) {
        console.error(e);
    }
    
    document.getElementById('start-quiz-btn').addEventListener('click', () => {
        window.location.href = '/quiz';
    });
}

function renderRevision(revisionList) {
    const container = document.getElementById('revision-list');
    if (!revisionList || revisionList.length === 0) {
        container.innerHTML = '<div class="topic-item"><p>Ready to start! Your first question awaits.</p></div>';
        return;
    }
    
    container.innerHTML = '';
    revisionList.slice(0, 5).forEach(item => {
        const div = document.createElement('div');
        div.className = `topic-item ${item.is_due ? 'due' : item.is_weak ? 'weak' : 'strong'}`;
        
        let status = 'Review';
        if (item.is_due) status = 'Due for Review';
        else if (item.is_weak) status = 'Weak Topic';
        else status = 'Strong';
        
        div.innerHTML = `
            <div>
                <strong>${item.topic}</strong>
                <div class="reason-text">${status}</div>
            </div>
            <div>${(item.mastery_level * 100).toFixed(0)}%</div>
        `;
        container.appendChild(div);
    });
}

function renderAnalytics(data) {
    const mc = document.getElementById('mastery-chart');
    const pl = document.getElementById('performance-list');
    
    // Mastery
    if (data.mastery.length === 0) {
        mc.innerHTML = '<p class="reason-text">No mastery data yet. Start practicing!</p>';
    } else {
        mc.innerHTML = '';
        data.mastery.forEach(m => {
            const pct = m.mastery_level * 100;
            const statusClass = pct < 40 ? 'weak' : pct > 80 ? 'strong' : '';
            mc.innerHTML += `
                <div class="mastery-row">
                    <div class="mastery-label">${m.topic}</div>
                    <div class="mastery-bar-container">
                        <div class="mastery-bar ${statusClass}" style="width: ${pct}%"></div>
                    </div>
                    <div>${pct.toFixed(0)}%</div>
                </div>
            `;
        });
    }
    
    // Performance
    if (data.recent_performance.length === 0) {
        pl.innerHTML = '<p class="reason-text">No recent performance logs.</p>';
    } else {
        pl.innerHTML = '';
        data.recent_performance.forEach(p => {
            const date = new Date(p.timestamp).toLocaleDateString();
            pl.innerHTML += `
                <div class="topic-item" style="border-left-color: ${p.correct ? 'var(--success-color)' : 'var(--error-color)'}; margin-bottom: 0.5rem; padding: 0.75rem;">
                    <div><strong>${p.topic}</strong> (${p.difficulty})</div>
                    <div>${p.correct ? '✓ Correct' : '✗ Incorrect'} ${p.hint_used ? '(Hint)' : ''}</div>
                </div>
            `;
        });
    }
}

// QUIZ LOGIC
let currentQuestionId = null;
let selectedOption = null;
let attemptCount = 1;

async function initQuiz() {
    const studentId = await getOrCreateStudent();
    fetchNextQuestion(studentId);
    
    document.getElementById('submit-btn').addEventListener('click', () => submitAnswer(studentId));
    document.getElementById('next-btn').addEventListener('click', () => {
        resetQuizUI();
        fetchNextQuestion(studentId);
    });
}

async function fetchNextQuestion(studentId) {
    document.getElementById('loading-state').classList.remove('hidden');
    document.getElementById('question-state').classList.add('hidden');
    document.getElementById('error-state').classList.add('hidden');
    document.getElementById('submit-btn').classList.remove('hidden');
    document.getElementById('next-btn').classList.add('hidden');
    
    try {
        const res = await fetch(`${API_BASE}/next_question/${studentId}`);
        const data = await res.json();
        
        if (data.status === 'success') {
            displayQuestion(data.question, data.reason);
        } else {
            throw new Error(data.message);
        }
    } catch (e) {
        console.error(e);
        document.getElementById('loading-state').classList.add('hidden');
        document.getElementById('error-state').classList.remove('hidden');
    }
}

function displayQuestion(question, reason) {
    currentQuestionId = question.id;
    attemptCount = 1;
    
    document.getElementById('current-topic-badge').textContent = question.topic;
    document.getElementById('q-difficulty').textContent = question.difficulty;
    document.getElementById('question-text').textContent = question.question_text;
    document.getElementById('selection-reason').textContent = reason;
    
    const container = document.getElementById('options-container');
    container.innerHTML = '';
    
    question.options.forEach((opt, index) => {
        const btn = document.createElement('button');
        btn.className = 'option-btn';
        btn.textContent = opt;
        btn.dataset.value = opt;
        btn.addEventListener('click', () => selectOption(btn));
        container.appendChild(btn);
    });
    
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('question-state').classList.remove('hidden');
}

function selectOption(btn) {
    if (btn.classList.contains('disabled')) return;
    
    document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    selectedOption = btn.dataset.value;
    document.getElementById('submit-btn').disabled = false;
}

async function submitAnswer(studentId) {
    if (!selectedOption) return;
    
    const submitBtn = document.getElementById('submit-btn');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Evaluating...';
    
    try {
        const res = await fetch(`${API_BASE}/answer/${studentId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                question_id: currentQuestionId,
                answer: selectedOption,
                attempt_count: attemptCount
            })
        });
        const data = await res.json();
        
        handleFeedback(data);
    } catch (e) {
        console.error(e);
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Answer';
    }
}

function handleFeedback(data) {
    const feedbackBox = document.getElementById('feedback-container');
    feedbackBox.classList.remove('hidden', 'correct', 'incorrect');
    
    const selectedBtn = document.querySelector('.option-btn.selected');
    
    if (data.status === 'completed') {
        // Final state
        document.querySelectorAll('.option-btn').forEach(b => b.classList.add('disabled'));
        document.getElementById('submit-btn').classList.add('hidden');
        document.getElementById('next-btn').classList.remove('hidden');
        
        if (data.is_correct) {
            feedbackBox.classList.add('correct');
            feedbackBox.innerHTML = `<h4>Correct!</h4><p>${data.feedback}</p>`;
            if(selectedBtn) selectedBtn.classList.add('correct');
        } else {
            feedbackBox.classList.add('incorrect');
            feedbackBox.innerHTML = `<h4>Incorrect.</h4><p>${data.explanation || data.feedback}</p>`;
            if(selectedBtn) selectedBtn.classList.add('incorrect');
        }
    } else if (data.status === 'retry') {
        // Socratic Hint state
        feedbackBox.classList.add('incorrect');
        feedbackBox.innerHTML = `<h4>Think again (Hint):</h4><p>${data.feedback}</p>`;
        
        if(selectedBtn) {
            selectedBtn.classList.remove('selected');
            selectedBtn.classList.add('incorrect', 'disabled');
        }
        
        selectedOption = null;
        attemptCount++;
        
        const submitBtn = document.getElementById('submit-btn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submit Answer';
    }
}

function resetQuizUI() {
    document.getElementById('feedback-container').classList.add('hidden');
    document.getElementById('submit-btn').textContent = 'Submit Answer';
    document.getElementById('submit-btn').disabled = true;
}
