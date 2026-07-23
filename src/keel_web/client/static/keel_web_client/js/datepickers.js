(function () {
  function init() {
    if (typeof window.flatpickr !== "function") return;
    document.querySelectorAll("[data-datepicker]:not(.flatpickr-input)").forEach(function (el) {
      window.flatpickr(el, {
        dateFormat: "Y-m-d",
        altInput: true,
        altFormat: "M j, Y",
        minDate: el.dataset.minDate || "today",
        allowInput: true,
        disableMobile: true,
      });
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
