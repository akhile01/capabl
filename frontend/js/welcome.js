document.addEventListener('DOMContentLoaded', async () => {
  if (API.getStudentId()) {
    window.location.href = '/';
    return;
  }

  const form = document.getElementById('onboarding-form');
  const btn = form.querySelector('button');

  // Load subjects dynamically later (Phase 2 requirement), for now it's free text.
  
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('student-name').value.trim();
    const subject = document.getElementById('subject-select').value.trim() || 'Unknown';
    
    if (!name) return;

    btn.disabled = true;
    btn.textContent = 'Setting up...';

    try {
      const data = await API.post('/students', { name });
      API.setStudent(data.student_id, data.name, subject);
      window.location.href = '/';
    } catch (err) {
      alert('Failed to create student: ' + err.message);
      btn.disabled = false;
      btn.textContent = 'Start learning';
    }
  });
});
