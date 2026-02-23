(function () {
  const header = document.getElementById("ctcHeader");
  const toggle = document.getElementById("ctcMobileToggle");
  const menu = document.getElementById("ctcMobileMenu");
  if (!header || !toggle || !menu) return;

  const root = document.documentElement;
  const OPEN_CLASS = "ctc-mnav-open";

  const isOpen = () => root.classList.contains(OPEN_CLASS);

  const setOpen = (open) => {
    root.classList.toggle(OPEN_CLASS, open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    menu.setAttribute("aria-hidden", open ? "false" : "true");
  };

  // Smooth open/close
  toggle.addEventListener("click", () => setOpen(!isOpen()));

  // Close when clicking a link
  menu.addEventListener("click", (e) => {
    const a = e.target && e.target.closest ? e.target.closest("a") : null;
    if (a) setOpen(false);
  });

  // Close on escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") setOpen(false);
  });

  // Close if clicking outside
  document.addEventListener("click", (e) => {
    if (!isOpen()) return;
    const t = e.target;
    if (!t) return;
    if (t.closest && (t.closest("#ctcHeader") || t.closest("#ctcMobileMenu"))) return;
    setOpen(false);
  });

  // Hide on scroll down, show on scroll up (seamless)
  let lastY = window.scrollY || 0;
  let ticking = false;

  const onScroll = () => {
    if (isOpen()) return;

    const y = window.scrollY || 0;
    const delta = Math.abs(y - lastY);

    // Always visible near top
    if (y <= 8) {
      header.classList.remove("is-down");
      header.classList.add("is-up");
      lastY = y;
      return;
    }

    // Ignore tiny jitter
    if (delta < 10) {
      lastY = y;
      return;
    }

    if (y > lastY) {
      header.classList.remove("is-up");
      header.classList.add("is-down");
    } else {
      header.classList.remove("is-down");
      header.classList.add("is-up");
    }

    lastY = y;
  };

  window.addEventListener(
    "scroll",
    () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          onScroll();
          ticking = false;
        });
        ticking = true;
      }
    },
    { passive: true }
  );

  // Close menu when resizing to desktop
  window.addEventListener("resize", () => {
    if (window.innerWidth >= 900) setOpen(false);
  });

  // Initial state
  header.classList.add("is-up");
})();