document.documentElement.classList.add("js-ready");

document.addEventListener("DOMContentLoaded", () => {
  document.body.classList.add("ui-loaded");
  const toggle = document.querySelector("[data-menu-toggle]");
  const closeMenu = () => {
    document.body.classList.remove("menu-open");
    toggle?.setAttribute("aria-expanded", "false");
  };
  toggle?.addEventListener("click", () => {
    const open = document.body.classList.toggle("menu-open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  document
    .querySelector("[data-menu-close]")
    ?.addEventListener("click", closeMenu);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
  document
    .querySelectorAll("[data-dismiss]")
    .forEach((button) =>
      button.addEventListener("click", () => button.closest(".flash").remove()),
    );
  document.querySelectorAll("form[data-confirm]").forEach((form) =>
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    }),
  );
  document
    .querySelectorAll("[data-print]")
    .forEach((button) =>
      button.addEventListener("click", () => window.print()),
    );
  document.querySelectorAll("[data-back]").forEach((button) =>
    button.addEventListener("click", () => {
      if (window.history.length > 1) window.history.back();
      else window.location.assign("/");
    }),
  );
  const deviceChoice = document.querySelector('select[name="device_id"]');
  const customDevice = document.querySelector("[data-custom-device]");
  if (deviceChoice && customDevice) {
    const updateCustomDevice = () => {
      if (deviceChoice.value === "-1") customDevice.open = true;
    };
    deviceChoice.addEventListener("change", updateCustomDevice);
    updateCustomDevice();
  }

  const revealItems = document.querySelectorAll(
    ".page-heading, .welcome-banner, .metric-card, .panel, .resource-card",
  );
  revealItems.forEach((item, index) => {
    item.dataset.reveal = "";
    item.style.transitionDelay = `${Math.min(index % 6, 5) * 45}ms`;
  });
  if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -28px" },
    );
    revealItems.forEach((item) => revealObserver.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  document.querySelectorAll(".metric-card > strong").forEach((counter) => {
    const text = counter.textContent.trim();
    if (!/^\d+$/.test(text)) return;
    const target = Number.parseInt(text, 10);
    const padded = text.length > 1;
    const started = performance.now();
    const duration = 520;
    const tick = (now) => {
      const progress = Math.min((now - started) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const value = Math.round(target * eased);
      counter.textContent = padded ? String(value).padStart(text.length, "0") : value;
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

  document.addEventListener("pointerdown", (event) => {
    const button = event.target.closest(".btn");
    if (!button || button.matches(":disabled")) return;
    const bounds = button.getBoundingClientRect();
    const ripple = document.createElement("span");
    ripple.className = "btn-ripple";
    ripple.style.left = `${event.clientX - bounds.left}px`;
    ripple.style.top = `${event.clientY - bounds.top}px`;
    button.append(ripple);
    ripple.addEventListener("animationend", () => ripple.remove(), { once: true });
  });
});
