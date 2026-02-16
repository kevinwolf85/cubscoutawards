const rankSelect = document.getElementById("rankSelect");
const rankGrid = document.getElementById("rankGrid");
const rankSummary = document.getElementById("rankSummary");
const rankTemplateLink = document.getElementById("rankTemplateLink");
const rankTemplateStatus = document.getElementById("rankTemplateStatus");

const rankConfig = {
  Lion: { available: false },
  Tiger: { available: false },
  Wolf: {
    available: true,
    href: "/wolf_rank_template.csv",
    label: "Download Wolf Rank CSV Template",
    note: "Source PDF appears non-fillable, so template is derived from visible placeholders.",
  },
  Bear: { available: false },
  Webelo: { available: false },
  "Arrow of Light": { available: false },
};

function setActiveChip(rank) {
  rankGrid?.querySelectorAll(".rank-chip").forEach((chip) => {
    chip.classList.toggle("active", chip.dataset.rank === rank);
  });
}

function renderRank(rank) {
  const cfg = rankConfig[rank] || { available: false };
  setActiveChip(rank);
  if (rankSummary) {
    const title = rankSummary.querySelector("strong");
    if (title) title.textContent = rank;
  }

  if (cfg.available) {
    rankTemplateLink.textContent = cfg.label;
    rankTemplateLink.setAttribute("href", cfg.href);
    rankTemplateLink.setAttribute("download", "");
    rankTemplateLink.style.pointerEvents = "auto";
    rankTemplateLink.style.opacity = "1";
    rankTemplateStatus.textContent = cfg.note;
  } else {
    rankTemplateLink.textContent = `${rank} template coming soon`;
    rankTemplateLink.setAttribute("href", "#");
    rankTemplateLink.removeAttribute("download");
    rankTemplateLink.style.pointerEvents = "none";
    rankTemplateLink.style.opacity = "0.6";
    rankTemplateStatus.textContent = "CSV template for this rank is not added yet.";
  }
}

if (rankSelect && rankTemplateLink && rankTemplateStatus) {
  rankSelect.addEventListener("change", () => {
    renderRank(rankSelect.value);
  });

  rankGrid?.querySelectorAll(".rank-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const rank = chip.dataset.rank;
      if (!rank) return;
      rankSelect.value = rank;
      renderRank(rank);
    });
  });

  renderRank(rankSelect.value);
}
