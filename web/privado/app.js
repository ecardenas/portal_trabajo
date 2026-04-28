// Skeleton de carga para el modal de detalle (igual que público)
function renderDetailSkeleton() {
  $("dPuesto").innerHTML = `<span class="skeleton skeleton-text w-320"></span>`;
  $("detalleBody").innerHTML = `
    <section class="detail-summary-grid">
      <div class="mini-stat"><span class="skeleton skeleton-text w-80"></span><strong><span class="skeleton skeleton-text w-120"></span></strong></div>
      <div class="mini-stat"><span class="skeleton skeleton-text w-80"></span><strong><span class="skeleton skeleton-text w-80"></span></strong></div>
      <div class="mini-stat"><span class="skeleton skeleton-text w-80"></span><strong><span class="skeleton skeleton-text w-80"></span></strong></div>
      <div class="mini-stat"><span class="skeleton skeleton-text w-80"></span><strong><span class="skeleton skeleton-text w-120"></span></strong></div>
    </section>
    <div class="detail-layout">
      <div class="detail-column">
        <section class="detail-section-card"><div class="detail-section-head"><h4>Información general</h4></div><div class="detail-grid"><span class="skeleton skeleton-text w-180"></span><span class="skeleton skeleton-text w-180"></span><span class="skeleton skeleton-text w-180"></span><span class="skeleton skeleton-text w-180"></span></div></section>
      </div>
      <div class="detail-column">
        <section class="detail-section-card"><div class="detail-section-head"><h4>Perfil del puesto</h4></div><div class="detail-grid"><span class="skeleton skeleton-text w-180"></span><span class="skeleton skeleton-text w-180"></span><span class="skeleton skeleton-text w-180"></span></div></section>
      </div>
    </div>
  `;
}

// Utilidad para resaltar texto filtrado (igual que público)
function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, function (c) {
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c];
  });
}

