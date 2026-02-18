const workflowType = document.body.dataset.workflow || "adventures";

const csvFile = document.getElementById("csvFile");
const csvName = document.getElementById("csvName");
const status = document.getElementById("status");
const livePreview = document.getElementById("livePreview");
const downloadPanel = document.getElementById("downloadPanel");
const validationPanel = document.getElementById("validationPanel");
const generateBtn = document.getElementById("generateBtn");
const validateBtn = document.getElementById("validateBtn");
const fontSample = document.getElementById("fontSample");
const scriptSample = document.getElementById("scriptSample");
const rankSelect = document.getElementById("rankSelect");
const rankTemplateLink = document.getElementById("rankTemplateLink");
const rankTemplateNote = document.getElementById("rankTemplateNote");
const csvFieldContainer = csvFile ? csvFile.closest(".field") : null;

const fields = {
  fontName: document.getElementById("fontName"),
  scriptFont: document.getElementById("scriptFont"),
  shiftLeft: document.getElementById("shiftLeft"),
  shiftDown: document.getElementById("shiftDown"),
  fontSize: document.getElementById("fontSize"),
  scriptFontSize: document.getElementById("scriptFontSize"),
  outputName: document.getElementById("outputName"),
  outputMode: document.getElementById("outputMode"),
};

const rankTemplateMap = {
  Lion: {
    csvHref: "/rank_template.csv",
    linkLabel: "Download Rank CSV Template",
    note: "One shared rank CSV template works for all ranks.",
  },
  Tiger: {
    csvHref: "/rank_template.csv",
    linkLabel: "Download Rank CSV Template",
    note: "One shared rank CSV template works for all ranks.",
  },
  Wolf: {
    csvHref: "/rank_template.csv",
    linkLabel: "Download Rank CSV Template",
    note: "One shared rank CSV template works for all ranks.",
  },
  Bear: {
    csvHref: "/rank_template.csv",
    linkLabel: "Download Rank CSV Template",
    note: "One shared rank CSV template works for all ranks.",
  },
  Webelo: {
    csvHref: "/rank_template.csv",
    linkLabel: "Download Rank CSV Template",
    note: "One shared rank CSV template works for all ranks.",
  },
  "Arrow of Light": {
    csvHref: "/rank_template.csv",
    linkLabel: "Download Rank CSV Template",
    note: "One shared rank CSV template works for all ranks.",
  },
};

const fontPreviewMap = {
  Helvetica: "Helvetica, Arial, sans-serif",
  TimesRoman: "Times New Roman, Times, serif",
  Courier: "Courier New, Courier, monospace",
  Alegreya: '"Alegreya", Georgia, serif',
  Archivo: '"Archivo", "Arial Narrow", sans-serif',
  FiraSans: '"Fira Sans", Arial, sans-serif',
  Bangers: '"Bangers", "Impact", sans-serif',
  CabinSketch: '"Cabin Sketch", "Comic Sans MS", cursive',
  LilitaOne: '"Lilita One", "Arial Black", sans-serif',
  Righteous: '"Righteous", "Trebuchet MS", sans-serif',
  Oswald: '"Oswald", "Arial Narrow", sans-serif',
  Montserrat: '"Montserrat", Arial, sans-serif',
  Kanit: '"Kanit", Arial, sans-serif',
  Lora: '"Lora", Georgia, serif',
  CrimsonPro: '"Crimson Pro", Georgia, serif',
  IBMPlexSerif: '"IBM Plex Serif", Georgia, serif',
  Merriweather: '"Merriweather", Georgia, serif',
  DejaVuSerif: '"DejaVu Serif", Georgia, serif',
  DejaVuSans: '"DejaVu Sans", Verdana, sans-serif',
  DejaVuSansMono: '"DejaVu Sans Mono", "Courier New", monospace',
  PatrickHand: '"Patrick Hand", cursive',
  PermanentMarker: '"Permanent Marker", cursive',
  DancingScript: '"Dancing Script", cursive',
  Caveat: '"Caveat", cursive',
  KaushanScript: '"Kaushan Script", cursive',
  DejaVuSerifItalic: '"DejaVu Serif", Georgia, serif',
  DejaVuSansOblique: '"DejaVu Sans", Verdana, sans-serif',
};

const requiredEls = [
  csvFile,
  csvName,
  status,
  livePreview,
  downloadPanel,
  validationPanel,
  generateBtn,
  validateBtn,
  fontSample,
  scriptSample,
  fields.fontName,
  fields.scriptFont,
  fields.shiftLeft,
  fields.shiftDown,
  fields.fontSize,
  fields.scriptFontSize,
  fields.outputName,
  fields.outputMode,
];

