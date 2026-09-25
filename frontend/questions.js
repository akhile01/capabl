// questions.js
// Handles the Question Bank frontend logic

document.addEventListener('DOMContentLoaded', () => {
    initQuestions();
});

let questionBank = [];
let filteredQuestions = [];

async function initQuestions() {
    renderSkeletons();
    await fetchQuestions();
}

function renderSkeletons() {
    const list = document.getElementById('qb-list');
    list.innerHTML = '';
    
    // Create 5-7 skeleton rows
    for (let i = 0; i < 6; i++) {
        const div = document.createElement('div');
        div.className = 'qb-row skeleton';
        div.innerHTML = `
            <div class="q-text-col skeleton-bg">████████████████████████████</div>
            <div class="q-subject-col skeleton-bg">████████</div>
            <div class="q-topic-col skeleton-bg">████████</div>
            <div class="q-diff-col skeleton-bg">████</div>
            <div class="q-status-col skeleton-bg">██████</div>
            <div class="q-date-col skeleton-bg">████</div>
            <div class="q-action-col skeleton-bg">→</div>
        `;
        list.appendChild(div);
    }
}

async function fetchQuestions() {
    document.getElementById('qb-error').classList.add('hidden');
    document.getElementById('qb-list').classList.remove('hidden');
    
    try {
        const studentId = localStorage.getItem('student_id') || 'unknown';
        // Note: The /api/questions endpoint is expected to return the list of generated questions and attempts
        const res = await fetch(`/api/questions/${studentId}`);
        
        if (!res.ok) {
            throw new Error('Questions API unavailable');
        }
        
        const data = await res.json();
        questionBank = data.questions || [];
        
        if (questionBank.length === 0) {
            showEmptyState();
        } else {
            populateFilters(questionBank);
            applyFilters();
            renderAnalytics(questionBank);
        }
    } catch (e) {
        console.error(e);
        showErrorState();
    }
}

function showEmptyState() {
    document.getElementById('qb-list').classList.add('hidden');
    document.getElementById('qb-empty').classList.remove('hidden');
    document.getElementById('qb-error').classList.add('hidden');
    document.getElementById('qb-no-results').classList.add('hidden');
    updateAnalyticsEmpty();
}

function showErrorState() {
    document.getElementById('qb-list').classList.add('hidden');
    document.getElementById('qb-empty').classList.add('hidden');
    document.getElementById('qb-error').classList.remove('hidden');
    document.getElementById('qb-no-results').classList.add('hidden');
    updateAnalyticsEmpty();
}

function showNoResultsState() {
    document.getElementById('qb-list').classList.add('hidden');
    document.getElementById('qb-empty').classList.add('hidden');
    document.getElementById('qb-error').classList.add('hidden');
    document.getElementById('qb-no-results').classList.remove('hidden');
}

function updateAnalyticsEmpty() {
    document.getElementById('stat-total').textContent = '—';
    document.getElementById('stat-attempted').textContent = '—';
    document.getElementById('stat-accuracy').textContent = '—';
    document.getElementById('stat-review').textContent = '—';
    
    document.querySelectorAll('.stat-val').forEach(el => el.classList.remove('skeleton'));
}

function renderAnalytics(questions) {
    const total = questions.length;
    let attempted = 0;
    let correct = 0;
    let review = 0;
    
    questions.forEach(q => {
        if (q.status && q.status !== 'unattempted') {
            attempted++;
            if (q.status === 'correct') correct++;
            if (q.status === 'review' || q.status === 'incorrect') review++;
        }
    });
    
    const accuracy = attempted > 0 ? ((correct / attempted) * 100).toFixed(0) + '%' : '—';
    
    const setStat = (id, val) => {
        const el = document.getElementById(id);
        el.textContent = val;
        el.classList.remove('skeleton');
    };
    
    setStat('stat-total', total);
    setStat('stat-attempted', attempted);
    setStat('stat-accuracy', accuracy);
    setStat('stat-review', review > 0 ? review : '—');
}

