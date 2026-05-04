/* ============================================================
   FB Marketplace Bot — Dashboard JS
   ============================================================ */

const API = {
  ads:    () => fetch("/api/ads").then(r => r.json()),
  stats:  () => fetch("/api/stats").then(r => r.json()),
  search: () => fetch("/api/search", { method: "POST" }).then(r => r.json()),
  clear:  () => fetch("/api/clear",  { method: "POST" }).then(r => r.json()),
};

// ── State ────────────────────────────────────────────────────
let allAds       = [];
let activeFilter = "all";
let searchQuery  = "";
let socket       = null;

// ── DOM refs ─────────────────────────────────────────────────
const adsGrid      = document.getElementById("adsGrid");
const emptyState   = document.getElementById("emptyState");
const loadingState = document.getElementById("loadingState");
const btnSearch    = document.getElementById("btnSearch");
const btnSearchTxt = document.getElementById("btnSearchText");
const btnClear     = document.getElementById("btnClear");
const statusPill   = document.getElementById("statusPill");
const statusDot    = statusPill.querySelector(".status-dot");
const statusText   = document.getElementById("statusText");
const searchInput  = document.getElementById("searchInput");
const toast        = document.getElementById("toast");
const modalOverlay = document.getElementById("modalOverlay");
const modalContent = document.getElementById("modalContent");
const modalClose   = document.getElementById("modalClose");

