const menuToggle = document.getElementById("menuToggle");
const menuPanel = document.getElementById("menuPanel");

if (menuToggle && menuPanel) {
  const closeMenu = () => {
    menuPanel.hidden = true;
    menuToggle.setAttribute("aria-expanded", "false");
  };

  const openMenu = () => {
    menuPanel.hidden = false;
    menuToggle.setAttribute("aria-expanded", "true");
  };

  closeMenu();

  menuToggle.addEventListener("click", () => {
    const isOpen = menuToggle.getAttribute("aria-expanded") === "true";
    if (isOpen) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (!menuPanel.contains(target) && !menuToggle.contains(target)) {
      closeMenu();
    }
  });

  menuPanel.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      closeMenu();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeMenu();
    }
  });
}
