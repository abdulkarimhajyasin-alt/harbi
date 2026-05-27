document.addEventListener("click", (event) => {
  if (event.target.closest("[data-table-action]")) {
    event.stopPropagation();
  }

  const openButton = event.target.closest("[data-open-modal]");
  if (openButton) {
    const modal = document.getElementById(openButton.dataset.openModal);
    if (modal) {
      modal.classList.add("is-open");
      modal.setAttribute("aria-hidden", "false");
      const input = modal.querySelector("input");
      if (input) input.focus();
    }
  }

  if (event.target.matches("[data-close-modal]") || event.target.classList.contains("modal")) {
    const modal = event.target.closest(".modal");
    if (modal) {
      modal.classList.remove("is-open");
      modal.setAttribute("aria-hidden", "true");
    }
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  document.querySelectorAll(".modal.is-open").forEach((modal) => {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
  });
});