function highlightText(text, filter) {
  if (!filter) return escapeHtml(text);
  const re = new RegExp(`(${filter.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return escapeHtml(text).replace(re, '<span class="highlight">$1</span>');
}

function makeDetailItem(label, value, type = "text", full = false, filter = "") {
  if (!value && value !== 0) return "";
  const fullClass = full ? "detail-item-full" : "";
  if (type === "link") {
    const safeUrl = escapeHtml(value);
    return `
      <div class="detail-item ${fullClass}">
        <span class="detail-label">${label}</span>
        <div class="detail-value"><a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${safeUrl}</a></div>
      </div>
    `;
  }
  return `
    <div class="detail-item ${fullClass}">
      <span class="detail-label">${label}</span>
      <div class="detail-value">${highlightText(value, filter)}</div>
    </div>
  `;
}
// Renderiza la flecha de orden en la columna activa
function renderOrdenarFlecha() {
  document.querySelectorAll('th.sortable').forEach(th => {
    const span = th.querySelector('.sort-ind');
    if (!span) return;
    if (th.dataset.sort === state.sortBy) {
      span.textContent = state.sortOrder === 'asc' ? '▲' : '▼';
      span.style.opacity = 1;
    } else {
      span.textContent = '';
      span.style.opacity = 0.3;
    }
  });
}
// Utilidades básicas copiadas de la versión pública para consistencia
const money = (v) => (v || v === 0 ? `S/${Number(v).toLocaleString("es-PE")}` : "-");

function parseDate(dmy) {
  if (!dmy || typeof dmy !== "string") return null;
  const parts = dmy.split("/");
  if (parts.length !== 3) return null;
  const [d, m, y] = parts.map(Number);
  if (!d || !m || !y) return null;
  return new Date(y, m - 1, d);
}

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function diffDays(fromDate, toDate) {
  const ms = startOfDay(toDate) - startOfDay(fromDate);
  return Math.round(ms / 86400000);
}

function formatDate(dmy) {
  const dt = parseDate(dmy);
  if (!dt) return dmy || "-";
  return dt.toLocaleDateString("es-PE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
// Muestra un mensaje de error debajo del input correspondiente
function showInputError(id, msg) {
  const input = document.getElementById(id);
  if (!input) return;
  let errorElem = input.parentNode.querySelector('.input-error');
  if (!errorElem) {
    errorElem = document.createElement('div');
    errorElem.className = 'input-error';
    errorElem.style.color = '#d32f2f';
    errorElem.style.fontSize = '0.9em';
    errorElem.style.marginTop = '2px';
    input.parentNode.appendChild(errorElem);
  }
  errorElem.textContent = msg || '';
  errorElem.style.display = msg ? 'block' : 'none';
}
function isAlphaWithSpaces(str) {
  // Solo letras y espacios, sin tildes ni números ni caracteres especiales
  return /^[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ ]+$/.test(str);
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

function buildQuery() {
  let puesto = $("q").value.trim();
  let ubicacion = $("ubicacion").value.trim();
  let carrera = $("carrera") ? $("carrera").value.trim() : "";
  let especializacion = $("especializacion") ? $("especializacion").value.trim() : "";
  let entidad = $("entidad") ? $("entidad").value.trim() : "";
  let remVal = $("remVal") ? $("remVal").value.trim() : "";
  let remOp = $("remOp") ? $("remOp").value.trim() : "gte";
  let situacion = $("situacion") ? $("situacion").value.trim() : "todos";

  // Limpiar errores previos
  showInputError("puesto", "");
  showInputError("ubicacion", "");
  let valid = true;

  // Validar longitud mínima y solo letras/espacios
  if (puesto.length > 0) {
    if (puesto.length < 5) {
      showInputError("puesto", "Ingrese mínimo 5 letras (solo texto)");
      valid = false;
    } else if (!isAlphaWithSpaces(puesto)) {
      showInputError("puesto", "Solo letras y espacios permitidos");
      valid = false;
    }
  }
  if (ubicacion.length > 0) {
    if (ubicacion.length < 3) {
      showInputError("ubicacion", "Ingrese mínimo 3 letras (solo texto)");
      valid = false;
    } else if (!isAlphaWithSpaces(ubicacion)) {
      showInputError("ubicacion", "Solo letras y espacios permitidos");
      valid = false;
    }
  }
  if (carrera.length > 0 && carrera.length < 3) {
    showInputError("carrera", "Ingrese mínimo 3 letras");
    valid = false;
  }
  if (especializacion.length > 0 && especializacion.length < 3) {
    showInputError("especializacion", "Ingrese mínimo 3 letras");
    valid = false;
  }
  if (entidad.length > 0 && entidad.length < 2) {
    showInputError("entidad", "Ingrese mínimo 2 letras");
    valid = false;
  }
  if (remVal && isNaN(Number(remVal))) {
    showInputError("remVal", "Ingrese un valor numérico válido");
    valid = false;
  }

  if (!valid) return null;

  const params = new URLSearchParams();
  params.set("pagina", state.page);
  params.set("limite", state.limit);
  params.set("ordenar_por", state.sortBy);
  params.set("orden", state.sortOrder);
  params.set("solo_30", "true");

  if (puesto) params.set("q", puesto);
  if (ubicacion) params.set("ubicacion", ubicacion);
  if (carrera) params.set("carrera", carrera);
  if (especializacion) params.set("especializacion", especializacion);
  if (entidad) params.set("entidad", entidad);
  if (remVal) params.set("remVal", remVal);
  if (remOp) params.set("remOp", remOp);
  if (situacion && situacion !== "todos") params.set("situacion", situacion);

  return `/buscar?${params.toString()}`;
}

const state = {
  page: 1,
  limit: 20,
  totalPages: 1,
  totalRecords: 0,
  sortBy: "fecha_fin",
  sortOrder: "asc",
  loading: false,
};

function getActiveFiltersCount() {
  let count = 0;
    ["q", "ubicacion", "carrera", "especializacion", "entidad", "remVal"].forEach((id) => {
    const el = $(id);
    if (el && el.value.trim()) count += 1;
  });
  return count;
}

function renderActiveFiltersChip() {
  const count = getActiveFiltersCount();
  const chip = $("activeFiltersChip");
  if (!chip) return;

  if (count > 0) {
    chip.textContent = `Filtros activos (${count})`;
    chip.classList.remove("is-hidden");
  } else {
    chip.classList.add("is-hidden");
  }
}

window.renderActiveFiltersChip = renderActiveFiltersChip;
const $ = (id) => document.getElementById(id);

function formatDate(dmy) {
  const dt = parseDate(dmy);
  if (!dt) return dmy || "-";
  return dt.toLocaleDateString("es-PE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}
function diffDays(fromDate, toDate) {
  const ms = startOfDay(toDate) - startOfDay(fromDate);
  return Math.round(ms / 86400000);
}
function isVigente(fechaFin) {
  const dt = parseDate(fechaFin);
  if (!dt) return false;
  const now = new Date();
  const today = startOfDay(now);
  return startOfDay(dt) >= today;
}
function getOfferTags(item) {
  if (!isVigente(item.fecha_fin)) return [];
  const today = startOfDay(new Date());
  const fechaFin = parseDate(item.fecha_fin);
  const fechaInicio = parseDate(item.fecha_inicio);
  const tags = [];
  if (fechaFin) {
    const daysToClose = diffDays(today, fechaFin);
    if (daysToClose === 0) {
      tags.push({ key: "vence-hoy", label: "Vence hoy", cls: "tag-danger" });
    } else if (daysToClose > 0 && daysToClose <= 7) {
      tags.push({ key: "vence-pronto", label: "Vence pronto", cls: "tag-warn" });
    }
  }
  if (fechaInicio) {
    const daysSincePublished = diffDays(fechaInicio, today);
    if (daysSincePublished >= 0 && daysSincePublished <= 3) {
      tags.push({ key: "nuevo", label: "Nuevo", cls: "tag-info" });
    }
  }
  return tags.slice(0, 2);
}
function renderTags(item) {
  const tags = getOfferTags(item);
  if (!tags.length) return '<span class="tag tag-empty">—</span>';
  return tags
    .map((tag) => `<span class="tag ${tag.cls}">${tag.label}</span>`)
    .join("");
}
function renderRows(items) {
  const tbody = $("tbody");
  tbody.innerHTML = "";
  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;padding:32px;">No se encontraron resultados</td></tr>`;
    return;
  }
  items.forEach((it, index) => {
    const num = (state.page - 1) * state.limit + index + 1;
    const tagsHtml = renderTags(it);
    const tr = document.createElement("tr");
    const id_oferta = it.id_oferta || it.id; // fallback
    // Imagen de detalle
    const imgDetail = `<img src="../img/detail.png" alt="Ver detalle" class="img-detail-btn" data-id="${it.id}" style="cursor:pointer;width:28px;height:28px;" title="Ver detalle" />`;
    // Imagen de priorizada
    let imgStar = '';
    if (typeof misConvocatorias !== 'undefined' && misConvocatorias.ids) {
      const priorizada = misConvocatorias.ids.has(id_oferta);
      imgStar = `<img src="../img/${priorizada ? 'on' : 'off'}.png" alt="${priorizada ? 'Quitar de mis convocatorias' : 'Agregar a mis convocatorias'}" class="img-star-btn" data-star-id="${id_oferta}" style="cursor:pointer;width:28px;height:28px;margin-left:8px;" title="${priorizada ? 'Quitar de mis convocatorias' : 'Agregar a mis convocatorias'}" />`;
    }
    tr.innerHTML = `
      <td>${num}</td>
      <td>${it.puesto || "-"}</td>
      <td>${it.entidad || "-"}</td>
      <td>${it.ubicacion || "-"}</td>
      <td>${money(it.remuneracion)}</td>
      <td>${formatDate(it.fecha_fin)}</td>
      <td><div class="table-tags">${tagsHtml}</div></td>
      <td><span class="action-imgs">${imgDetail}${imgStar}</span></td>
    `;
    tbody.appendChild(tr);
  });
  // Enlazar evento para abrir detalle
  setTimeout(() => {
    document.querySelectorAll('.img-detail-btn').forEach(img => {
      img.onclick = function() {
        if (window.showDetail) window.showDetail(this.dataset.id);
      };
    });
    document.querySelectorAll('.img-star-btn').forEach(img => {
      img.onclick = async function(e) {
        const id_oferta = this.getAttribute('data-star-id');
        const priorizada = misConvocatorias.ids.has(id_oferta);
        if (!priorizada) {
          showMisConvocModal({
            modo: 'agregar',
            id_oferta,
            onConfirm: async () => {
              const ok = await agregarMisConvocatoria(id_oferta);
              if (ok) {
                await cargarMisConvocatorias();
                runSearch();
              }
            }
          });
        } else {
          showMisConvocModal({
            modo: 'quitar',
            id_oferta,
            onConfirm: async () => {
              const ok = await quitarMisConvocatoria(id_oferta);
              if (ok) {
                await cargarMisConvocatorias();
                runSearch();
              }
            }
          });
        }
      };
    });
  }, 0);
}

