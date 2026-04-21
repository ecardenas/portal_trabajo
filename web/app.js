
// Responsive: ocultar filtros y forzar estado vigentes en móvil
function isMobile() {
  return window.innerWidth < 768;
}

function ajustarFiltrosPorDispositivo() {
  // Ocultar filtros en móvil
  const estadoField = document.querySelector('.field.hide-mobile label[for="estado"]')?.parentElement || document.querySelector('.field label[for="estado"]')?.parentElement;
  const especField = document.querySelector('.field.hide-mobile label[for="especializacion"]')?.parentElement || document.querySelector('.field label[for="especializacion"]')?.parentElement;
  if (isMobile()) {
    if (estadoField) estadoField.style.display = 'none';
    if (especField) especField.style.display = 'none';
    // Forzar estado vigentes
    const estadoSel = document.getElementById('estado');
    if (estadoSel) estadoSel.value = 'vigentes';
  } else {
    if (estadoField) estadoField.style.display = '';
    if (especField) especField.style.display = '';
  }
}

window.addEventListener('resize', ajustarFiltrosPorDispositivo);
window.addEventListener('DOMContentLoaded', ajustarFiltrosPorDispositivo);

// Estado global (debe ir antes de cualquier uso)
const state = {
  page: 1,
  limit: 20,
  totalPages: 1,
  totalRecords: 0,
  sortBy: "fecha_inicio",
  sortOrder: "desc",
  loading: false,
};

// Ordenamiento móvil: alternar asc/desc tocando el mismo campo
const ordenarSel = document.getElementById('ordenar');
if (ordenarSel) {
  ordenarSel.addEventListener('change', function() {
    if (state.sortBy === this.value) {
      // Alternar sentido
      state.sortOrder = state.sortOrder === 'asc' ? 'desc' : 'asc';
    } else {
      state.sortBy = this.value;
      state.sortOrder = 'desc'; // Por defecto descendente
    }
    state.page = 1;
    renderOrdenarFlecha();
    buscar();
  });
  // Mostrar flecha visual
  function renderOrdenarFlecha() {
    const sel = document.getElementById('ordenar');
    if (!sel) return;
    let flecha = state.sortOrder === 'asc' ? '↑' : '↓';
    sel.style.backgroundImage = `none`;
    sel.nextElementSibling && (sel.nextElementSibling.textContent = '');
    // Agrega la flecha al label
    const label = sel.parentElement.parentElement.querySelector('label');
    if (label) {
      label.innerHTML = `Ordenar por <span style='font-size:18px;vertical-align:middle;'>${flecha}</span>`;
    }
  }
  renderOrdenarFlecha();
}

const $ = (id) => document.getElementById(id);
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

