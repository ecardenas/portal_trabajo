const form = document.getElementById('login-form');
const emailInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const emailError = document.getElementById('loginEmailError');
const passwordError = document.getElementById('loginPasswordError');
const formError = document.getElementById('loginFormError');
const submitBtn = document.getElementById('loginSubmitBtn');

function setFieldError(input, errorNode, message) {
  const wrap = input?.closest('.register-input-wrap');
  if (!errorNode || !wrap) return;
  errorNode.textContent = message || '';
  errorNode.classList.toggle('is-hidden', !message);
  wrap.classList.toggle('has-error', !!message);
}

function clearFormError() {
  if (!formError) return;
  formError.textContent = '';
  formError.classList.add('is-hidden');
}

function setFormError(message) {
  if (!formError) return;
  formError.textContent = message;
  formError.classList.remove('is-hidden');
}

function validateLoginFields() {
  const email = emailInput.value.trim();
  const password = passwordInput.value;
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  let isValid = true;
  clearFormError();

  if (!email) {
    setFieldError(emailInput, emailError, 'Ingresa tu correo electrónico.');
    isValid = false;
  } else if (!emailPattern.test(email)) {
    setFieldError(emailInput, emailError, 'Ingresa un correo electrónico válido.');
    isValid = false;
  } else {
    setFieldError(emailInput, emailError, '');
  }

  if (!password) {
    setFieldError(passwordInput, passwordError, 'Ingresa tu contraseña.');
    isValid = false;
  } else if (password.length < 6) {
    setFieldError(passwordInput, passwordError, 'La contraseña debe tener al menos 6 caracteres.');
    isValid = false;
  } else {
    setFieldError(passwordInput, passwordError, '');
  }

  return isValid;
}

if (emailInput) {
  emailInput.addEventListener('input', () => setFieldError(emailInput, emailError, ''));
}

if (passwordInput) {
  passwordInput.addEventListener('input', () => setFieldError(passwordInput, passwordError, ''));
}

if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!validateLoginFields()) {
      return;
    }

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    submitBtn.disabled = true;
    submitBtn.textContent = 'Validando...';
    clearFormError();

    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await res.json().catch(() => ({}));

      if (res.ok && data.access_token) {
        localStorage.setItem('jwt', data.access_token);
        window.location.href = 'index.html';
        return;
      }

      setFormError(data.detail || 'No se pudo iniciar sesión. Verifica tus credenciales.');
    } catch (err) {
      setFormError('No fue posible conectar con el servidor. Inténtalo nuevamente.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Ingresar';
    }
  });
}