function populateFilters(questions) {
    const subjects = new Set();
    const topics = new Set();
    const diffs = new Set();
    const statuses = new Set();
    
    questions.forEach(q => {
        if (q.subject) subjects.add(q.subject);
        if (q.topic) topics.add(q.topic);
        if (q.difficulty) diffs.add(q.difficulty);
        if (q.status) statuses.add(q.status);
    });
    
    const fillSelect = (id, set, defaultText) => {
        const sel = document.getElementById(id);
        sel.innerHTML = `<option value="">${defaultText} ▾</option>`;
        Array.from(set).sort().forEach(val => {
            const opt = document.createElement('option');
            opt.value = val;
            opt.textContent = val.toUpperCase();
            sel.appendChild(opt);
        });
        sel.classList.remove('skeleton-bg');
    };
    
    fillSelect('filter-subject', subjects, 'All Subjects');
    fillSelect('filter-topic', topics, 'All Topics');
    fillSelect('filter-diff', diffs, 'Difficulty');
    fillSelect('filter-status', statuses, 'Status');
    
    document.getElementById('filter-sort').innerHTML = `
        <option value="recent">Sort: Recent ▾</option>
        <option value="oldest">Sort: Oldest ▾</option>
        <option value="difficulty">Sort: Difficulty ▾</option>
        <option value="unattempted">Sort: Unattempted ▾</option>
    `;
    document.getElementById('filter-sort').classList.remove('skeleton-bg');
    
    // Add event listeners
    document.getElementById('qb-search').addEventListener('input', applyFilters);
    document.querySelectorAll('.filter-select').forEach(sel => {
        sel.addEventListener('change', applyFilters);
    });
}

function applyFilters() {
    const query = document.getElementById('qb-search').value.toLowerCase();
    const subj = document.getElementById('filter-subject').value;
    const topic = document.getElementById('filter-topic').value;
    const diff = document.getElementById('filter-diff').value;
    const stat = document.getElementById('filter-status').value;
    const sort = document.getElementById('filter-sort').value || 'recent';
    
    filteredQuestions = questionBank.filter(q => {
        const textMatch = !query || 
            (q.question_text && q.question_text.toLowerCase().includes(query)) ||
            (q.id && q.id.toLowerCase().includes(query)) ||
            (q.topic && q.topic.toLowerCase().includes(query));
            
        const subjMatch = !subj || q.subject === subj;
        const topicMatch = !topic || q.topic === topic;
        const diffMatch = !diff || q.difficulty === diff;
        const statMatch = !stat || q.status === stat;
        
        return textMatch && subjMatch && topicMatch && diffMatch && statMatch;
    });
    
    // Sorting
    filteredQuestions.sort((a, b) => {
        if (sort === 'recent') return new Date(b.date || 0) - new Date(a.date || 0);
        if (sort === 'oldest') return new Date(a.date || 0) - new Date(b.date || 0);
        if (sort === 'unattempted') {
            if (a.status === 'unattempted' && b.status !== 'unattempted') return -1;
            if (a.status !== 'unattempted' && b.status === 'unattempted') return 1;
            return 0;
        }
        if (sort === 'difficulty') {
            const dVal = { 'easy': 1, 'medium': 2, 'hard': 3 };
            return (dVal[b.difficulty] || 0) - (dVal[a.difficulty] || 0);
        }
        return 0;
    });
    
    renderQuestionList();
}

function renderQuestionList() {
    const list = document.getElementById('qb-list');
    list.innerHTML = '';
    
    if (filteredQuestions.length === 0) {
        showNoResultsState();
        return;
    }
    
    document.getElementById('qb-no-results').classList.add('hidden');
    document.getElementById('qb-empty').classList.add('hidden');
    document.getElementById('qb-error').classList.add('hidden');
    list.classList.remove('hidden');
    
    filteredQuestions.forEach(q => {
        const div = document.createElement('div');
        div.className = 'qb-row';
        div.tabIndex = 0;
        div.setAttribute('role', 'button');
        div.setAttribute('aria-label', `View question: ${q.question_text || 'Untitled'}`);
        div.onclick = () => openQuestionDetail(q);
        div.onkeydown = (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                openQuestionDetail(q);
            }
        };
        
        let statusText = '• NOT ATTEMPTED';
        let statusClass = 'unattempted';
        
        if (q.status === 'correct') { statusText = '✓ CORRECT'; statusClass = 'correct'; }
        else if (q.status === 'incorrect') { statusText = '! INCORRECT'; statusClass = 'incorrect'; }
        else if (q.status === 'review') { statusText = '↻ REVIEW'; statusClass = 'review'; }
        
        const dateStr = q.date ? new Date(q.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }).toUpperCase() : '';
        
        div.innerHTML = `
            <div class="q-text-col">${q.question_text || ''}</div>
            <div class="q-subject-col">${q.subject || ''}</div>
            <div class="q-topic-col">${q.topic || ''}</div>
            <div class="q-diff-col">${q.difficulty || ''}</div>
            <div class="q-status-col ${statusClass}">${statusText}</div>
            <div class="q-date-col">${dateStr}</div>
            <div class="q-action-col">VIEW →</div>
        `;
        list.appendChild(div);
    });
}

