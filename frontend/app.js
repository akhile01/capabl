const API_BASE = '/api';

// For MVP, we auto-create/fetch a default student
let currentUser = null;

async function getOrCreateStudent() {
    let studentId = localStorage.getItem('student_id');
    if (!studentId) {
        const res = await fetch(`${API_BASE}/students`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name: 'Rajeev' })
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
    
    // Set Student Name 
    const heroName = document.getElementById('hero-name');
    if (heroName) heroName.textContent = 'Rajeev';
    
    // Load Revision
    try {
        const revRes = await fetch(`${API_BASE}/revision/${studentId}`);
        const revData = await revRes.json();
        renderRevision(revData.revision);
    } catch (e) {
        console.error(e);
        document.getElementById('revision-list').innerHTML = '<div class="editorial-row">Failed to load revision data.</div>';
    }
    
    // Load Analytics
    try {
        const anRes = await fetch(`${API_BASE}/analytics/${studentId}`);
        const anData = await anRes.json();
        renderAnalytics(anData);
    } catch (e) {
        console.error(e);
    }
}

function renderRevision(revisionList) {
    const container = document.getElementById('revision-list');
    
    // Update Hero Recommendation
    if (revisionList && revisionList.length > 0) {
        const rec = revisionList[0];
        document.getElementById('rec-topic').textContent = rec.topic;
        document.getElementById('rec-mastery').textContent = `${(rec.mastery_level * 100).toFixed(0)}%`;
        
        const recStatus = document.querySelector('.panel-status');
        if (rec.is_due) {
            recStatus.textContent = 'DUE FOR REVIEW';
            recStatus.className = 'panel-status status-due';
            document.getElementById('rec-desc').textContent = 'Your orchestrator selected this topic because it is currently weak and due for revision.';
        } else if (rec.is_weak) {
            recStatus.textContent = 'WEAK TOPIC';
            recStatus.className = 'panel-status status-weak';
            document.getElementById('rec-desc').textContent = 'Your orchestrator selected this topic because it is below your mastery target.';
        } else {
            recStatus.textContent = 'STRONG TOPIC';
            recStatus.className = 'panel-status status-strong';
            document.getElementById('rec-desc').textContent = 'Your orchestrator selected this topic to reinforce your strong knowledge.';
        }
        
        // Update Due Today stat
        const dueCount = revisionList.filter(r => r.is_due).length;
        document.getElementById('stat-due').textContent = dueCount;
    }

    if (!revisionList || revisionList.length === 0) {
        container.innerHTML = '<div class="editorial-row">Ready to start! Your first question awaits.</div>';
        return;
    }
    
    container.innerHTML = '';
    revisionList.slice(0, 5).forEach((item, index) => {
        let status = 'REVIEW';
        let statusClass = '';
        if (item.is_due) { status = 'DUE'; statusClass = 'due'; }
        else if (item.is_weak) { status = 'WEAK'; statusClass = 'weak'; }
        else { status = 'STRONG'; statusClass = 'strong'; }
        
        const div = document.createElement('div');
        div.className = 'editorial-row';
        div.innerHTML = `
            <div class="row-num">0${index + 1}</div>
            <div class="row-title">${item.topic}</div>
            <div class="row-status ${statusClass}">${status}</div>
            <div class="row-mastery">${(item.mastery_level * 100).toFixed(0)}%</div>
            <div class="row-diff">MIXED</div>
            <div class="row-action" onclick="window.location.href='/quiz'">REVIEW &rarr;</div>
        `;
        container.appendChild(div);
    });
}