if (requiredEls.some((el) => !el)) {
  console.warn("Generator UI not initialized: missing required elements.");
} else {
  const canonicalHeaderAliases = {
    Date: ["date", "award date", "earned date", "completion date"],
    "Pack Number": ["pack number", "pack #", "pack no", "pack", "packno"],
    "Den Number": ["den number", "den #", "den no", "den", "denno", "den no."],
    "Scout Name": [
      "scout name",
      "name",
      "youth name",
      "child name",
      "childs name",
      "cub name",
      "scout",
    ],
    "Award Name": ["award name", "award", "adventure", "adventure name", "adventure title"],
    Rank: ["rank", "rank name", "rank title"],
    "Den Leader": ["den leader", "denleader", "leader", "den leader name"],
    Cubmaster: ["cubmaster", "cub master", "cm", "cubmaster name"],
  };
  const commonRequiredFields = ["Date", "Pack Number", "Scout Name", "Den Leader", "Cubmaster"];
  const csvMappingState = {
    headers: [],
    rows: [],
    mapping: {},
    unresolvedRequired: [],
  };
  let csvMapperEls = null;

  function currentRank() {
    return rankSelect ? rankSelect.value : "";
  }

  function requiredFieldsForWorkflow() {
    if (workflowType === "ranks") {
      return [...commonRequiredFields];
    }
    return [...commonRequiredFields, "Award Name"];
  }

  function normalizeHeaderToken(value) {
    return String(value || "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  function inferAutoMapping(headers) {
    const normalizedHeaders = new Map();
    headers.forEach((header) => {
      normalizedHeaders.set(normalizeHeaderToken(header), header);
    });
    const inferred = {};
    Object.entries(canonicalHeaderAliases).forEach(([canonical, aliases]) => {
      if (headers.includes(canonical)) {
        inferred[canonical] = canonical;
        return;
      }
      for (const alias of aliases) {
        const match = normalizedHeaders.get(normalizeHeaderToken(alias));
        if (match) {
          inferred[canonical] = match;
          return;
        }
      }
    });
    return inferred;
  }

  function getRowValue(row, canonicalHeader) {
    const direct = (row[canonicalHeader] || "").trim();
    if (direct) return direct;
    const mappedHeader = csvMappingState.mapping[canonicalHeader];
    if (!mappedHeader) return "";
    return (row[mappedHeader] || "").trim();
  }

  function calculateUnresolvedRequired() {
    const required = requiredFieldsForWorkflow();
    const available = new Set(csvMappingState.headers);
    return required.filter((field) => {
      if (available.has(field)) return false;
      const mapped = csvMappingState.mapping[field];
      return !mapped || !available.has(mapped);
    });
  }

  function ensureMapperUi() {
    if (csvMapperEls || !csvFieldContainer) return csvMapperEls;
    const container = document.createElement("div");
    container.className = "csv-mapper";
    container.hidden = true;
    container.innerHTML = `
      <div class="csv-mapper-head">
        <strong>CSV column mapping required</strong>
        <p>Your file headers do not fully match expected fields. Map missing required fields below.</p>
      </div>
      <div class="csv-mapper-list" id="csvMapperList"></div>
    `;
    csvFieldContainer.appendChild(container);
    csvMapperEls = {
      container,
      list: container.querySelector("#csvMapperList"),
    };
    return csvMapperEls;
  }

  function renderCsvMapper() {
    const mapper = ensureMapperUi();
    if (!mapper || !mapper.list) return;
    const missing = csvMappingState.unresolvedRequired;
    if (!missing.length) {
      mapper.container.hidden = true;
      return;
    }

    const options = csvMappingState.headers
      .map((header) => `<option value="${header.replaceAll('"', "&quot;")}">${header}</option>`)
      .join("");
    mapper.list.innerHTML = missing
      .map((field) => {
        const selected = csvMappingState.mapping[field] || "";
        return `
          <label class="csv-mapper-row">
            <span>${field}</span>
            <select data-map-field="${field}">
              <option value="">Select CSV column...</option>
              ${options}
            </select>
          </label>
        `;
      })
      .join("");
    mapper.container.hidden = false;
    mapper.list.querySelectorAll("select[data-map-field]").forEach((select) => {
      const field = select.getAttribute("data-map-field");
      if (field) {
        const selected = csvMappingState.mapping[field] || "";
        if (selected && csvMappingState.headers.includes(selected)) {
          select.value = selected;
        }
      }
      select.addEventListener("change", () => {
        const targetField = select.getAttribute("data-map-field");
        if (!targetField) return;
        if (select.value) {
          csvMappingState.mapping[targetField] = select.value;
        } else {
          delete csvMappingState.mapping[targetField];
        }
        csvMappingState.unresolvedRequired = calculateUnresolvedRequired();
        renderCsvMapper();
        refreshPreviewFromCurrentState();
      });
    });
  }

  function currentCsvMappingPayload() {
    const required = new Set([...requiredFieldsForWorkflow(), "Rank", "Den Number"]);
    const payload = {};
    Object.entries(csvMappingState.mapping).forEach(([target, source]) => {
      if (!source || !required.has(target)) return;
      payload[target] = source;
    });
    return payload;
  }

  function refreshPreviewFromCurrentState() {
    if (!csvMappingState.rows.length) {
      previewData = {
        ...defaultPreview,
        award: workflowType === "ranks" ? currentRank() || "Wolf" : defaultPreview.award,
      };
      renderLivePreview();
      return;
    }
    const row = csvMappingState.rows[0];
    const rankOrAward =
      getRowValue(row, "Award Name") ||
      getRowValue(row, "Rank") ||
      (workflowType === "ranks" ? currentRank() : "") ||
      defaultPreview.award;
    previewData = {
      date: getRowValue(row, "Date") || defaultPreview.date,
      pack: getRowValue(row, "Pack Number") || defaultPreview.pack,
      scout: getRowValue(row, "Scout Name") || defaultPreview.scout,
      award: rankOrAward,
      denLeader: getRowValue(row, "Den Leader") || defaultPreview.denLeader,
      cubmaster: getRowValue(row, "Cubmaster") || defaultPreview.cubmaster,
    };
    renderLivePreview();
  }

  function setStatus(message, type = "info") {
    status.textContent = message;
    status.dataset.type = type;
  }

  function setFontSample() {
    const fontFamily = fontPreviewMap[fields.fontName.value] || "inherit";
    const scriptFamily =
      fields.scriptFont.value === "None"
        ? fontFamily
        : fontPreviewMap[fields.scriptFont.value] || "inherit";
    fontSample.style.fontFamily = fontFamily;
    scriptSample.style.fontFamily = scriptFamily;
  }

  function updateRankTemplateUi() {
    if (!rankSelect || !rankTemplateLink || !rankTemplateNote) return;
    const rank = currentRank();
    const cfg = rankTemplateMap[rank] || rankTemplateMap.Wolf;
    rankTemplateNote.textContent = cfg.note;
    if (cfg.csvHref) {
      rankTemplateLink.textContent = cfg.linkLabel;
      rankTemplateLink.setAttribute("href", cfg.csvHref);
      rankTemplateLink.setAttribute("download", "");
      rankTemplateLink.style.pointerEvents = "auto";
      rankTemplateLink.style.opacity = "1";
    } else {
      rankTemplateLink.textContent = cfg.linkLabel;
      rankTemplateLink.setAttribute("href", "#");
      rankTemplateLink.removeAttribute("download");
      rankTemplateLink.style.pointerEvents = "none";
      rankTemplateLink.style.opacity = "0.6";
    }
  }

  function gatherPayload() {
    return {
      workflow: workflowType,
      rank: currentRank(),
      fontName: fields.fontName.value,
      scriptFont: fields.scriptFont.value,
      shiftLeft: fields.shiftLeft.value,
      shiftDown: fields.shiftDown.value,
      fontSize: fields.fontSize.value,
      scriptFontSize: fields.scriptFontSize.value,
      outputName: fields.outputName.value,
      outputMode: fields.outputMode.value,
    };
  }

  const defaultPreview = {
    date: "02/22/2026",
    pack: "Pack 202",
    scout: "Piney Knotts",
    award: workflowType === "ranks" ? currentRank() || "Wolf" : "Badge to the Bone",
    denLeader: "Ranger Barkley",
    cubmaster: "Twig Timberly",
  };

  let previewData = { ...defaultPreview };

  function parseCsvRows(text) {
    const lines = text.split(/\r?\n/).filter((line) => line.trim());
    if (lines.length < 2) return { headers: [], rows: [] };
    const parseLine = (line) =>
      line
        .split(/,(?=(?:(?:[^\"]*\"){2})*[^\"]*$)/)
        .map((part) => part.trim().replace(/^\"|\"$/g, ""));
    const headers = parseLine(lines[0]);
    const rows = lines.slice(1).map((line) => {
      const values = parseLine(line);
      const row = {};
      headers.forEach((header, i) => {
        row[header] = values[i] || "";
      });
      return row;
    });
    return { headers, rows };
  }

  function updatePreviewFromCsv(file) {
    if (!file) {
      csvMappingState.headers = [];
      csvMappingState.rows = [];
      csvMappingState.mapping = {};
      csvMappingState.unresolvedRequired = [];
      renderCsvMapper();
      refreshPreviewFromCurrentState();
      return;
    }
    file
      .text()
      .then((text) => {
        const parsed = parseCsvRows(text);
        csvMappingState.headers = parsed.headers;
        csvMappingState.rows = parsed.rows;
        csvMappingState.mapping = inferAutoMapping(parsed.headers);
        csvMappingState.unresolvedRequired = calculateUnresolvedRequired();
        renderCsvMapper();
        refreshPreviewFromCurrentState();
      })
      .catch(() => {
        csvMappingState.headers = [];
        csvMappingState.rows = [];
        csvMappingState.mapping = {};
        csvMappingState.unresolvedRequired = [];
        renderCsvMapper();
        refreshPreviewFromCurrentState();
      });
  }

  function renderLivePreview() {
    const payload = gatherPayload();
    const regularFamily = fontPreviewMap[payload.fontName] || "inherit";
    const scriptFamily =
      payload.scriptFont === "None"
        ? regularFamily
        : fontPreviewMap[payload.scriptFont] || "inherit";
    const regularCssFamily = regularFamily.replaceAll('"', "'");
    const scriptCssFamily = scriptFamily.replaceAll('"', "'");
    const regularSize = Number.parseFloat(payload.fontSize) || 9;
    const scriptSize = Number.parseFloat(payload.scriptFontSize) || regularSize;
    const esc = (value) =>
      String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    const title = workflowType === "ranks" ? "Cub Scout Rank Card" : "Cub Scout Award Certificate";
    const detailLine =
      workflowType === "ranks"
        ? `earned the rank of ${esc(previewData.award)}`
        : `for completing ${esc(previewData.award)}`;

    livePreview.innerHTML = `
      <div class="preview-meta">
        <span>${esc(previewData.date)}</span>
        <span>${esc(previewData.pack)}</span>
      </div>
      <h3 class="preview-title">${title}</h3>
      <p class="preview-line" style="font-family:${regularCssFamily};font-size:${regularSize}px;">
        ${esc(previewData.scout)}
      </p>
      <p class="preview-line" style="font-family:${regularCssFamily};font-size:${regularSize}px;">
        ${detailLine}
      </p>
      <div class="preview-sig-row">
        <div class="preview-sig">
          <div class="preview-sig-name" style="font-family:${scriptCssFamily};font-size:${scriptSize}px;">
            ${esc(previewData.denLeader)}
          </div>
          <div class="preview-sig-label">Den Leader</div>
        </div>
        <div class="preview-sig">
          <div class="preview-sig-name" style="font-family:${scriptCssFamily};font-size:${scriptSize}px;">
            ${esc(previewData.cubmaster)}
          </div>
          <div class="preview-sig-label">Cubmaster</div>
        </div>
      </div>
    `;
  }

  function renderValidationReport(report) {
    if (!report) {
      validationPanel.innerHTML = `<div class="placeholder">Run CSV validation to see row-level checks.</div>`;
      return;
    }

    const errors = report.errors || [];
    const warnings = report.warnings || [];
    const summaryClass = errors.length ? "error" : warnings.length ? "warn" : "success";
    const esc = (value) =>
      String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    const renderList = (title, items) => {
      if (!items.length) return "";
      return `
        <div class="validation-block">
          <strong>${esc(title)}</strong>
          <ul>
            ${items.map((item) => `<li>${esc(item)}</li>`).join("")}
          </ul>
        </div>
      `;
    };

    validationPanel.innerHTML = `
      <div class="validation-summary ${summaryClass}">
        Rows: ${report.row_count} • Headers: ${report.header_count} • Errors: ${errors.length} • Warnings: ${warnings.length}
      </div>
      ${renderList("Errors", errors)}
      ${renderList("Warnings", warnings)}
    `;
  }

  async function validateCsv() {
    const file = csvFile.files[0];
    if (!file) {
      setStatus("Please select a CSV file.", "error");
      return;
    }

    if (csvMappingState.unresolvedRequired.length) {
      renderCsvMapper();
      setStatus(
        `Map required fields before validation: ${csvMappingState.unresolvedRequired.join(", ")}`,
        "error",
      );
      return;
    }

    const payload = gatherPayload();
    validateBtn.disabled = true;
    setStatus("Validating CSV...", "info");
    const formData = new FormData();
    formData.append("csv", file);
    formData.append("workflow", payload.workflow);
    if (payload.rank) {
      formData.append("rank", payload.rank);
    }
    formData.append("csvMapping", JSON.stringify(currentCsvMappingPayload()));

    try {
      const response = await fetch("/validate-csv", { method: "POST", body: formData });
      const report = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(report.error || "CSV validation failed.");
      }
      renderValidationReport(report);
      if (report.errors?.length) {
        setStatus(`Validation found ${report.errors.length} error(s).`, "error");
      } else if (report.warnings?.length) {
        setStatus(`Validation passed with ${report.warnings.length} warning(s).`, "warn");
      } else {
        setStatus("Validation passed with no issues.", "success");
      }
    } catch (err) {
      setStatus(err.message, "error");
    } finally {
      validateBtn.disabled = false;
    }
  }

  function downloadNameFromResponse(response, fallbackName) {
    const header = response.headers.get("Content-Disposition") || "";
    const match = header.match(/filename=\"?([^\";]+)\"?/i);
    return match ? match[1] : fallbackName;
  }

  async function generatePdf() {
    const file = csvFile.files[0];
    if (!file) {
      setStatus("Please select a CSV file.", "error");
      return;
    }

    if (csvMappingState.unresolvedRequired.length) {
      renderCsvMapper();
      setStatus(
        `Map required fields before generating: ${csvMappingState.unresolvedRequired.join(", ")}`,
        "error",
      );
      return;
    }

    const payload = gatherPayload();
    const formData = new FormData();
    formData.append("csv", file);
    formData.append("workflow", payload.workflow);
    if (payload.rank) {
      formData.append("rank", payload.rank);
    }
    formData.append("csvMapping", JSON.stringify(currentCsvMappingPayload()));
    formData.append("fontName", payload.fontName);
    formData.append("scriptFont", payload.scriptFont);
    formData.append("shiftLeft", payload.shiftLeft);
    formData.append("shiftDown", payload.shiftDown);
    formData.append("fontSize", payload.fontSize);
    formData.append("scriptFontSize", payload.scriptFontSize);
    formData.append("outputName", payload.outputName);
    formData.append("outputMode", payload.outputMode);

    generateBtn.disabled = true;
    setStatus("Generating file...", "info");

    try {
      const response = await fetch("/generate", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        if (data.report) {
          renderValidationReport(data.report);
        }
        throw new Error(data.error || "Failed to generate PDF.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const fallbackName =
        payload.outputMode === "per_scout_zip"
          ? `${payload.outputName.replace(/\.pdf$/i, "") || "scout_awards"}.zip`
          : payload.outputName;
      const downloadName = downloadNameFromResponse(response, fallbackName);
      downloadPanel.innerHTML = `
        <div>
          <strong>${downloadName}</strong>
          <p style="margin: 6px 0; color: #64748b;">Ready to download.</p>
          <a href="${url}" download="${downloadName}">Download File</a>
        </div>
      `;
      setStatus("File generated successfully.", "success");
    } catch (err) {
      setStatus(err.message, "error");
    } finally {
      generateBtn.disabled = false;
    }
  }

  csvFile.addEventListener("change", () => {
    const file = csvFile.files[0];
    csvName.textContent = file ? file.name : "No file selected";
    updatePreviewFromCsv(file);
  });

  Object.values(fields).forEach((field) => {
    field.addEventListener("change", () => {
      setFontSample();
      renderLivePreview();
    });
    field.addEventListener("input", () => {
      renderLivePreview();
    });
  });

  if (rankSelect) {
    rankSelect.addEventListener("change", () => {
      updateRankTemplateUi();
      csvMappingState.unresolvedRequired = calculateUnresolvedRequired();
      renderCsvMapper();
      refreshPreviewFromCurrentState();
    });
  }

  generateBtn.addEventListener("click", generatePdf);
  validateBtn.addEventListener("click", validateCsv);

  updateRankTemplateUi();
  setFontSample();
  renderLivePreview();
  renderValidationReport(null);
  renderCsvMapper();
}
