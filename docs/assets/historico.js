(function () {
  const pageSize = 50;
  let allItems = [];
  let filtered = [];
  let visible = pageSize;

  const els = {};

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    Object.assign(els, {
      anio: document.getElementById("filtro-anio"),
      fuente: document.getElementById("filtro-fuente"),
      tipo: document.getElementById("filtro-tipo"),
      tema: document.getElementById("filtro-tema"),
      texto: document.getElementById("filtro-texto"),
      orden: document.getElementById("orden"),
      contador: document.getElementById("contador-resultados"),
      resultados: document.getElementById("resultados"),
      vacio: document.getElementById("estado-vacio"),
      mas: document.getElementById("mostrar-mas"),
    });

    try {
      const index = await RegMonitor.fetchJson("data/items-index.json");
      const params = new URLSearchParams(window.location.search);
      renderAnios(index.anios || []);
      setIfPresent(els.anio, params.get("anio"));
      await loadYear(els.anio.value);
      restoreQuery(params);
      bindEvents();
      applyFilters(false);
    } catch (error) {
      els.contador.textContent = "No se ha podido cargar el histórico.";
      els.resultados.replaceChildren(RegMonitor.emptyNode(error.message));
    }
  }

  function renderAnios(anios) {
    els.anio.replaceChildren();
    anios.forEach((entry) => {
      const option = document.createElement("option");
      option.value = entry.anio;
      option.textContent = `${entry.anio} · ${entry.items} ítems`;
      els.anio.append(option);
    });
  }

  function bindEvents() {
    [els.anio, els.fuente, els.tipo, els.tema, els.orden].forEach((element) => {
      element.addEventListener("change", async () => {
        if (element === els.anio) {
          await loadYear(els.anio.value);
        }
        visible = pageSize;
        applyFilters();
      });
    });

    let timer = null;
    els.texto.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        visible = pageSize;
        applyFilters();
      }, 180);
    });

    els.mas.addEventListener("click", () => {
      visible += pageSize;
      renderResults();
    });
  }

  async function loadYear(anio) {
    if (!anio) {
      allItems = [];
      populateFilterOptions();
      return;
    }
    allItems = await RegMonitor.fetchJson(`data/items-${anio}.json`);
    populateFilterOptions();
  }

  function populateFilterOptions() {
    fillSelect(els.fuente, unique(allItems.map((item) => item.fuente)), "Todas");
    fillSelect(els.tipo, unique(allItems.map((item) => item.tipo)), "Todos", RegMonitor.labelTipo);
    fillSelect(
      els.tema,
      unique(allItems.flatMap((item) => item.temas)),
      "Todos",
      (tema) => RegMonitor.temaLabels[tema] || tema
    );
  }

  function fillSelect(select, values, emptyLabel, labeler) {
    const current = select.value;
    select.replaceChildren();
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = emptyLabel;
    select.append(empty);
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = labeler ? labeler(value) : value;
      select.append(option);
    });
    select.value = values.includes(current) ? current : "";
  }

  function applyFilters(updateUrl = true) {
    const text = normalize(els.texto.value);
    filtered = allItems.filter((item) => {
      if (els.fuente.value && item.fuente !== els.fuente.value) return false;
      if (els.tipo.value && item.tipo !== els.tipo.value) return false;
      if (els.tema.value && !item.temas.includes(els.tema.value)) return false;
      if (text) {
        const haystack = normalize(`${item.titulo} ${item.extracto}`);
        if (!haystack.includes(text)) return false;
      }
      return true;
    });

    sortItems();
    if (updateUrl) updateQuery();
    renderResults();
  }

  function sortItems() {
    const order = els.orden.value;
    filtered.sort((a, b) => {
      if (order === "score-desc") {
        return b.score - a.score || b.fecha_publicacion.localeCompare(a.fecha_publicacion);
      }
      if (order === "fecha-asc") {
        return a.fecha_publicacion.localeCompare(b.fecha_publicacion);
      }
      return b.fecha_publicacion.localeCompare(a.fecha_publicacion);
    });
  }

  function renderResults() {
    els.contador.textContent = RegMonitor.plural(filtered.length, "resultado", "resultados");
    syncActiveFilters();
    els.resultados.replaceChildren(...filtered.slice(0, visible).map(resultNode));
    els.vacio.hidden = filtered.length !== 0;
    els.mas.hidden = visible >= filtered.length;
  }

  function resultNode(item) {
    const node = RegMonitor.itemNode(item);
    node.classList.remove("item-card");
    node.classList.add("result-row");
    const topics = document.createElement("p");
    topics.className = "topics-line";
    topics.textContent = item.temas.map((tema) => RegMonitor.temaLabels[tema] || tema).join(" · ");
    node.append(topics);
    return node;
  }

  function syncActiveFilters() {
    [
      [els.fuente, Boolean(els.fuente.value)],
      [els.tipo, Boolean(els.tipo.value)],
      [els.tema, Boolean(els.tema.value)],
      [els.texto, Boolean(els.texto.value.trim())],
      [els.orden, els.orden.value !== "fecha-desc"],
    ].forEach(([element, active]) => {
      element.classList.toggle("is-active", active);
    });
  }

  function restoreQuery(params) {
    setIfPresent(els.fuente, params.get("fuente"));
    setIfPresent(els.tipo, params.get("tipo"));
    setIfPresent(els.tema, params.get("tema"));
    setIfPresent(els.texto, params.get("q"));
    setIfPresent(els.orden, params.get("orden"));
  }

  function updateQuery() {
    const params = new URLSearchParams();
    addParam(params, "anio", els.anio.value);
    addParam(params, "fuente", els.fuente.value);
    addParam(params, "tipo", els.tipo.value);
    addParam(params, "tema", els.tema.value);
    addParam(params, "q", els.texto.value.trim());
    addParam(params, "orden", els.orden.value === "fecha-desc" ? "" : els.orden.value);
    const query = params.toString();
    history.replaceState(null, "", query ? `?${query}` : window.location.pathname);
  }

  function setIfPresent(element, value) {
    if (value) element.value = value;
  }

  function addParam(params, key, value) {
    if (value) params.set(key, value);
  }

  function unique(values) {
    return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b, "es"));
  }

  function normalize(value) {
    return value
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim();
  }
})();