function isVigente(fechaFin) {
  const dt = parseDate(fechaFin);
  if (!dt) return false;
  const now = new Date();
  const today = startOfDay(now);
  return startOfDay(dt) >= today;
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function buildQuery() {
  const q = $("q").value.trim();
  const carrera = $("carrera").value.trim();
  const especializacion = $("especializacion").value.trim();
  const ubicacion = $("ubicacion").value.trim();
  const entidad = $("entidad").value.trim();
  const remOp = $("remOp").value;
  const remVal = $("remVal").value.trim();
  const estado = $("estado").value;

  const params = new URLSearchParams();
  params.set("pagina", state.page);
  params.set("limite", state.limit);
  params.set("ordenar_por", state.sortBy);
  params.set("orden", state.sortOrder);

  if (q) params.set("q", q);
  if (carrera) params.set("carrera", carrera);
  if (especializacion) params.set("especializacion", especializacion);
  if (ubicacion) params.set("ubicacion", ubicacion);
  if (entidad) params.set("entidad", entidad);
  if (remVal) {
    params.set("remuneracion", remVal);
    params.set("remuneracion_op", remOp);
  }
  if (estado !== "todos") params.set("estado", estado);

  return `/buscar?${params.toString()}`;
}

function getActiveFiltersCount() {
  let count = 0;
  ["q", "carrera", "especializacion", "ubicacion", "entidad", "remVal"].forEach((id) => {
    if ($(id).value.trim()) count += 1;
  });
  if ($("estado").value !== "todos") count += 1;
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

function syncFiltersCollapseByViewport() {
  const filtersCard = $("filtersCard");
  const toggleBtn = $("toggleFilters");
  if (!filtersCard || !toggleBtn) return;

  if (window.innerWidth < 768) {
    if (!filtersCard.dataset.initializedMobile) {
      filtersCard.classList.add("filters-collapsed");
      filtersCard.dataset.initializedMobile = "true";
    }
  } else {
    filtersCard.classList.remove("filters-collapsed");
  }

  const collapsed = filtersCard.classList.contains("filters-collapsed");
  toggleBtn.textContent = collapsed ? "Mostrar filtros" : "Ocultar filtros";
  toggleBtn.setAttribute("aria-expanded", String(!collapsed));
}

function updateLoading(loading) {
  state.loading = loading;
  document.body.classList.toggle("is-loading", loading);

  if ($("btnBuscar")) {
    $("btnBuscar").disabled = loading;
    $("btnBuscar").innerHTML = loading
      ? `<span class="btn-spinner" aria-hidden="true"></span><span>Buscando...</span>`
      : `<span>Buscar</span>`;
  }

  if ($("btnLimpiar")) $("btnLimpiar").disabled = loading;
  if ($("prev")) $("prev").disabled = loading || state.page <= 1;
  if ($("next")) $("next").disabled = loading || state.page >= state.totalPages;
}

function renderStatsSkeleton() {
  ["sActivas", "sTotal", "sProm", "sMax"].forEach((id) => {
    const el = $(id);
    if (el) el.innerHTML = `<span class="skeleton skeleton-text w-120"></span>`;
  });
}

async function loadStats() {
  renderStatsSkeleton();
  const s = await fetchJSON("/estadisticas");

  $("sActivas").textContent = s.ofertas_vigentes ?? "-";
  $("sTotal").textContent = s.ofertas_total ?? "-";
  $("sProm").textContent = s.remuneracion_promedio ? money(s.remuneracion_promedio) : "-";
  $("sMax").textContent = s.remuneracion_maxima ? money(s.remuneracion_maxima) : "-";
}

function getRowNumber(index) {
  return (state.page - 1) * state.limit + index + 1;
}

function getStatusBadge(fechaFin) {
  return isVigente(fechaFin)
    ? '<span class="status status-ok">Vigente</span>'
    : '<span class="status status-warn">Cerrada</span>';
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
    .map((tag) => `<span class="tag ${tag.cls}">${escapeHtml(tag.label)}</span>`)
    .join("");
}

function renderTableSkeleton(rows = 8) {
  const tbody = $("tbody");
  tbody.innerHTML = "";

  for (let i = 0; i < rows; i++) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="skeleton skeleton-text w-24"></span></td>
      <td><span class="skeleton skeleton-text w-180"></span></td>
      <td><span class="skeleton skeleton-text w-180"></span></td>
      <td><span class="skeleton skeleton-text w-120"></span></td>
      <td><span class="skeleton skeleton-text w-80"></span></td>
      <td><span class="skeleton skeleton-text w-80"></span></td>
      <td><span class="skeleton skeleton-text w-80"></span></td>
      <td><span class="skeleton skeleton-pill"></span></td>
      <td><span class="skeleton skeleton-text w-120"></span></td>
      <td><span class="skeleton skeleton-button"></span></td>
    `;
    tbody.appendChild(tr);
  }

  renderCardsSkeleton(rows);
}

function renderCardsSkeleton(count = 5) {
  const cards = $("cardsResults");
  if (!cards) return;
  cards.innerHTML = "";

  for (let i = 0; i < count; i++) {
    const article = document.createElement("article");
    article.className = "result-card";
    article.innerHTML = `
      <div class="result-card-top">
        <span class="skeleton skeleton-pill small"></span>
        <span class="skeleton skeleton-pill small"></span>
      </div>
      <div class="skeleton skeleton-text w-90"></div>
      <div style="height:8px"></div>
      <div class="skeleton skeleton-text w-75"></div>
      <div style="height:14px"></div>
      <div class="card-meta-grid">
        <span class="skeleton skeleton-text w-80"></span>
        <span class="skeleton skeleton-text w-80"></span>
        <span class="skeleton skeleton-text w-80"></span>
        <span class="skeleton skeleton-text w-80"></span>
      </div>
      <div style="height:10px"></div>
      <div class="card-tags-row">
        <span class="skeleton skeleton-pill small"></span>
        <span class="skeleton skeleton-pill small"></span>
      </div>
      <div style="height:10px"></div>
      <span class="skeleton skeleton-button w-120"></span>
    `;
    cards.appendChild(article);
  }
}

function renderEmptyState(
  message = "No se encontraron resultados",
  detail = "Ajusta los filtros o limpia la búsqueda para ver más ofertas."
) {
  $("tbody").innerHTML = `
    <tr>
      <td colspan="10">
        <div class="empty-state">
          <div class="empty-state-icon">⌕</div>
          <div>
            <strong>${escapeHtml(message)}</strong>
            <p>${escapeHtml(detail)}</p>
          </div>
        </div>
      </td>
    </tr>
  `;

  const cards = $("cardsResults");
  if (cards) {
    cards.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⌕</div>
        <div>
          <strong>${escapeHtml(message)}</strong>
          <p>${escapeHtml(detail)}</p>
        </div>
      </div>
    `;
  }
}

function renderRows(items) {
  const tbody = $("tbody");
  const cards = $("cardsResults");
  tbody.innerHTML = "";
  if (cards) cards.innerHTML = "";

  if (!items.length) {
    renderEmptyState();
    return;
  }

  items.forEach((it, index) => {
    const num = getRowNumber(index);
    const badge = getStatusBadge(it.fecha_fin);
    const tagsHtml = renderTags(it);

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="cell-index">${num}</td>
      <td class="cell-puesto">${escapeHtml(it.puesto || "-")}</td>
      <td>${escapeHtml(it.entidad || "-")}</td>
      <td>${escapeHtml(it.ubicacion || "-")}</td>
      <td>${money(it.remuneracion)}</td>
      <td>${formatDate(it.fecha_inicio)}</td>
      <td>${formatDate(it.fecha_fin)}</td>
      <td>${badge}</td>
      <td><div class="table-tags">${tagsHtml}</div></td>
      <td><button class="ghost btn-detail" data-id="${it.id}">Ver detalle</button></td>
    `;
    tbody.appendChild(tr);

    if (cards) {
      const card = document.createElement("article");
      card.className = "result-card";
      card.innerHTML = `
        <div class="result-card-top">
          <span class="result-index">#${num}</span>
          ${badge}
        </div>
        <h3 class="result-title">${escapeHtml(it.puesto || "-")}</h3>
        <p class="result-entity">${escapeHtml(it.entidad || "-")}</p>

        <div class="card-meta-grid">
          <div>
            <span class="meta-label">Ubicación</span>
            <strong>${escapeHtml(it.ubicacion || "-")}</strong>
          </div>
          <div>
            <span class="meta-label">Remuneración</span>
            <strong>${money(it.remuneracion)}</strong>
          </div>
          <div>
            <span class="meta-label">Inicio</span>
            <strong>${formatDate(it.fecha_inicio)}</strong>
          </div>
          <div>
            <span class="meta-label">Fin</span>
            <strong>${formatDate(it.fecha_fin)}</strong>
          </div>
        </div>

        <div class="card-tags-row">
          ${tagsHtml}
        </div>

        <button class="ghost btn-detail full" data-id="${it.id}">Ver detalle</button>
      `;
      cards.appendChild(card);
    }
  });

  document.querySelectorAll("button[data-id]").forEach((b) => {
    b.addEventListener("click", () => showDetail(b.dataset.id));
  });
}

function makeDetailItem(label, value, type = "text", full = false) {
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
      <div class="detail-value">${escapeHtml(value)}</div>
    </div>
  `;
}

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

function buildMobileAccordionSection(title, items, open = false) {
  const cleanItems = items.filter(Boolean).join("");
  if (!cleanItems) return "";
  return `
    <details ${open ? "open" : ""}>
      <summary>${title}</summary>
      <div class="detail-accordion-body">${cleanItems}</div>
    </details>
  `;
}

async function showDetail(id) {
  const dialog = $("detalleDialog");
  renderDetailSkeleton();
  dialog.showModal();

  try {
    const d = await fetchJSON(`/ofertas/${id}`);
    $("dPuesto").textContent = d.puesto || "Detalle de oferta";

    const tagsHtml = renderTags(d);

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
      makeDetailItem("Ubicación", d.ubicacion),
      makeDetailItem("Número de convocatoria", d.numero_convocatoria),
      makeDetailItem("Link de postulación", d.link_postulacion, "link", true),
    ];

    const profileItems = [
      makeDetailItem("Formación", d.formacion, "text", true),
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
        ${buildMobileAccordionSection("Resumen", [
          makeDetailItem("Remuneración", money(d.remuneracion)),
          makeDetailItem("Vacantes", d.vacantes ?? "-"),
          makeDetailItem("Estado", isVigente(d.fecha_fin) ? "Vigente" : "Cerrada"),
          makeDetailItem("Vigencia", `${formatDate(d.fecha_inicio)} - ${formatDate(d.fecha_fin)}`),
        ], true)}
        ${buildMobileAccordionSection("Información general", generalItems, true)}
        ${buildMobileAccordionSection("Perfil del puesto", [
          makeDetailItem("Formación", d.formacion, "text", true),
          makeDetailItem("Experiencia", d.experiencia, "text", true),
          makeDetailItem("Especialización", d.especializacion, "text", true),
        ], false)}
        ${buildMobileAccordionSection("Conocimientos y competencias", [
          makeDetailItem("Conocimiento", d.conocimiento, "text", true),
          makeDetailItem("Competencias", d.competencias, "text", true),
        ], false)}
        ${buildMobileAccordionSection("Postulación", [
          makeDetailItem("Link de postulación", d.link_postulacion, "link", true),
        ], true)}
      </div>
    `;

    $("detalleBody").innerHTML = summary + desktopLayout + mobileAccordion;
  } catch (e) {
    $("detalleBody").innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">!</div>
        <div>
          <strong>No se pudo cargar el detalle</strong>
          <p>${escapeHtml(e.message)}</p>
        </div>
      </div>
    `;
  }
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

  $("prev").disabled = state.loading || state.page <= 1;
  $("next").disabled = state.loading || state.page >= state.totalPages;
}

function renderSortIndicators() {
  document.querySelectorAll("th.sortable").forEach((th) => {
    const span = th.querySelector(".sort-ind");
    const field = th.dataset.sort;
    if (!span) return;

    if (field === state.sortBy) {
      span.textContent = state.sortOrder === "asc" ? "▲" : "▼";
      th.setAttribute("aria-sort", state.sortOrder === "asc" ? "ascending" : "descending");
    } else {
      span.textContent = "";
      th.setAttribute("aria-sort", "none");
    }
  });
}

async function runSearch(options = {}) {
  updateLoading(true);
  renderTableSkeleton();
  renderActiveFiltersChip();
  updateResultsMeta(0);

  try {
    const data = await fetchJSON(buildQuery());
    const items = data.ofertas || [];
    const total = data.total || 0;
    state.totalPages = Math.max(1, Math.ceil(total / state.limit));

    renderRows(items);
    renderSortIndicators();
    updateResultsMeta(total);
    renderActiveFiltersChip();

    if (window.innerWidth < 768 && options.collapseFiltersOnMobile) {
      const filtersCard = $("filtersCard");
      if (filtersCard) {
        filtersCard.classList.add("filters-collapsed");
        syncFiltersCollapseByViewport();
      }
    }
  } catch (e) {
    renderEmptyState("Error cargando resultados", e.message);
    updateResultsMeta(0);
  } finally {
    updateLoading(false);
  }
}

function resetFilters() {
  ["q", "carrera", "especializacion", "ubicacion", "entidad", "remVal"].forEach((id) => {
    $(id).value = "";
  });
  $("remOp").value = "gte";
  $("estado").value = "todos";
  state.page = 1;
  renderActiveFiltersChip();
  runSearch({ collapseFiltersOnMobile: false });
}

function bindEnterSearch() {
  document.querySelectorAll(".filter-control").forEach((el) => {
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        state.page = 1;
        runSearch({ collapseFiltersOnMobile: true });
      }
    });
  });
}