function updateResultsMeta(total) {
  state.totalRecords = total;
  const from = total === 0 ? 0 : (state.page - 1) * state.limit + 1;
  const to = Math.min(state.page * state.limit, total);
  $("totalResultados").textContent = `${total.toLocaleString("es-PE")} registro${total === 1 ? "" : "s"}`;
  $("resultsRange").textContent = total === 0
    ? "Sin resultados"
    : `Mostrando ${from} - ${to} de ${total.toLocaleString("es-PE")}`;
  $("pageInfo").textContent = `Página ${state.page} de ${state.totalPages}`;
  // Lógica idéntica a la pública: solo deshabilitar si loading o fuera de rango
  const prevBtn = $("prev");
  const nextBtn = $("next");
  if (prevBtn) prevBtn.disabled = state.loading || state.page <= 1;
  if (nextBtn) nextBtn.disabled = state.loading || state.page >= state.totalPages;
}

async function runSearch(options = {}) {
  console.log('[DEBUG] runSearch: page', state.page, 'limit', state.limit, 'sortBy', state.sortBy, 'sortOrder', state.sortOrder);
  state.loading = true;
  $("btnBuscar").disabled = true;
  $("btnBuscar").innerHTML = `<span class="btn-spinner" aria-hidden="true"></span><span>Buscando...</span>`;
  $("tbody").innerHTML = `<tr><td colspan="10" style="text-align:center;padding:32px;">Buscando...</td></tr>`;
  updateResultsMeta(0);
  let total = 0;
  try {
    const data = await fetchJSON(buildQuery());
    const items = data.ofertas || [];
    total = data.total || 0;
    state.totalPages = Math.max(1, Math.ceil(total / state.limit));
    console.log('[DEBUG] total:', total, 'state.totalPages:', state.totalPages, 'state.page:', state.page);
    renderRows(items);
    renderOrdenarFlecha();
    if (options.scrollResultados) {
      const resultadosTitle = document.querySelector('.results-panel .section-title');
      if (resultadosTitle) {
        resultadosTitle.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
    renderActiveFiltersChip();
  } catch (e) {
    $("tbody").innerHTML = `<tr><td colspan="10" style="text-align:center;padding:32px;">Error cargando resultados: ${e.message}</td></tr>`;
    total = 0;
  } finally {
    state.loading = false;
    updateResultsMeta(total);
    $("btnBuscar").disabled = false;
    $("btnBuscar").innerHTML = `<span>Buscar</span>`;
  }
}

function resetFilters() {
  ["q", "carrera", "especializacion", "ubicacion", "entidad", "remVal"].forEach((id) => {
    $(id).value = "";
    showInputError(id, "");
  });
  $("remOp").value = "gte";
  if ($("situacion")) $("situacion").value = "todos";
  state.page = 1;
  runSearch();
  renderActiveFiltersChip();
}

function bindEvents() {
  // Tooltips
  document.querySelectorAll('.help-icon-btn').forEach(btn => {
    btn.addEventListener('focus', function() {
      this.querySelector('.tooltip').style.display = 'block';
    });
    btn.addEventListener('blur', function() {
      this.querySelector('.tooltip').style.display = 'none';
    });
    btn.addEventListener('mouseenter', function() {
      this.querySelector('.tooltip').style.display = 'block';
    });
    btn.addEventListener('mouseleave', function() {
      this.querySelector('.tooltip').style.display = 'none';
    });
  });
  // Ordenar al hacer clic en columnas
  document.querySelectorAll("th.sortable").forEach((th) => {
    th.addEventListener("click", () => {
      const field = th.dataset.sort;
      if (state.sortBy === field) {
        state.sortOrder = state.sortOrder === "asc" ? "desc" : "asc";
      } else {
        state.sortBy = field;
        state.sortOrder = field === "fecha_inicio" ? "desc" : "asc";
      }
      state.page = 1;
      runSearch(true);
    });
  });
  renderOrdenarFlecha();
  $("btnBuscar").addEventListener("click", () => {
    state.page = 1;
    runSearch({ scrollResultados: false });
  });
  $("btnLimpiar").addEventListener("click", resetFilters);
  $("prev").addEventListener("click", function () {
    if (state.loading) return;
    if (state.page > 1) {
      state.page -= 1;
      console.log('[DEBUG] Botón Anterior: page', state.page);
      runSearch({ scrollResultados: true });
    }
  });
  $("next").addEventListener("click", function () {
    if (state.loading) return;
    if (state.page < state.totalPages) {
      state.page += 1;
      console.log('[DEBUG] Botón Siguiente: page', state.page);
      runSearch({ scrollResultados: true });
    }
  });
  // Modal de detalle de convocatoria (igual que público)
  async function showDetail(id) {
    const dialog = $("detalleDialog");
    if (!dialog) return;
    renderDetailSkeleton();
    dialog.showModal();
    try {
      const d = await fetchJSON(`/ofertas/${id}`);
      $("dPuesto").textContent = d.puesto || "Detalle de oferta";
      const tagsHtml = renderTags(d);
      const filtroPuesto = $("q")?.value.trim();
      const filtroUbicacion = $("ubicacion")?.value.trim();
      const summary = `
        <section class="detail-summary-grid">
          <div class="mini-stat"><span>Remuneración</span><strong>${money(d.remuneracion)}</strong></div>
          <div class="mini-stat"><span>Vacantes</span><strong>${d.vacantes ?? "-"}</strong></div>
          <div class="mini-stat"><span>Estado</span><strong>${isVigente(d.fecha_fin) ? "Vigente" : "Cerrada"}</strong></div>
          <div class="mini-stat"><span>Vigencia</span><strong>${formatDate(d.fecha_inicio)} - ${formatDate(d.fecha_fin)}</strong></div>
        </section>
        <div class="detail-tags-bar">
          ${tagsHtml}
        </div>
      `;
      const generalItems = [
        makeDetailItem("Entidad", d.entidad),
        makeDetailItem("Ubicación", d.ubicacion, "text", false, filtroUbicacion),
        makeDetailItem("Número de convocatoria", d.numero_convocatoria),
        makeDetailItem("Link de postulación", d.link_postulacion, "link", true),
      ];
      const profileItems = [
        makeDetailItem("Formación", d.formacion, "text", true, filtroPuesto),
        makeDetailItem("Experiencia", d.experiencia, "text", true),
        makeDetailItem("Especialización", d.especializacion, "text", true),
        makeDetailItem("Conocimiento", d.conocimiento, "text", true),
        makeDetailItem("Competencias", d.competencias, "text", true),
      ];
      const desktopLayout = `
        <div class="detail-layout">
          <div class="detail-column">
            <section class="detail-section-card">
              <div class="detail-section-head"><h4>Información general</h4></div>
              <div class="detail-grid">${generalItems.filter(Boolean).join("")}</div>
            </section>
          </div>
          <div class="detail-column">
            <section class="detail-section-card">
              <div class="detail-section-head"><h4>Perfil del puesto</h4></div>
              <div class="detail-grid">${profileItems.filter(Boolean).join("")}</div>
            </section>
          </div>
        </div>
      `;
      const mobileAccordion = `
        <div class="detail-accordion">
          <details open>
            <summary>Resumen</summary>
            <div class="detail-accordion-body">
              ${makeDetailItem("Remuneración", money(d.remuneracion))}
              ${makeDetailItem("Vacantes", d.vacantes ?? "-")}
              ${makeDetailItem("Estado", isVigente(d.fecha_fin) ? "Vigente" : "Cerrada")}
              ${makeDetailItem("Vigencia", `${formatDate(d.fecha_inicio)} - ${formatDate(d.fecha_fin)}`)}
            </div>
          </details>
          <details>
            <summary>Información general</summary>
            <div class="detail-accordion-body">${generalItems.filter(Boolean).join("")}</div>
          </details>
          <details>
            <summary>Perfil del puesto</summary>
            <div class="detail-accordion-body">
              ${makeDetailItem("Formación", d.formacion, "text", true, filtroPuesto)}
              ${makeDetailItem("Experiencia", d.experiencia, "text", true)}
              ${makeDetailItem("Especialización", d.especializacion, "text", true)}
            </div>
          </details>
          <details>
            <summary>Conocimientos y competencias</summary>
            <div class="detail-accordion-body">
              ${makeDetailItem("Conocimiento", d.conocimiento, "text", true)}
              ${makeDetailItem("Competencias", d.competencias, "text", true)}
            </div>
          </details>
          <details>
            <summary>Postulación</summary>
            <div class="detail-accordion-body">
              ${makeDetailItem("Link de postulación", d.link_postulacion, "link", true)}
            </div>
          </details>
        </div>
      `;
      $("detalleBody").innerHTML = summary + desktopLayout + mobileAccordion;
    } catch (e) {
      $("detalleBody").innerHTML = `<strong>No se pudo cargar el detalle</strong>`;
    }
  }
  window.showDetail = showDetail;
  if (document.getElementById('cerrarDetalle')) {
    document.getElementById('cerrarDetalle').onclick = () => {
      document.getElementById('detalleDialog').close();
    };
  }
  document.querySelectorAll(".filter-control").forEach((el) => {
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        state.page = 1;
        runSearch(true);
      }
    });
    el.addEventListener("input", renderActiveFiltersChip);
    el.addEventListener("change", renderActiveFiltersChip);
  });
  if ($("situacion")) $("situacion").addEventListener("change", renderActiveFiltersChip);
}

