// --- Lógica de priorización de convocatorias ---
const misConvocatorias = {
  ids: new Set(),
  total: 0,
  max: 20,
  loaded: false,
};

async function cargarMisConvocatorias() {
  const jwt = localStorage.getItem('jwt');
  if (!jwt) return;
  try {
    const res = await fetch('/mis-convocatorias', {
      headers: { 'Authorization': 'Bearer ' + jwt }
    });
    if (res.ok) {
      const data = await res.json();
      misConvocatorias.ids = new Set(data.map(x => x.id_oferta));
      misConvocatorias.total = data.length;
      misConvocatorias.loaded = true;
    }
  } catch {}
}

function renderStarBtn(id_oferta) {
  const priorizada = misConvocatorias.ids.has(id_oferta);
  return `<button class="star-btn" title="${priorizada ? 'Quitar de mis convocatorias' : 'Agregar a mis convocatorias'}" data-star-id="${id_oferta}">
    <svg class="star-icon${priorizada ? ' priorizada' : ''}" viewBox="0 0 24 24" fill="none" stroke="currentColor">
      <polygon points="12,2 15,9 22,9.3 17,14.1 18.5,21 12,17.5 5.5,21 7,14.1 2,9.3 9,9"/>
    </svg>
  </button>`;
}

function showMisConvocModal({modo, id_oferta, onConfirm}) {
  // modo: 'agregar' | 'quitar'
  let msg = '', title = '', btnMain = '', btnGhost = '';
  if (modo === 'agregar') {
    title = 'Agregar a mis convocatorias';
    msg = `¿Desea agregar a su lista priorizada? Puede registrar hasta 20. Va registrando <b>${misConvocatorias.total}</b> de 20.`;
    btnMain = 'Agregar';
    btnGhost = 'Cancelar';
  } else {
    title = 'Quitar de mis convocatorias';
    msg = '¿Desea quitar de su lista priorizada?';
    btnMain = 'Quitar';
    btnGhost = 'Cancelar';
  }
  const modal = document.createElement('div');
  modal.className = 'modal-misconv';
  modal.innerHTML = `
    <div class="modal-misconv-content">
      <h3>${title}</h3>
      <p>${msg}</p>
      <div class="modal-actions">
        <button class="btn-main">${btnMain}</button>
        <button class="btn-ghost">${btnGhost}</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  modal.querySelector('.btn-main').onclick = () => {
    onConfirm();
    document.body.removeChild(modal);
  };
  modal.querySelector('.btn-ghost').onclick = () => {
    document.body.removeChild(modal);
  };
}

async function agregarMisConvocatoria(id_oferta) {
  const jwt = localStorage.getItem('jwt');
  if (!jwt) return;
  const res = await fetch(`/mis-convocatorias/${id_oferta}`, {
    method: 'POST',
    headers: { 'Authorization': 'Bearer ' + jwt }
  });
  if (res.ok) {
    misConvocatorias.ids.add(id_oferta);
    misConvocatorias.total++;
    return true;
  }
  return false;
}

async function quitarMisConvocatoria(id_oferta) {
  const jwt = localStorage.getItem('jwt');
  if (!jwt) return;
  const res = await fetch(`/mis-convocatorias/${id_oferta}`, {
    method: 'DELETE',
    headers: { 'Authorization': 'Bearer ' + jwt }
  });
  if (res.ok) {
    misConvocatorias.ids.delete(id_oferta);
    misConvocatorias.total--;
    return true;
  }
  return false;
}
