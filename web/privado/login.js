// Lógica básica para login
const form = document.getElementById('login-form');
if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = form.email.value;
    const password = form.password.value;
    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (res.ok && data.access_token) {
        localStorage.setItem('jwt', data.access_token);
        window.location.href = 'index.html';
      } else {
        alert(data.detail || 'Error de autenticación');
      }
    } catch (err) {
      alert('Error de red o servidor');
    }
  });
}
// Google y Outlook login: listeners para OAuth