function renderFiltrosAvanzados() {
  // Ya está en el HTML, solo enlazar eventos y tooltips
  bindEvents();
  renderActiveFiltersChip();
}

window.renderActiveFiltersChip = renderActiveFiltersChip;

// Inicializar todo al cargar
document.addEventListener('DOMContentLoaded', async () => {
  // Autenticación y usuario
  const jwt = localStorage.getItem('jwt');
  if (!jwt) {
    window.location.href = 'login.html';
    return;
  }
  let user = null;
  try {
    const res = await fetch('/auth/me', {
      headers: { 'Authorization': 'Bearer ' + jwt }
    });
    if (res.ok) {
      user = (await res.json()).user;
    } else {
      throw new Error('No autorizado');
    }
  } catch {
    localStorage.removeItem('jwt');
    window.location.href = 'login.html';
    return;
  }
  // Mostrar usuario en hero
  const userInfo = document.getElementById('userInfo');
  userInfo.style.display = 'flex';
  document.getElementById('userName').textContent = user.email || user.name || 'Usuario';
  // Menú usuario
  const userMenuBtn = document.getElementById('userMenuBtn');
  const userDropdown = document.getElementById('userDropdown');
  userMenuBtn.onclick = (e) => {
    e.stopPropagation();
    userDropdown.style.display = userDropdown.style.display === 'block' ? 'none' : 'block';
  };
  document.body.onclick = () => { userDropdown.style.display = 'none'; };
  document.getElementById('btnCerrarSesion').onclick = () => {
    localStorage.removeItem('jwt');
    window.location.href = '/static/index.html';
  };
  document.getElementById('btnActualizarDatos').onclick = () => {
    alert('Funcionalidad próximamente');
  };
  // Obtener monto máximo para validación de remuneración
  try {
    const stats = await fetchJSON('/estadisticas?solo_30=false');
    state.montoMaximo = stats.remuneracion_maxima || 0;
  } catch {}
  // Cargar priorizadas y luego renderizar
  await cargarMisConvocatorias();
  renderFiltrosAvanzados();
  setTimeout(() => runSearch(), 100);
});