function openQuestionDetail(q) {
    document.getElementById('qb-list-view').classList.add('hidden');
    document.getElementById('qb-detail-view').classList.remove('hidden');
    
    document.getElementById('detail-id').textContent = q.id || '';
    document.getElementById('detail-subject').textContent = q.subject || '';
    document.getElementById('detail-topic').textContent = q.topic || '';
    document.getElementById('detail-diff').textContent = q.difficulty || '';
    
    document.getElementById('detail-text').textContent = q.question_text || '';
    
    const optsContainer = document.getElementById('detail-options');
    optsContainer.innerHTML = '';
    if (q.options) {
        const labels = ['A', 'B', 'C', 'D', 'E'];
        q.options.forEach((opt, idx) => {
            const optDiv = document.createElement('div');
            optDiv.className = 'detail-option';
            optDiv.innerHTML = `<span class="opt-label">${labels[idx] || ''}</span><span class="opt-text">${opt}</span>`;
            optsContainer.appendChild(optDiv);
        });
    }
    
    // Result State
    const resContainer = document.getElementById('detail-result');
    const unattemptedContainer = document.getElementById('detail-unattempted');
    
    if (q.status && q.status !== 'unattempted') {
        resContainer.classList.remove('hidden');
        unattemptedContainer.classList.add('hidden');
        
        const statusEl = document.getElementById('detail-result-status');
        if (q.status === 'correct') {
            resContainer.className = 'qb-detail-result correct';
            statusEl.textContent = '✓ CORRECT';
        } else {
            resContainer.className = 'qb-detail-result incorrect';
            statusEl.textContent = '! INCORRECT';
        }
        document.getElementById('detail-your-answer').textContent = q.user_answer || 'Unknown';
    } else {
        resContainer.classList.add('hidden');
        unattemptedContainer.classList.remove('hidden');
    }
    
    // Explanation
    const expContainer = document.getElementById('detail-explanation');
    if (q.explanation) {
        expContainer.classList.remove('hidden');
        document.getElementById('detail-explanation-text').textContent = q.explanation;
    } else {
        expContainer.classList.add('hidden');
    }
    
    // Adaptive Context
    const adaptiveContainer = document.getElementById('detail-adaptive');
    if (q.adaptive_reason) {
        adaptiveContainer.classList.remove('hidden');
        document.getElementById('detail-adaptive-reason').textContent = q.adaptive_reason;
    } else {
        adaptiveContainer.classList.add('hidden');
    }
    
    // Source Context
    const sourceContainer = document.getElementById('detail-source');
    if (q.source) {
        sourceContainer.classList.remove('hidden');
        document.getElementById('detail-source-name').textContent = q.source;
    } else {
        sourceContainer.classList.add('hidden');
    }
    
    // Meta
    document.getElementById('detail-type').textContent = q.question_type ? q.question_type.toUpperCase().replace('_', ' ') : 'MULTIPLE CHOICE';
}

function closeDetailView() {
    document.getElementById('qb-detail-view').classList.add('hidden');
    document.getElementById('qb-list-view').classList.remove('hidden');
}

function clearFilters() {
    document.getElementById('qb-search').value = '';
    document.querySelectorAll('.filter-select').forEach(sel => sel.value = '');
    applyFilters();
}

function filterBySubject(subject) {
    document.getElementById('filter-subject').value = subject;
    closeDetailView();
    applyFilters();
}

function filterByTopic(topic) {
    document.getElementById('filter-topic').value = topic;
    closeDetailView();
    applyFilters();
}
