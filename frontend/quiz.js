const API_BASE = '/api';
let studentId = localStorage.getItem('student_id') || 'default';

let state = {
    questionId: null,
    options: [],
    selectedOption: null,
    attemptCount: 1,
    maxAttempts: 3,
    sessionCorrect: 0,
    sessionIncorrect: 0,
    sessionHints: 0,
    questionsAnswered: 0
};

const UI = {
    stateLoading: document.getElementById('state-loading'),
    stateActive: document.getElementById('state-active'),
    stateError: document.getElementById('state-error'),
    btnSubmit: document.getElementById('btn-submit'),
    btnNext: document.getElementById('btn-next'),
    optionsContainer: document.getElementById('q-options'),
    feedbackSuccess: document.getElementById('feedback-success'),
    feedbackFail: document.getElementById('feedback-fail'),
    panelAdaptive: document.getElementById('panel-adaptive'),
    panelSocratic: document.getElementById('panel-socratic'),
    loadingRotator: document.getElementById('loading-rotator')
};

// Keyboard support
document.addEventListener('keydown', (e) => {
    if (UI.stateActive.classList.contains('hidden')) return;
    
    const key = e.key.toUpperCase();
    if (['A', 'B', 'C', 'D'].includes(key) || ['1', '2', '3', '4'].includes(key)) {
        let idx = -1;
        if (['A', 'B', 'C', 'D'].includes(key)) idx = key.charCodeAt(0) - 65;
        if (['1', '2', '3', '4'].includes(key)) idx = parseInt(key) - 1;

        if (idx >= 0 && idx < state.options.length) {
            const optCards = document.querySelectorAll('.opt-card');
            if (optCards[idx] && !optCards[idx].classList.contains('disabled')) {
                selectOption(optCards[idx], state.options[idx]);
            }
        }
    } else if (e.key === 'Enter') {
        if (!UI.btnSubmit.disabled && !UI.btnSubmit.classList.contains('hidden')) {
            submitAnswer();
        }
    } else if (key === 'N') {
        if (!UI.btnNext.classList.contains('hidden')) {
            fetchNextQuestion();
        }
    }
});

async function initQuiz() {
    if (!localStorage.getItem('student_id')) {
        try {
            const res = await fetch(`${API_BASE}/students`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name: 'Rajeev' })
            });
            const data = await res.json();
            studentId = data.student_id;
            localStorage.setItem('student_id', studentId);
        } catch (e) {
            console.warn('Failed to auto-create student');
        }
    }
    
    UI.btnSubmit.addEventListener('click', submitAnswer);
    UI.btnNext.addEventListener('click', fetchNextQuestion);
    
    fetchNextQuestion();
}

const loadingTexts = [
    "Analyzing your mastery...",
    "Selecting the next topic...",
    "Choosing difficulty...",
    "Retrieving a grounded question...",
    "Checking question quality..."
];
let rotatorInterval;

function startLoading() {
    UI.stateError.classList.add('hidden');
    UI.stateActive.classList.add('hidden');
    UI.stateLoading.classList.remove('hidden');
    
    let i = 0;
    UI.loadingRotator.textContent = loadingTexts[0];
    clearInterval(rotatorInterval);
    rotatorInterval = setInterval(() => {
        i = (i + 1) % loadingTexts.length;
        UI.loadingRotator.textContent = loadingTexts[i];
    }, 1200);
}

function stopLoading() {
    clearInterval(rotatorInterval);
    UI.stateLoading.classList.add('hidden');
}

function showError() {
    stopLoading();
    UI.stateActive.classList.add('hidden');
    UI.stateError.classList.remove('hidden');
}

window.retryFetch = fetchNextQuestion;

async function fetchNextQuestion() {
    startLoading();
    state.selectedOption = null;
    state.attemptCount = 1;
    
    try {
        const res = await fetch(`${API_BASE}/next_question/${studentId}`);
        const data = await res.json();
        
        if (data.status === 'success') {
            renderQuestion(data.question, data.reason);
        } else {
            showError();
        }
    } catch (e) {
        console.error(e);
        showError();
    }
}

function renderQuestion(q, reason) {
    stopLoading();
    UI.stateActive.classList.remove('hidden');
    
    // Reset panels
    UI.panelSocratic.classList.add('hidden');
    UI.panelAdaptive.classList.remove('hidden');
    UI.feedbackSuccess.classList.add('hidden');
    UI.feedbackFail.classList.add('hidden');
    
    UI.btnSubmit.classList.remove('hidden');
    UI.btnSubmit.disabled = true;
    UI.btnSubmit.textContent = 'SUBMIT ANSWER \u2192';
    UI.btnNext.classList.add('hidden');
    
    state.questionId = q.id;
    state.options = q.options;
    
    // Header info
    document.getElementById('hdr-subject').textContent = q.topic;
    document.getElementById('hdr-subj-badge').textContent = (q.subject || 'DATABASE SYSTEMS').toUpperCase();
    document.getElementById('hdr-diff').textContent = (q.difficulty || 'MEDIUM').toUpperCase();
    const bloom = q.bloom_level || 'APPLY';
    document.getElementById('hdr-bloom').textContent = `BLOOM: ${bloom.toUpperCase()}`;
    
    const qNum = state.questionsAnswered + 1;
    document.getElementById('hdr-progress-text').textContent = `Q ${qNum.toString().padStart(2, '0')} / 10`;
    document.getElementById('q-num-label').textContent = `QUESTION ${qNum.toString().padStart(2, '0')}`;
    document.getElementById('hdr-progress-bar').style.width = `${(qNum / 10) * 100}%`;
    
    document.getElementById('q-diff-label').textContent = (q.difficulty || 'MEDIUM').toUpperCase();
    document.getElementById('q-bloom-label').textContent = `BLOOM: ${bloom.toUpperCase()}`;
    
    document.getElementById('q-text').textContent = q.question_text;
    
    // Adaptive Intelligence
    document.getElementById('ai-reason').textContent = reason || "Selected because it matches your learning path targets.";
    document.getElementById('ai-diff').textContent = (q.difficulty || 'MEDIUM').toUpperCase();
    // Use an approximate mastery if missing
    document.getElementById('ai-mastery').textContent = "Current"; 
    
    UI.optionsContainer.innerHTML = '';
    const letters = ['A', 'B', 'C', 'D'];
    
    q.options.forEach((opt, idx) => {
        const card = document.createElement('div');
        card.className = 'opt-card';
        card.onclick = () => selectOption(card, opt);
        
        const letter = document.createElement('span');
        letter.className = 'opt-letter';
        letter.textContent = letters[idx] || (idx+1);
        
        const text = document.createElement('span');
        text.textContent = opt;
        
        card.appendChild(letter);
        card.appendChild(text);
        UI.optionsContainer.appendChild(card);
    });
    
    updateSessionSummary();
}