function bindFiltersToggle() {
  const toggleBtn = $("toggleFilters");
  const filtersCard = $("filtersCard");
  if (!toggleBtn || !filtersCard) return;

  toggleBtn.addEventListener("click", () => {
    filtersCard.classList.toggle("filters-collapsed");
    syncFiltersCollapseByViewport();
  });
}

function bindEvents() {
  $("btnBuscar").addEventListener("click", () => {
    state.page = 1;
    runSearch({ collapseFiltersOnMobile: true });
  });

  $("btnLimpiar").addEventListener("click", resetFilters);

  $("prev").addEventListener("click", () => {
    if (state.page > 1) {
      state.page -= 1;
      runSearch();
    }
  });

  $("next").addEventListener("click", () => {
    if (state.page < state.totalPages) {
      state.page += 1;
      runSearch();
    }
  });

  $("cerrarDetalle").addEventListener("click", () => $("detalleDialog").close());

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
      runSearch();
    });
  });

  const dialog = $("detalleDialog");
  dialog.addEventListener("click", (e) => {
    const rect = dialog.getBoundingClientRect();
    const inDialog =
      rect.top <= e.clientY &&
      e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX &&
      e.clientX <= rect.left + rect.width;
    if (!inDialog) dialog.close();
  });

  window.addEventListener("resize", syncFiltersCollapseByViewport);

  bindEnterSearch();
  bindFiltersToggle();
  syncFiltersCollapseByViewport();
}

(async function init() {
  try {
    bindEvents();
    await loadStats();
    await runSearch();
  } catch (e) {
    alert(`Error cargando datos: ${e.message}`);
  }
})();