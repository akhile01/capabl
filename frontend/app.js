const API_BASE = '/api';

// For MVP, we auto-create/fetch a default student
let currentUser = null;
const DEFAULT_STUDENT_NAME = 'Student';

function getSubject() {
    return localStorage.getItem('subject') || 'Unknown';
}

function getStudentName() {
    return localStorage.getItem('student_name') || DEFAULT_STUDENT_NAME;
}

function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
}

function quizUrlForTopic(topic) {
    return topic ? `/quiz?topic=${encodeURIComponent(topic)}` : '/quiz';
}

async function getOrCreateStudent() {
    let studentId = localStorage.getItem('student_id');
    if (!studentId) {
        const name = getStudentName();
        const res = await fetch(`${API_BASE}/students`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ name })
        });
        if (!res.ok) throw new Error(`Could not create student (HTTP ${res.status})`);
        const data = await res.json();
        studentId = data.student_id;
        localStorage.setItem('student_id', studentId);
        localStorage.setItem('student_name', name);
    }
    currentUser = studentId;
    return studentId;
}

// DASHBOARD LOGIC
async function initDashboard() {
    const studentId = await getOrCreateStudent();
    
    // Set Student Name 
    const heroName = document.getElementById('hero-name');
    if (heroName) heroName.textContent = getStudentName();
    const avatar = document.getElementById('nav-avatar');
    if (avatar) avatar.textContent = getStudentName().charAt(0).toUpperCase();
    
    const subjectParam = `?subject=${encodeURIComponent(getSubject())}`;
    
    // Load Revision
    try {
        const revRes = await fetch(`${API_BASE}/revision/${studentId}${subjectParam}`);
        const revData = await revRes.json();
        renderRevision(revData.revision);
    } catch (e) {
        console.error(e);
        document.getElementById('revision-list').innerHTML = '<div class="editorial-row">Failed to load revision data.</div>';
    }
    
    // Load Analytics
    try {
        const anRes = await fetch(`${API_BASE}/analytics/${studentId}${subjectParam}`);
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
        const startBtn = document.getElementById('rec-start-btn');
        if (startBtn) startBtn.onclick = () => window.location.href = quizUrlForTopic(rec.topic);
        const viewBtn = document.getElementById('rec-view-btn');
        if (viewBtn) viewBtn.onclick = () => window.location.href = `/questions?topic=${encodeURIComponent(rec.topic)}`;
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
        document.getElementById('rec-topic').textContent = 'Your first adaptive session';
        document.getElementById('rec-mastery').textContent = '0%';
        const recStatus = document.querySelector('.panel-status');
        if (recStatus) { recStatus.textContent = 'NEW'; recStatus.className = 'panel-status status-weak'; }
        document.getElementById('rec-desc').textContent = 'No topic history yet. Start practicing and the orchestrator will begin tracking your mastery.';
        document.getElementById('stat-due').textContent = '0';
        const viewBtn = document.getElementById('rec-view-btn');
        if (viewBtn) viewBtn.onclick = () => window.location.href = '/questions';
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
            <div class="row-title">${escapeHtml(item.topic)}</div>
            <div class="row-status ${statusClass}">${status}</div>
            <div class="row-mastery">${(item.mastery_level * 100).toFixed(0)}%</div>
            <div class="row-diff">MIXED</div>
            <div class="row-action" role="button" tabindex="0">REVIEW &rarr;</div>
        `;
        const action = div.querySelector('.row-action');
        action.onclick = () => window.location.href = quizUrlForTopic(item.topic);
        action.onkeydown = (e) => { if (e.key === 'Enter' || e.key === ' ') action.onclick(); };
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
                        <span class="mastery-title">${escapeHtml(m.topic)}</span>
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
                    <div class="row-title">${escapeHtml(p.topic)}</div>
                    <div class="row-diff">${escapeHtml((p.difficulty || '').toUpperCase())}</div>
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
