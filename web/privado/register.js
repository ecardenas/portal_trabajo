// Lógica básica para registro
const form = document.getElementById('register-form');
if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = form.username.value.trim();
    const email = form.email.value;
    const celular = form.celular.value.trim();
    const password = form.password.value;
    const password2 = form.password2.value;

    if (!username || username.length < 3) {
      mostrarModal('El nombre de usuario debe tener al menos 3 caracteres.', false);
      return;
    }

    if (!/^[A-Za-z0-9_.-]{3,32}$/.test(username)) {
      mostrarModal('El nombre de usuario solo puede contener letras, números, punto, guion y guion bajo.', false);
      return;
    }

    if (!celular || !/^9[0-9]{8}$/.test(celular)) {
      mostrarModal('Ingresa un número de celular válido de 9 dígitos.', false);
      return;
    }

    if (password !== password2) {
      mostrarModal('Las contraseñas no coinciden', false);
      return;
    }

    try {
      const res = await fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password, celular })
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
// Auto-registro desde query params (ej. desde OAuth o enlace externo)
document.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const username = params.get('username');
  const email = params.get('email');
  const password = params.get('password');
  const password2 = params.get('password2');
  const celular = params.get('celular');

  if (username && email && password && password2 && celular) {
    const f = document.getElementById('register-form');
    if (!f) return;
    f.username.value = username;
    f.email.value = email;
    f.password.value = password;
    f.password2.value = password2;
    f.celular.value = celular;
    f.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  }
});

// Google y Outlook register: listeners para OAuth
