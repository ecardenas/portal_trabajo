// Lógica básica para registro
const form = document.getElementById('register-form');
if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = form.email.value;
    const password = form.password.value;
    const password2 = form.password2.value;
    if (password !== password2) {
      mostrarModal('Las contraseñas no coinciden', false);
      return;
    }
    try {
      const res = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (res.ok) {
        mostrarModal('¡Registro exitoso! Ahora puedes iniciar sesión.', true);
      } else {
        mostrarModal(data.detail || 'Error en el registro', false);
      }
    } catch (err) {
      mostrarModal('Error de red o servidor', false);
    }
  });
}

function mostrarModal(mensaje, exito) {
  const modal = document.getElementById('modalRegistro');
  if (!modal) return;
  modal.style.display = 'flex';
  const h3 = modal.querySelector('h3');
  const p = modal.querySelector('p');
  const btn = document.getElementById('btnIrLogin');
  if (exito) {
    h3.textContent = '¡Registro exitoso!';
    p.textContent = 'Ahora puedes iniciar sesión.';
    btn.style.display = 'block';
  } else {
    h3.textContent = 'Error';
    p.textContent = mensaje;
    btn.style.display = 'none';
  }
}

const btnIrLogin = document.getElementById('btnIrLogin');
if (btnIrLogin) {
  btnIrLogin.onclick = () => {
    window.location.href = 'login.html';
  };
}
// Google y Outlook register: listeners para OAuth
