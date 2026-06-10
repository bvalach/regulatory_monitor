(function () {
  let currentDigest = null;

  const temaLabels = {
    higiene_seguridad: "Higiene y seguridad alimentaria",
    aditivos_contaminantes: "Aditivos y contaminantes",
    etiquetado_consumidor: "Etiquetado e información al consumidor",
    bienestar_sanidad_animal: "Bienestar animal y sanidad animal",
    subproductos_sandach: "Subproductos y SANDACH",
    envases_sostenibilidad: "Envases y sostenibilidad",
    comercio_exterior: "Comercio exterior y aranceles",
    ayudas_fiscalidad: "Ayudas, subvenciones y fiscalidad sectorial",
    otros: "Otros",
  };

  async function fetchJson(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`No se pudo cargar ${path}`);
    }
    return response.json();
  }

  function formatDate(value) {
    return new Intl.DateTimeFormat("es-ES", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
  }

  function formatDateTime(value) {
    return new Intl.DateTimeFormat("es-ES", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  }

  function itemNode(item, topicId) {
    const article = document.createElement("article");
    article.className = "item-card";
    article.classList.add(topicClass(topicId || (item.temas || [])[0]));

    const header = document.createElement("header");
    header.append(
      badge(item.fuente, `source-${item.fuente}`, `Fuente: ${item.fuente}`),
      badge(labelTipo(item.tipo), "type-badge", `Tipo: ${labelTipo(item.tipo)}`)
    );

    const title = document.createElement("h3");
    title.className = "item-title";
    const link = document.createElement("a");
    link.href = item.url;
    link.textContent = item.titulo;
    link.title = item.titulo;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    title.append(link);

    article.append(header, title);

    if (item.extracto && !isDuplicateExtract(item.titulo, item.extracto)) {
      const extract = document.createElement("p");
      extract.className = "extract";
      extract.textContent = item.extracto;
      article.append(extract);
    }

    article.append(metaNode(item));
    return article;
  }

  function badge(text, className, ariaLabel) {
    const span = document.createElement("span");
    span.className = `badge ${className}`;
    span.textContent = text;
    if (ariaLabel) span.setAttribute("aria-label", ariaLabel);
    return span;
  }

  function labelTipo(tipo) {
    return tipo.replace(/_/g, " ");
  }

  function renderAlerts(meta) {
    const container = document.getElementById("avisos-fuentes");
    if (!container || !meta || !meta.fuentes) return;
    container.replaceChildren();
    Object.entries(meta.fuentes)
      .filter(([, estado]) => estado.estado !== "ok")
      .forEach(([fuente, estado]) => {
        const alert = document.createElement("p");
        alert.className = "alert";
        alert.textContent = `${fuente} degradada: ${estado.detalle || "sin detalle"}`;
        container.append(alert);
      });
  }

  function renderStatus(status, meta) {
    const degraded = Object.values(meta.fuentes || {}).some((fuente) => fuente.estado !== "ok");
    const dot = document.createElement("span");
    dot.className = `status-dot ${degraded ? "status-degraded" : "status-ok"}`;
    dot.setAttribute("aria-hidden", "true");

    const text = document.createElement("span");
    text.textContent = `Última ejecución: ${formatDateTime(meta.ultima_ejecucion)} · ${plural(meta.recuentos.items_total, "ítem acumulado", "ítems acumulados")}`;

    status.className = "status-line";
    status.replaceChildren(dot, text);
  }

  async function initIndex() {
    const status = document.getElementById("ultima-ejecucion");
    const selector = document.getElementById("digest-selector");
    const periodo = document.getElementById("digest-periodo");
    const digestRoot = document.getElementById("digest");
    const exportMd = document.getElementById("export-md");
    const exportCsv = document.getElementById("export-csv");

    try {
      const [meta, digestIndex] = await Promise.all([
        fetchJson("data/meta.json"),
        fetchJson("data/digests/index.json"),
      ]);
      renderStatus(status, meta);
      renderAlerts(meta);

      selector.replaceChildren();
      digestIndex.digests.forEach((entry) => {
        const option = document.createElement("option");
        option.value = entry.json;
        option.textContent = `${entry.id} · ${plural(entry.items, "ítem", "ítems")}`;
        selector.append(option);
      });

      const first = digestIndex.digests.find((entry) => entry.id === meta.digest_reciente) || digestIndex.digests[0];
      if (!first) {
        digestRoot.replaceChildren(emptyNode("Todavía no hay digests publicados."));
        return;
      }
      selector.value = first.json;
      await loadSelectedDigest(first.json, periodo, digestRoot, exportMd, exportCsv);
      selector.addEventListener("change", () => loadSelectedDigest(selector.value, periodo, digestRoot, exportMd, exportCsv));
      exportMd.addEventListener("click", () => exportDigest("markdown"));
      exportCsv.addEventListener("click", () => exportDigest("csv"));
    } catch (error) {
      status.textContent = "No se han podido cargar los datos del observatorio.";
      digestRoot.replaceChildren(emptyNode(error.message));
    }
  }

  async function loadSelectedDigest(path, periodo, root, exportMd, exportCsv) {
    currentDigest = await renderDigest(path, periodo, root);
    setExportEnabled(Boolean(currentDigest), exportMd, exportCsv);
  }

  async function renderDigest(path, periodo, root) {
    const data = await fetchJson(path);
    periodo.textContent = `${data.id}: ${formatDate(data.desde)} a ${formatDate(data.hasta)}`;
    root.replaceChildren();

    if (data.sin_novedades) {
      root.append(emptyNode("No se han detectado novedades relevantes esta semana."));
      return data;
    }

    data.temas.forEach((tema) => {
      const section = document.createElement("section");
      section.className = "topic";
      section.classList.add(topicClass(tema.id));

      const titleWrap = document.createElement("div");
      titleWrap.className = "topic-title";
      const title = document.createElement("h2");
      title.textContent = tema.etiqueta;
      const count = document.createElement("span");
      count.className = "count";
      count.textContent = plural(tema.items.length, "ítem", "ítems");
      titleWrap.append(title, count);

      section.append(titleWrap, ...tema.items.map((item) => itemNode(item, tema.id)));
      root.append(section);
    });
    return data;
  }

  function setExportEnabled(enabled, ...buttons) {
    buttons.filter(Boolean).forEach((button) => {
      button.disabled = !enabled;
    });
  }

  function exportDigest(format) {
    if (!currentDigest) return;
    const baseName = `digest-${currentDigest.id}`;
    if (format === "csv") {
      downloadText(`${baseName}.csv`, buildCsv(currentDigest), "text/csv;charset=utf-8");
      return;
    }
    downloadText(`${baseName}.md`, buildMarkdown(currentDigest), "text/markdown;charset=utf-8");
  }

  function buildMarkdown(data) {
    const lines = [
      `# Digest ${data.id}`,
      "",
      `Periodo: ${formatDate(data.desde)} a ${formatDate(data.hasta)}`,
    ];

    if (data.generado_en) {
      lines.push(`Generado: ${formatDateTime(data.generado_en)}`);
    }

    lines.push("");

    if (data.sin_novedades) {
      lines.push("No se han detectado novedades relevantes esta semana.");
      return `${lines.join("\n")}\n`;
    }

    data.temas.forEach((tema) => {
      lines.push(`## ${tema.etiqueta}`, "");
      tema.items.forEach((item) => {
        const terminos = Array.isArray(item.terminos) ? item.terminos.join(", ") : "";
        lines.push(
          `### [${escapeMarkdown(item.titulo)}](<${item.url}>)`,
          "",
          `- Fuente: ${item.fuente}`,
          `- Tipo: ${labelTipo(item.tipo)}`,
          `- Fecha de publicación: ${formatDate(item.fecha_publicacion)}`,
          `- Score: ${item.score}`,
          `- Términos: ${terminos}`,
          "",
          item.extracto || "",
          ""
        );
      });
    });

    return `${lines.join("\n").trimEnd()}\n`;
  }

  function buildCsv(data) {
    const headers = [
      "digest_id",
      "periodo_desde",
      "periodo_hasta",
      "tema_id",
      "tema",
      "id",
      "fuente",
      "tipo",
      "fecha_publicacion",
      "titulo",
      "url",
      "score",
      "terminos",
      "extracto",
    ];

    const rows = flattenDigestItems(data).map(({ tema, item }) => [
      data.id,
      data.desde,
      data.hasta,
      tema.id,
      tema.etiqueta,
      item.id,
      item.fuente,
      item.tipo,
      item.fecha_publicacion,
      item.titulo,
      item.url,
      item.score,
      Array.isArray(item.terminos) ? item.terminos.join("|") : "",
      item.extracto,
    ]);

    return `\uFEFF${[headers, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n")}\n`;
  }

  function flattenDigestItems(data) {
    return (data.temas || []).flatMap((tema) =>
      (tema.items || []).map((item) => ({ tema, item }))
    );
  }

  function metaNode(item) {
    const footer = document.createElement("footer");
    footer.className = "item-meta";

    const time = document.createElement("time");
    time.dateTime = item.fecha_publicacion;
    time.textContent = formatDate(item.fecha_publicacion);

    const score = document.createElement("span");
    score.className = `score ${scoreClass(item.score)}`;
    score.textContent = `score ${item.score}`;

    footer.append(time, score);
    (item.terminos || []).forEach((termino) => {
      const tag = document.createElement("span");
      tag.className = "tag";
      tag.textContent = termino;
      footer.append(tag);
    });

    return footer;
  }

  function scoreClass(score) {
    if (score > 30) return "score-high";
    if (score >= 10) return "score-medium";
    return "score-low";
  }

  function topicClass(topicId) {
    return topicId ? `topic-${topicId}` : "topic-otros";
  }

  function isDuplicateExtract(title, extract) {
    return normalizeText(title) === normalizeText(extract);
  }

  function normalizeText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function plural(count, singular, pluralLabel) {
    return `${count} ${count === 1 ? singular : pluralLabel}`;
  }

  function downloadText(filename, content, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function csvEscape(value) {
    const text = value == null ? "" : String(value);
    if (/[",\n\r]/.test(text)) {
      return `"${text.replace(/"/g, '""')}"`;
    }
    return text;
  }

  function escapeMarkdown(value) {
    return String(value || "").replace(/([\\[\]])/g, "\\$1");
  }

  function emptyNode(text) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent = text;
    return p;
  }

  window.RegMonitor = {
    fetchJson,
    formatDate,
    formatDateTime,
    itemNode,
    badge,
    labelTipo,
    plural,
    temaLabels,
    emptyNode,
  };

  document.addEventListener("DOMContentLoaded", () => {
    if (document.body.dataset.page === "index") {
      initIndex();
    }
  });
})();
