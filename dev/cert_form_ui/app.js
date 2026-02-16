const csvFile = document.getElementById("csvFile");
const csvName = document.getElementById("csvName");
const status = document.getElementById("status");
const livePreview = document.getElementById("livePreview");
const downloadPanel = document.getElementById("downloadPanel");
const generateBtn = document.getElementById("generateBtn");
const fontSample = document.getElementById("fontSample");
const scriptSample = document.getElementById("scriptSample");

const fields = {
  fontName: document.getElementById("fontName"),
  scriptFont: document.getElementById("scriptFont"),
  shiftLeft: document.getElementById("shiftLeft"),
  shiftDown: document.getElementById("shiftDown"),
  fontSize: document.getElementById("fontSize"),
  scriptFontSize: document.getElementById("scriptFontSize"),
  outputName: document.getElementById("outputName"),
};

const fontPreviewMap = {
  Helvetica: "Helvetica, Arial, sans-serif",
  TimesRoman: "Times New Roman, Times, serif",
  Courier: "Courier New, Courier, monospace",
  Alegreya: "\"Alegreya\", Georgia, serif",
  Archivo: "\"Archivo\", \"Arial Narrow\", sans-serif",
  FiraSans: "\"Fira Sans\", Arial, sans-serif",
  Bangers: "\"Bangers\", \"Impact\", sans-serif",
  CabinSketch: "\"Cabin Sketch\", \"Comic Sans MS\", cursive",
  LilitaOne: "\"Lilita One\", \"Arial Black\", sans-serif",
  Righteous: "\"Righteous\", \"Trebuchet MS\", sans-serif",
  DejaVuSerif: "\"DejaVu Serif\", Georgia, serif",
  DejaVuSans: "\"DejaVu Sans\", Verdana, sans-serif",
  DejaVuSansMono: "\"DejaVu Sans Mono\", \"Courier New\", monospace",
  PatrickHand: "\"Patrick Hand\", cursive",
  PermanentMarker: "\"Permanent Marker\", cursive",
  DejaVuSerifItalic: "\"DejaVu Serif\", Georgia, serif",
  DejaVuSansOblique: "\"DejaVu Sans\", Verdana, sans-serif",
};

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

function gatherPayload() {
  return {
    fontName: fields.fontName.value,
    scriptFont: fields.scriptFont.value,
    shiftLeft: fields.shiftLeft.value,
    shiftDown: fields.shiftDown.value,
    fontSize: fields.fontSize.value,
    scriptFontSize: fields.scriptFontSize.value,
    outputName: fields.outputName.value,
  };
}

const defaultPreview = {
  date: "02/22/2026",
  pack: "Pack 202",
  scout: "Piney Knotts",
  award: "Badge to the Bone",
  denLeader: "Ranger Barkley",
  cubmaster: "Twig Timberly",
};

let previewData = { ...defaultPreview };

function parseCsvRows(text) {
  const lines = text.split(/\r?\n/).filter((line) => line.trim());
  if (lines.length < 2) return [];
  const parseLine = (line) =>
    line
      .split(/,(?=(?:(?:[^\"]*\"){2})*[^\"]*$)/)
      .map((part) => part.trim().replace(/^\"|\"$/g, ""));
  const headers = parseLine(lines[0]);
  return lines.slice(1).map((line) => {
    const values = parseLine(line);
    const row = {};
    headers.forEach((header, i) => {
      row[header] = values[i] || "";
    });
    return row;
  });
}

function updatePreviewFromCsv(file) {
  if (!file) {
    previewData = { ...defaultPreview };
    renderLivePreview();
    return;
  }
  file
    .text()
    .then((text) => {
      const rows = parseCsvRows(text);
      if (!rows.length) {
        previewData = { ...defaultPreview };
        renderLivePreview();
        return;
      }
      const row = rows[0];
      previewData = {
        date: row["Date"] || defaultPreview.date,
        pack: row["Pack Number"] || defaultPreview.pack,
        scout: row["Scout Name"] || defaultPreview.scout,
        award: row["Award Name"] || defaultPreview.award,
        denLeader: row["Den Leader"] || defaultPreview.denLeader,
        cubmaster: row["Cubmaster"] || defaultPreview.cubmaster,
      };
      renderLivePreview();
    })
    .catch(() => {
      previewData = { ...defaultPreview };
      renderLivePreview();
    });
}

function renderLivePreview() {
  const payload = gatherPayload();
  const regularFamily = fontPreviewMap[payload.fontName] || "inherit";
  const scriptFamily =
    payload.scriptFont === "None"
      ? regularFamily
      : fontPreviewMap[payload.scriptFont] || "inherit";
  const regularCssFamily = regularFamily.replaceAll("\"", "'");
  const scriptCssFamily = scriptFamily.replaceAll("\"", "'");
  const regularSize = Number.parseFloat(payload.fontSize) || 9;
  const scriptSize = Number.parseFloat(payload.scriptFontSize) || regularSize;
  const esc = (value) =>
    String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll("\"", "&quot;")
      .replaceAll("'", "&#39;");
  livePreview.innerHTML = `
    <div class="preview-meta">
      <span>${esc(previewData.date)}</span>
      <span>${esc(previewData.pack)}</span>
    </div>
    <h3 class="preview-title">Cub Scout Award Certificate</h3>
    <p class="preview-line" style="font-family:${regularCssFamily};font-size:${regularSize}px;">
      ${esc(previewData.scout)}
    </p>
    <p class="preview-line" style="font-family:${regularCssFamily};font-size:${regularSize}px;">
      for completing ${esc(previewData.award)}
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

async function generatePdf() {
  const file = csvFile.files[0];
  if (!file) {
    setStatus("Please select a CSV file.", "error");
    return;
  }

  const payload = gatherPayload();
  const formData = new FormData();
  formData.append("csv", file);
  formData.append("fontName", payload.fontName);
  formData.append("scriptFont", payload.scriptFont);
  formData.append("shiftLeft", payload.shiftLeft);
  formData.append("shiftDown", payload.shiftDown);
  formData.append("fontSize", payload.fontSize);
  formData.append("scriptFontSize", payload.scriptFontSize);
  formData.append("outputName", payload.outputName);

  generateBtn.disabled = true;
  setStatus("Generating PDF...", "info");

  try {
    const response = await fetch("/generate", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Failed to generate PDF.");
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    downloadPanel.innerHTML = `
      <div>
        <strong>${payload.outputName}</strong>
        <p style="margin: 6px 0; color: #64748b;">Ready to download.</p>
        <a href="${url}" download="${payload.outputName}">Download PDF</a>
      </div>
    `;
    setStatus("PDF generated successfully.", "success");
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

generateBtn.addEventListener("click", generatePdf);

setFontSample();
renderLivePreview();
