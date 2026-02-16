const csvFile = document.getElementById("csvFile");
const csvName = document.getElementById("csvName");
const status = document.getElementById("status");
const outputArea = document.getElementById("outputArea");
const generateBtn = document.getElementById("generateBtn");
const fontSample = document.getElementById("fontSample");
const scriptSample = document.getElementById("scriptSample");

const fields = {
  fontName: document.getElementById("fontName"),
  scriptFont: document.getElementById("scriptFont"),
  shiftLeft: document.getElementById("shiftLeft"),
  shiftDown: document.getElementById("shiftDown"),
  fontSize: document.getElementById("fontSize"),
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
    outputName: fields.outputName.value,
  };
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
    outputArea.innerHTML = `
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
});

fields.fontName.addEventListener("change", setFontSample);
fields.scriptFont.addEventListener("change", setFontSample);

generateBtn.addEventListener("click", generatePdf);

setFontSample();