function renderAnalytics(data) {
    // Mastery Overview
    const mc = document.getElementById('mastery-list');
    let totalMastery = 0;
    let masteredCount = 0;
    
    if (data.mastery.length === 0) {
        mc.innerHTML = '<div class="editorial-row">No mastery data yet. Start practicing!</div>';
        document.getElementById('stat-mastery').textContent = '0%';
        document.getElementById('stat-mastered').textContent = '0 / 0';
    } else {
        mc.innerHTML = '';
        data.mastery.slice(0, 5).forEach(m => {
            const pct = m.mastery_level * 100;
            totalMastery += pct;
            if (m.mastery_level >= 0.8) masteredCount++;
            
            mc.innerHTML += `
                <div class="mastery-item">
                    <div class="mastery-top">
                        <span class="mastery-title">${m.topic}</span>
                        <span class="mastery-pct">${pct.toFixed(0)}%</span>
                    </div>
                    <div class="mastery-bar-wrap">
                        <div class="mastery-fill" style="width: ${pct}%"></div>
                    </div>
                </div>
            `;
        });
        
        document.getElementById('stat-mastery').textContent = `${(totalMastery / data.mastery.length).toFixed(0)}%`;
        document.getElementById('stat-mastered').textContent = `${masteredCount} / ${data.mastery.length}`;
    }
    
    // Recent Performance
    const pl = document.getElementById('performance-list');
    let correctCount = 0;
    
    if (data.recent_performance.length === 0) {
        pl.innerHTML = '<div class="editorial-row">No recent performance logs.</div>';
        document.getElementById('stat-accuracy').textContent = '0%';
        renderTrend([]);
    } else {
        pl.innerHTML = '';
        data.recent_performance.slice(0, 5).forEach((p, i) => {
            if (p.correct) correctCount++;
            const timeStr = 'Recent'; 
            pl.innerHTML += `
                <div class="editorial-row perf-row">
                    <div class="row-title">${p.topic}</div>
                    <div class="row-diff">${p.difficulty.toUpperCase()}</div>
                    <div class="row-status ${p.correct ? 'strong' : 'weak'}">${p.correct ? '✓ Correct' : '✗ Incorrect'}</div>
                    <div class="row-status">${p.hint_used ? 'Hint used' : 'No hint'}</div>
                    <div class="row-status" style="text-align: right;">${timeStr}</div>
                </div>
            `;
        });
        
        const accuracy = (correctCount / Math.min(data.recent_performance.length, 5)) * 100;
        document.getElementById('stat-accuracy').textContent = `${accuracy.toFixed(0)}%`;
        
        renderTrend(data.recent_performance.slice(0, 7));
    }
}

function renderTrend(performances) {
    const viz = document.getElementById('trend-viz');
    if (!viz) return;
    viz.innerHTML = '';
    
    // Reverse to chronological
    const chron = [...performances].reverse();
    const count = Math.max(7, chron.length);
    
    for (let i = 0; i < 7; i++) {
        const bar = document.createElement('div');
        bar.className = 'trend-bar';
        if (i >= 7 - chron.length) {
            const p = chron[i - (7 - chron.length)];
            bar.style.height = p.correct ? '100%' : '30%';
            if (i === 6) bar.classList.add('latest');
        } else {
            bar.style.height = '10%'; // empty filler
        }
        viz.appendChild(bar);
    }
}

// Keep Quiz logic unchanged for quiz.html
let currentQuestionId = null;
let selectedOption = null;
let attemptCount = 1;

async function initQuiz() {
    const studentId = await getOrCreateStudent();
    fetchNextQuestion(studentId);
    
    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
        submitBtn.addEventListener('click', () => submitAnswer(studentId));
    }
    
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            resetQuizUI();
            fetchNextQuestion(studentId);
        });
    }
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

// --- GLOBAL TOAST SYSTEM ---
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('toast-container')) {
        const container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }
});

window.showToast = function(title, desc = '', type = 'default') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = '●';
    if (type === 'success') icon = '✓';
    else if (type === 'error') icon = '!';
    else if (type === 'warning') icon = '↻';
    
    toast.innerHTML = `
        <div class="toast-icon">${icon}</div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            ${desc ? `<div class="toast-desc">${desc}</div>` : ''}
        </div>
        <button class="toast-close">&times;</button>
    `;
    
    container.appendChild(toast);
    
    // Animate in
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });
    
    // Close button
    toast.querySelector('.toast-close').onclick = () => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    };
    
    // Auto dismiss
    setTimeout(() => {
        if (toast.parentNode) {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
}
