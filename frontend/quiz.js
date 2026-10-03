// NOTE: API_BASE is declared in app.js, which quiz.html loads before this file.
// Re-declaring it here threw "Identifier 'API_BASE' has already been declared"
// and prevented this whole script from running (no buttons worked).
let studentId = localStorage.getItem('student_id') || 'default';
const SESSION_LENGTH = 10;
const urlParams = new URLSearchParams(window.location.search);
const requestedTopic = urlParams.get('topic');
let sessionComplete = false;

function currentSubject() {
    return (typeof getSubject === 'function') ? getSubject() : (localStorage.getItem('subject') || 'Unknown');
}

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
    try {
        studentId = await getOrCreateStudent();
    } catch (e) {
        console.warn('Failed to auto-create student', e);
    }
    sessionStorage.removeItem('quiz_session');
    
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

function showError(message) {
    stopLoading();
    UI.stateActive.classList.add('hidden');
    UI.stateError.classList.remove('hidden');
    const detail = document.getElementById('error-detail');
    if (detail) detail.textContent = message || '';
}

window.retryFetch = fetchNextQuestion;

async function fetchNextQuestion() {
    if (sessionComplete) {
        window.location.href = '/quiz/summary';
        return;
    }
    startLoading();
    state.selectedOption = null;
    state.attemptCount = 1;
    
    try {
        const params = new URLSearchParams({ subject: currentSubject() });
        if (requestedTopic) params.set('topic', requestedTopic);
        const res = await fetch(`${API_BASE}/next_question/${studentId}?${params.toString()}`);
        const data = await res.json();
        
        if (res.ok && data.status === 'success') {
            renderQuestion(data.question, data.reason, data.mastery);
        } else {
            showError(data.detail || data.message || 'The server could not provide a question.');
        }
    } catch (e) {
        console.error(e);
        showError('Could not reach the server. Check that the backend is running.');
    }
}

function renderQuestion(q, reason, mastery) {
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
    document.getElementById('hdr-subj-badge').textContent = (q.subject || currentSubject()).toUpperCase();
    document.getElementById('hdr-diff').textContent = (q.difficulty || 'MEDIUM').toUpperCase();
    const bloom = q.bloom_level || 'APPLY';
    document.getElementById('hdr-bloom').textContent = `BLOOM: ${bloom.toUpperCase()}`;
    
    const qNum = state.questionsAnswered + 1;
    document.getElementById('hdr-progress-text').textContent = `Q ${qNum.toString().padStart(2, '0')} / ${SESSION_LENGTH}`;
    document.getElementById('q-num-label').textContent = `QUESTION ${qNum.toString().padStart(2, '0')}`;
    document.getElementById('hdr-progress-bar').style.width = `${Math.min(100, (qNum / SESSION_LENGTH) * 100)}%`;
    
    document.getElementById('q-diff-label').textContent = (q.difficulty || 'MEDIUM').toUpperCase();
    document.getElementById('q-bloom-label').textContent = `BLOOM: ${bloom.toUpperCase()}`;
    
    document.getElementById('q-text').textContent = q.question_text;
    
    // Adaptive Intelligence
    document.getElementById('ai-reason').textContent = reason || "Selected because it matches your learning path targets.";
    document.getElementById('ai-diff').textContent = (q.difficulty || 'MEDIUM').toUpperCase();
    // Use an approximate mastery if missing
    document.getElementById('ai-mastery').textContent = (typeof mastery === 'number') ? `${Math.round(mastery * 100)}%` : '--%';
    document.getElementById('ai-status').textContent = requestedTopic ? 'SELECTED' : ((typeof mastery === 'number' && mastery < 0.6) ? 'WEAK' : 'DUE');
    
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
                attempt_count: state.attemptCount,
                subject: currentSubject()
            })
        });
        const data = await res.json();
        if (!res.ok || data.status === 'error') {
            throw new Error(data.detail || data.message || 'Evaluation failed');
        }
        handleEvaluation(data);
    } catch (e) {
        console.error(e);
        UI.btnSubmit.disabled = false;
        UI.btnSubmit.textContent = 'SUBMIT ANSWER \u2192';
        if (window.showToast) window.showToast('SUBMISSION FAILED', e.message, 'error');
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
        recordSessionEntry(data.is_correct, state.attemptCount > 1);
        
        document.querySelectorAll('.opt-card').forEach(c => c.classList.add('disabled', 'locked'));
        
        UI.btnSubmit.classList.add('hidden');
        UI.btnNext.classList.remove('hidden');
        if (state.questionsAnswered >= SESSION_LENGTH) {
            sessionComplete = true;
            UI.btnNext.textContent = 'VIEW SESSION SUMMARY \u2192';
        } else {
            UI.btnNext.textContent = 'NEXT QUESTION \u2192';
        }
        
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

function recordSessionEntry(isCorrect, hintUsed) {
    try {
        const log = JSON.parse(sessionStorage.getItem('quiz_session') || '[]');
        log.push({
            question_id: state.questionId,
            topic: document.getElementById('hdr-subject').textContent,
            correct: !!isCorrect,
            hint_used: !!hintUsed
        });
        sessionStorage.setItem('quiz_session', JSON.stringify(log));
    } catch (e) {
        console.warn('Could not persist session log', e);
    }
}

function updateSessionSummary() {
    document.getElementById('sess-count').textContent = `${state.questionsAnswered.toString().padStart(2, '0')} / ${SESSION_LENGTH}`;
    document.getElementById('sess-correct').textContent = state.sessionCorrect;
    document.getElementById('sess-incorrect').textContent = state.sessionIncorrect;
    document.getElementById('sess-hints').textContent = state.sessionHints;
    
    const total = state.sessionCorrect + state.sessionIncorrect;
    const acc = total > 0 ? ((state.sessionCorrect / total) * 100).toFixed(0) : 0;
    document.getElementById('sess-accuracy').textContent = `${acc}%`;
}

document.addEventListener('DOMContentLoaded', initQuiz);
