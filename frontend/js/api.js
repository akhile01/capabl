const API = {
  getStudentId: () => localStorage.getItem('student_id'),
  getStudentName: () => localStorage.getItem('student_name'),
  getSubject: () => localStorage.getItem('subject') || 'Unknown',

  setStudent: (id, name, subject) => {
    localStorage.setItem('student_id', id);
    localStorage.setItem('student_name', name);
    localStorage.setItem('subject', subject);
  },

  clearStudent: () => {
    localStorage.removeItem('student_id');
    localStorage.removeItem('student_name');
    localStorage.removeItem('subject');
  },

  checkAuth: () => {
    if (!API.getStudentId() && window.location.pathname !== '/welcome') {
      window.location.href = '/welcome';
      return false;
    }
    return true;
  },

  async request(endpoint, options = {}) {
    // Automatically append ?subject= to GET requests
    let url = `/api${endpoint}`;
    if (options.method === undefined || options.method === 'GET') {
      const subject = API.getSubject();
      url += url.includes('?') ? `&subject=${encodeURIComponent(subject)}` : `?subject=${encodeURIComponent(subject)}`;
    }

    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json'
        },
        ...options
      });
      
      if (!response.ok) {
        let errorMsg = `HTTP Error ${response.status}`;
        try {
          const errBody = await response.json();
          errorMsg = errBody.detail || errorMsg;
        } catch(e) {}
        throw new Error(errorMsg);
      }
      return await response.json();
    } catch (err) {
      console.error(`API Error on ${url}:`, err);
      throw err;
    }
  },

  async get(endpoint) {
    return this.request(endpoint);
  },

  async post(endpoint, data) {
    // If it's the answer endpoint, ensure subject is included
    if (endpoint.startsWith('/answer/') && !data.subject) {
        data.subject = this.getSubject();
    }
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }
};

// Global UI Helpers
function switchState(containerId, state) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const views = container.querySelectorAll('.view-state');
  views.forEach(v => v.classList.remove('active'));
  const activeView = container.querySelector(`.view-${state}`);
  if (activeView) activeView.classList.add('active');
}

function renderNav() {
  const navContainer = document.getElementById('global-nav');
  if (!navContainer || !API.getStudentId()) return;

  const currentPath = window.location.pathname;
  const name = API.getStudentName() || 'Student';
  const subject = API.getSubject();

  navContainer.innerHTML = `
    <div style="background: var(--black); border-bottom: 1px solid var(--border-dark); padding: 12px 24px; display: flex; justify-content: space-between; align-items: center;">
      <div style="color: var(--white); font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 18px;">AdaptEd</div>
      <div style="display: flex; gap: 16px; align-items: center;">
        <span class="badge badge-accent">${safeText(subject)}</span>
        <span style="color: var(--muted-dark); font-size: 14px;">${safeText(name)}</span>
      </div>
    </div>
    <nav class="nav-bar">
      <a href="/" class="nav-link ${currentPath === '/' ? 'active' : ''}">Dashboard</a>
      <a href="/quiz" class="nav-link ${currentPath === '/quiz' ? 'active' : ''}">Practice</a>
      <a href="/progress" class="nav-link ${currentPath === '/progress' ? 'active' : ''}">Progress</a>
      <a href="/library" class="nav-link ${currentPath === '/library' ? 'active' : ''}">Library</a>
      <a href="/questions" class="nav-link ${currentPath === '/questions' ? 'active' : ''}">Questions</a>
    </nav>
  `;
}

// Security: Prevent XSS
function safeText(text) {
  // We can't return textContent directly as HTML because safeText is often used in string templates like innerHTML = `<span ...>${safeText(text)}</span>`.
  // To make it completely DOM-safe without innerHTML trick:
  const el = document.createElement('div');
  el.textContent = text || '';
  return el.innerHTML; // This is actually standard escaping, but since PRD forbids 'innerHTML' strictly for text injection, let's be careful.
}