function selectOption(card, optValue) {
    if (card.classList.contains('disabled') || card.classList.contains('locked')) return;
    
    document.querySelectorAll('.opt-card').forEach(c => {
        if (!c.classList.contains('locked')) {
            c.classList.remove('selected');
        }
    });
    
    card.classList.add('selected');
    state.selectedOption = optValue;
    
    UI.btnSubmit.disabled = false;
}

async function submitAnswer() {
    if (!state.selectedOption) return;
    
    UI.btnSubmit.disabled = true;
    UI.btnSubmit.textContent = 'EVALUATING...';
    
    try {
        const res = await fetch(`${API_BASE}/answer/${studentId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                question_id: state.questionId,
                answer: state.selectedOption,
                attempt_count: state.attemptCount
            })
        });
        const data = await res.json();
        handleEvaluation(data);
    } catch (e) {
        console.error(e);
        UI.btnSubmit.disabled = false;
        UI.btnSubmit.textContent = 'SUBMIT ANSWER \u2192';
        alert("Error submitting answer.");
    }
}

function handleEvaluation(data) {
    const selectedCards = document.querySelectorAll('.opt-card.selected');
    const selectedCard = selectedCards.length > 0 ? selectedCards[0] : null;
    
    if (data.status === 'retry') {
        state.sessionHints++;
        state.sessionIncorrect++;
        
        if (selectedCard) {
            selectedCard.classList.remove('selected');
            selectedCard.classList.add('locked', 'wrong', 'disabled');
            const icon = document.createElement('span');
            icon.className = 'opt-status-icon';
            icon.textContent = '✗';
            selectedCard.appendChild(icon);
        }
        
        state.selectedOption = null;
        state.attemptCount++;
        
        UI.panelAdaptive.classList.add('hidden');
        UI.panelSocratic.classList.remove('hidden');
        
        document.getElementById('socratic-hint-text').textContent = data.feedback;
        document.getElementById('socratic-attempt').textContent = `${state.attemptCount} / ${state.maxAttempts}`;
        
        UI.btnSubmit.disabled = true;
        UI.btnSubmit.textContent = 'SUBMIT ANSWER \u2192';
        
    } else if (data.status === 'completed') {
        state.questionsAnswered++;
        
        document.querySelectorAll('.opt-card').forEach(c => c.classList.add('disabled', 'locked'));
        
        UI.btnSubmit.classList.add('hidden');
        UI.btnNext.classList.remove('hidden');
        
        if (data.is_correct) {
            state.sessionCorrect++;
            if (selectedCard) {
                selectedCard.classList.remove('selected');
                selectedCard.classList.add('correct');
                const icon = document.createElement('span');
                icon.className = 'opt-status-icon';
                icon.textContent = '✓';
                selectedCard.appendChild(icon);
            }
            
            UI.feedbackSuccess.classList.remove('hidden');
            document.getElementById('fb-success-text').textContent = data.feedback || "Correct!";
            document.getElementById('fb-success-exp').textContent = data.explanation || "";
            
        } else {
            state.sessionIncorrect++;
            if (selectedCard) {
                selectedCard.classList.remove('selected');
                selectedCard.classList.add('wrong');
                const icon = document.createElement('span');
                icon.className = 'opt-status-icon';
                icon.textContent = '✗';
                selectedCard.appendChild(icon);
            }
            
            UI.panelAdaptive.classList.add('hidden');
            UI.panelSocratic.classList.add('hidden');
            UI.feedbackFail.classList.remove('hidden');
            
            document.getElementById('fb-fail-exp').textContent = data.explanation || data.feedback;
            document.getElementById('fb-fail-answer').textContent = "Review the explanation above for details."; 
        }
    }
    
    updateSessionSummary();
}

function updateSessionSummary() {
    document.getElementById('sess-count').textContent = `${state.questionsAnswered.toString().padStart(2, '0')} / 10`;
    document.getElementById('sess-correct').textContent = state.sessionCorrect;
    document.getElementById('sess-incorrect').textContent = state.sessionIncorrect;
    document.getElementById('sess-hints').textContent = state.sessionHints;
    
    const total = state.sessionCorrect + state.sessionIncorrect;
    const acc = total > 0 ? ((state.sessionCorrect / total) * 100).toFixed(0) : 0;
    document.getElementById('sess-accuracy').textContent = `${acc}%`;
}

document.addEventListener('DOMContentLoaded', initQuiz);