// ── Toast ─────────────────────────────────────────────────────
let toastTimer = null;
function showToast(msg, type = "info") {
  toast.textContent = msg;
  toast.className   = `toast show ${type}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.className = "toast"; }, 3500);
}

// ── Status pill ───────────────────────────────────────────────
function setStatus(state, text) {
  statusDot.className = `status-dot ${state}`;
  statusText.textContent = text;
}

// ── Stats bar ─────────────────────────────────────────────────
async function refreshStats() {
  try {
    const s = await API.stats();
    document.getElementById("statTotal").textContent   = s.total;
    document.getElementById("statSparkGT").textContent = s.by_vehicle?.spark_gt   ?? 0;
    document.getElementById("statI10").textContent     = s.by_vehicle?.hyundai_i10 ?? 0;
    document.getElementById("statOther").textContent   = s.by_vehicle?.other       ?? 0;
    document.getElementById("statAvgPrice").textContent =
      s.avg_price ? `$${(s.avg_price/1_000_000).toFixed(1)}M` : "—";
    document.getElementById("statInterval").textContent =
      s.interval_minutes ? `${s.interval_minutes} min` : "—";
  } catch (_) {}
}

// ── Format helpers ────────────────────────────────────────────
function fmtPrice(p) {
  if (!p) return "Precio N/A";
  return "$" + p.toLocaleString("es-CO");
}

function timeAgo(isoStr) {
  if (!isoStr) return "";
  const diff = Date.now() - new Date(isoStr).getTime();
  const min  = Math.floor(diff / 60000);
  if (min < 1)  return "Justo ahora";
  if (min < 60) return `Hace ${min} min`;
  const hr = Math.floor(min / 60);
  if (hr < 24)  return `Hace ${hr}h`;
  return `Hace ${Math.floor(hr/24)}d`;
}

// ── Card builder ──────────────────────────────────────────────
function buildCard(ad, isNew = false) {
  const card = document.createElement("div");
  card.className = `ad-card${isNew ? " new-flash" : ""}`;
  card.dataset.vehicleKey = ad.vehicle_key;
  card.dataset.title      = (ad.title + " " + ad.location).toLowerCase();

  const imgHtml = ad.images?.length
    ? `<div class="card-image"><img src="${ad.images[0]}" alt="${ad.title}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=card-image-placeholder><svg viewBox=\\'0 0 24 24\\' width=\\'32\\' height=\\'32\\' fill=\\'none\\' stroke=\\'currentColor\\' stroke-width=\\'1.5\\'><rect x=\\'3\\' y=\\'3\\' width=\\'18\\' height=\\'18\\' rx=\\'2\\'/><circle cx=\\'8.5\\' cy=\\'8.5\\' r=\\'1.5\\'/><polyline points=\\'21 15 16 10 5 21\\'/></svg>Sin foto</div>'"/></div>`
    : `<div class="card-image-placeholder">
         <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
         Sin foto
       </div>`;

  card.innerHTML = `
    ${imgHtml}
    <div class="card-body">
      <div class="card-top">
        <span class="vehicle-tag" style="background:${ad.vehicle_color}">${ad.vehicle_label}</span>
        ${ad.year && ad.year !== "N/A" ? `<span style="font-size:0.7rem;color:var(--text3);font-family:var(--mono)">${ad.year}</span>` : ""}
      </div>
      <div class="card-title">${ad.title}</div>
      <div class="card-meta">
        <div class="card-meta-row">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
          ${ad.location || "Ubicación N/A"}
        </div>
      </div>
      <div class="card-price">${fmtPrice(ad.price)}</div>
    </div>
    <div class="card-footer">
      <span>${timeAgo(ad.seen_at)}</span>
      ${ad.url ? `<a class="card-link" href="${ad.url}" target="_blank" rel="noopener" onclick="event.stopPropagation()">
        Ver en FB
        <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
      </a>` : ""}
    </div>
  `;

  card.addEventListener("click", () => openModal(ad));
  return card;
}

// ── Render grid ───────────────────────────────────────────────
function renderGrid(newAds = null) {
  const src = newAds ?? allAds;

  const filtered = src.filter(ad => {
    const matchFilter = activeFilter === "all" || ad.vehicle_key === activeFilter;
    const matchSearch = !searchQuery || ad.title.includes(searchQuery.toLowerCase());
    return matchFilter && matchSearch;
  });

  if (newAds) {
    // Prepend new cards with flash
    filtered.forEach(ad => {
      const card = buildCard(ad, true);
      adsGrid.insertBefore(card, adsGrid.firstChild);
    });
  } else {
    adsGrid.innerHTML = "";
    filtered.forEach(ad => adsGrid.appendChild(buildCard(ad)));
  }

  const total = adsGrid.querySelectorAll(".ad-card").length;
  emptyState.style.display  = total === 0 ? "flex" : "none";
  loadingState.style.display = "none";
}

// ── Apply live filter/search ──────────────────────────────────
function applyFilters() {
  const cards = adsGrid.querySelectorAll(".ad-card");
  let visible = 0;
  cards.forEach(card => {
    const matchFilter = activeFilter === "all" || card.dataset.vehicleKey === activeFilter;
    const matchSearch = !searchQuery || card.dataset.title.includes(searchQuery);
    const show = matchFilter && matchSearch;
    card.style.display = show ? "" : "none";
    if (show) visible++;
  });
  emptyState.style.display = visible === 0 ? "flex" : "none";
}

// ── Modal ─────────────────────────────────────────────────────
function openModal(ad) {
  const imgHtml = ad.images?.length
    ? `<img class="modal-image" src="${ad.images[0]}" alt="${ad.title}" onerror="this.outerHTML='<div class=modal-image-placeholder><svg viewBox=\\'0 0 24 24\\' width=\\'40\\' height=\\'40\\' fill=\\'none\\' stroke=\\'currentColor\\' stroke-width=\\'1.5\\'><rect x=\\'3\\' y=\\'3\\' width=\\'18\\' height=\\'18\\' rx=\\'2\\'/><circle cx=\\'8.5\\' cy=\\'8.5\\' r=\\'1.5\\'/><polyline points=\\'21 15 16 10 5 21\\'/></svg></div>'" />`
    : `<div class="modal-image-placeholder">
         <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
       </div>`;

  modalContent.innerHTML = `
    ${imgHtml}
    <div class="modal-body">
      <span class="modal-vehicle-tag" style="background:${ad.vehicle_color}">${ad.vehicle_label}</span>
      <div class="modal-title">${ad.title}</div>
      <div class="modal-price">${fmtPrice(ad.price)}</div>
      <div class="modal-info-grid">
        <div class="modal-info-item">
          <div class="modal-info-label">Año / Modelo</div>
          <div class="modal-info-value">${ad.year || "N/A"}</div>
        </div>
        <div class="modal-info-item">
          <div class="modal-info-label">Ubicación</div>
          <div class="modal-info-value">${ad.location || "N/A"}</div>
        </div>
        <div class="modal-info-item">
          <div class="modal-info-label">Tipo</div>
          <div class="modal-info-value">${ad.vehicle_label}</div>
        </div>
        <div class="modal-info-item">
          <div class="modal-info-label">Encontrado</div>
          <div class="modal-info-value">${timeAgo(ad.seen_at)}</div>
        </div>
      </div>
      ${ad.description ? `<div class="modal-description">${ad.description}</div>` : ""}
      <div class="modal-cta">
        ${ad.url
          ? `<a href="${ad.url}" target="_blank" rel="noopener" class="btn btn-primary btn-full">
               <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
               Ver en Marketplace
             </a>`
          : `<span class="btn btn-ghost btn-full" style="opacity:0.4;cursor:default">Sin enlace disponible</span>`
        }
        <button class="btn btn-ghost btn-full" onclick="closeModal()">Cerrar</button>
      </div>
    </div>
  `;

  modalOverlay.classList.add("open");
}

function closeModal() {
  modalOverlay.classList.remove("open");
}

modalClose.addEventListener("click", closeModal);
modalOverlay.addEventListener("click", e => { if (e.target === modalOverlay) closeModal(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });

// ── Initial load ──────────────────────────────────────────────
async function loadAds() {
  loadingState.style.display = "flex";
  emptyState.style.display   = "none";
  try {
    const data = await API.ads();
    allAds = data.ads ?? [];
    renderGrid();
    refreshStats();
  } catch (_) {
    loadingState.style.display = "none";
    emptyState.style.display   = "flex";
    showToast("Error cargando anuncios", "error");
  }
}

// ── Search button ─────────────────────────────────────────────
btnSearch.addEventListener("click", async () => {
  btnSearch.disabled    = true;
  btnSearchTxt.textContent = "Buscando...";
  setStatus("searching", "Buscando...");
  showToast("Iniciando búsqueda en Marketplace...", "info");

  try {
    await API.search();
    // Result will come through WebSocket
  } catch (_) {
    btnSearch.disabled    = false;
    btnSearchTxt.textContent = "Buscar ahora";
    setStatus("error", "Error");
    showToast("No se pudo iniciar la búsqueda", "error");
  }
});

// ── Clear button ──────────────────────────────────────────────
btnClear.addEventListener("click", async () => {
  if (!confirm("¿Limpiar todo el historial? El bot volverá a notificar todos los anuncios.")) return;
  await API.clear();
  allAds = [];
  adsGrid.innerHTML = "";
  emptyState.style.display = "flex";
  refreshStats();
  showToast("Historial limpiado", "info");
});

// ── Filter buttons ────────────────────────────────────────────
document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeFilter = btn.dataset.filter;
    applyFilters();
  });
});

// ── Search input ──────────────────────────────────────────────
searchInput.addEventListener("input", () => {
  searchQuery = searchInput.value.trim().toLowerCase();
  applyFilters();
});

// ── WebSocket ─────────────────────────────────────────────────
function initSocket() {
  socket = io({ transports: ["websocket", "polling"] });

  socket.on("connect", () => {
    setStatus("online", "En línea");
    showToast("Conectado al servidor", "success");
  });

  socket.on("disconnect", () => {
    setStatus("error", "Sin conexión");
    showToast("Desconectado. Reconectando...", "error");
  });

  socket.on("new_ads", data => {
    const incoming = data.ads ?? [];
    if (!incoming.length) return;

    // Prepend to allAds
    allAds = [...incoming, ...allAds];

    // Add cards to grid if filter matches
    const matching = incoming.filter(ad => {
      const matchFilter = activeFilter === "all" || ad.vehicle_key === activeFilter;
      const matchSearch = !searchQuery || (ad.title + " " + ad.location).toLowerCase().includes(searchQuery);
      return matchFilter && matchSearch;
    });

    if (matching.length) renderGrid(matching);
    refreshStats();
  });

  socket.on("search_done", data => {
    btnSearch.disabled    = false;
    btnSearchTxt.textContent = "Buscar ahora";
    setStatus("online", "En línea");
    const count = data.count ?? 0;
    showToast(
      count > 0
        ? `✓ ${count} anuncio${count > 1 ? "s" : ""} nuevo${count > 1 ? "s" : ""} encontrado${count > 1 ? "s" : ""}`
        : "Sin anuncios nuevos esta vez",
      count > 0 ? "success" : "info"
    );
  });

  socket.on("search_error", data => {
    btnSearch.disabled    = false;
    btnSearchTxt.textContent = "Buscar ahora";
    setStatus("error", "Error");
    showToast(`Error: ${data.error}`, "error");
  });

  socket.on("db_cleared", () => {
    allAds = [];
    adsGrid.innerHTML = "";
    emptyState.style.display = "flex";
    refreshStats();
  });
}

// ── Boot ──────────────────────────────────────────────────────
loadAds();
initSocket();

// Auto-refresh stats every 60s
setInterval(refreshStats, 60_000);
