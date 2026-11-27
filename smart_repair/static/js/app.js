document.documentElement.classList.add("js-ready");

document.addEventListener("DOMContentLoaded", () => {
  document.body.classList.add("ui-loaded");
  const toggle = document.querySelector("[data-menu-toggle]");
  const desktopMenu = window.matchMedia("(min-width: 821px)");
  const setToggleState = (expanded) => {
    toggle?.setAttribute("aria-expanded", String(expanded));
    toggle?.setAttribute(
      "aria-label",
      expanded ? "Collapse navigation" : "Expand navigation",
    );
    toggle?.setAttribute(
      "title",
      expanded ? "Collapse sidebar" : "Expand sidebar",
    );
  };
  const savedSidebarState = (() => {
    try {
      return window.localStorage.getItem("smart-repair-sidebar");
    } catch {
      return null;
    }
  })();
  if (desktopMenu.matches && savedSidebarState === "collapsed") {
    document.body.classList.add("sidebar-collapsed");
  }
  setToggleState(
    desktopMenu.matches
      ? !document.body.classList.contains("sidebar-collapsed")
      : false,
  );
  const closeMenu = () => {
    document.body.classList.remove("menu-open");
    if (!desktopMenu.matches) setToggleState(false);
  };
  toggle?.addEventListener("click", () => {
    if (desktopMenu.matches) {
      const collapsed = document.body.classList.toggle("sidebar-collapsed");
      setToggleState(!collapsed);
      try {
        window.localStorage.setItem(
          "smart-repair-sidebar",
          collapsed ? "collapsed" : "expanded",
        );
      } catch {
        // Storage can be unavailable in a private browsing context.
      }
      return;
    }
    const open = document.body.classList.toggle("menu-open");
    setToggleState(open);
  });
  document
    .querySelector("[data-menu-close]")
    ?.addEventListener("click", closeMenu);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
  desktopMenu.addEventListener("change", (event) => {
    document.body.classList.remove("menu-open");
    if (event.matches) {
      let collapsed = false;
      try {
        collapsed =
          window.localStorage.getItem("smart-repair-sidebar") === "collapsed";
      } catch {
        collapsed = false;
      }
      document.body.classList.toggle("sidebar-collapsed", collapsed);
      setToggleState(!collapsed);
    } else {
      document.body.classList.remove("sidebar-collapsed");
      setToggleState(false);
    }
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
  document.querySelectorAll("[data-auto-submit]").forEach((field) =>
    field.addEventListener("change", () => field.form?.requestSubmit()),
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
    ".page-heading, .welcome-banner, .metric-card, .panel, .resource-card, " +
      ".device-card, .landing-hero > div, .device-strip, .how-section, " +
      ".steps-grid > article, .landing-cta, .auth-layout",
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

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const precisePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  const spaciousViewport = window.matchMedia("(min-width: 821px)");
  const scrollMeter = document.createElement("div");
  scrollMeter.className = "scroll-meter";
  scrollMeter.setAttribute("aria-hidden", "true");
  document.body.append(scrollMeter);
  const cursorLight = document.createElement("div");
  cursorLight.className = "cursor-light";
  cursorLight.setAttribute("aria-hidden", "true");
  document.body.append(cursorLight);
  let cursorFrame = 0;
  document.addEventListener("pointermove", (event) => {
    if (!precisePointer.matches || !spaciousViewport.matches || reducedMotion.matches) return;
    if (cursorFrame) cancelAnimationFrame(cursorFrame);
    cursorFrame = requestAnimationFrame(() => {
      cursorLight.style.setProperty("--cursor-x", `${event.clientX}px`);
      cursorLight.style.setProperty("--cursor-y", `${event.clientY}px`);
      cursorLight.classList.add("is-active");
    });
  });
  document.documentElement.addEventListener("mouseleave", () => {
    cursorLight.classList.remove("is-active");
  });

  let motionFrame = 0;
  const updateScrollMotion = () => {
    motionFrame = 0;
    const scrollRange = document.documentElement.scrollHeight - window.innerHeight;
    const progress = scrollRange > 0 ? window.scrollY / scrollRange : 0;
    scrollMeter.style.setProperty("--scroll-progress", String(Math.min(progress, 1)));
    if (reducedMotion.matches) return;
    document.documentElement.style.setProperty(
      "--page-parallax",
      `${Math.min(window.scrollY * 0.12, 96).toFixed(2)}px`,
    );
  };
  const requestScrollMotion = () => {
    if (!motionFrame) motionFrame = requestAnimationFrame(updateScrollMotion);
  };
  window.addEventListener("scroll", requestScrollMotion, { passive: true });
  window.addEventListener("resize", requestScrollMotion, { passive: true });
  updateScrollMotion();

  const tiltTargets = document.querySelectorAll(
    ".metric-card, .device-card, .resource-card, .steps-grid > article, " +
      ".visual-symptom-option, .landing-visual",
  );
  tiltTargets.forEach((target) => {
    target.classList.add("motion-3d");
    let tiltFrame = 0;
    const resetTilt = () => {
      if (tiltFrame) cancelAnimationFrame(tiltFrame);
      target.style.removeProperty("transform");
      target.style.removeProperty("--pointer-x");
      target.style.removeProperty("--pointer-y");
      target.classList.remove("is-tilting");
    };
    target.addEventListener("pointermove", (event) => {
      if (
        !precisePointer.matches ||
        !spaciousViewport.matches ||
        reducedMotion.matches
      ) return;
      const bounds = target.getBoundingClientRect();
      const x = (event.clientX - bounds.left) / bounds.width;
      const y = (event.clientY - bounds.top) / bounds.height;
      if (tiltFrame) cancelAnimationFrame(tiltFrame);
      tiltFrame = requestAnimationFrame(() => {
        target.classList.add("is-tilting");
        target.style.setProperty("--pointer-x", `${(x * 100).toFixed(1)}%`);
        target.style.setProperty("--pointer-y", `${(y * 100).toFixed(1)}%`);
        target.style.transform = `perspective(950px) rotateX(${((0.5 - y) * 5).toFixed(2)}deg) rotateY(${((x - 0.5) * 6).toFixed(2)}deg) translateY(-3px)`;
      });
    });
    target.addEventListener("pointerleave", resetTilt);
    target.addEventListener("pointercancel", resetTilt);
  });

  reducedMotion.addEventListener("change", () => {
    if (reducedMotion.matches) {
      document.documentElement.style.setProperty("--page-parallax", "0px");
      tiltTargets.forEach((target) => {
        target.style.removeProperty("transform");
        target.classList.remove("is-tilting");
      });
    }
  });
  spaciousViewport.addEventListener("change", (event) => {
    if (!event.matches) {
      tiltTargets.forEach((target) => {
        target.style.removeProperty("transform");
        target.classList.remove("is-tilting");
      });
    }
  });
});
