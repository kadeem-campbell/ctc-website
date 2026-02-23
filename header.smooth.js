document.addEventListener("DOMContentLoaded", () => {
  const header = document.getElementById("ctcHeader");
  const mobileMenu = document.getElementById("ctcMobileMenu");
  
  // Guard clause if elements don't exist
  if (!header) return;

  let lastScrollTop = 0;
  const delta = 5; // Minimum scroll distance to trigger change
  const headerHeight = header.offsetHeight;
  let ticking = false;

  // Add initial state to ensure it starts visible
  header.classList.add("nav-up");

  function updateHeader() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

    // 1. Prevent action if mobile menu is open (user needs to see the menu)
    // Checks if the root/html has the open class defined in your other scripts
    const isMobileOpen = document.documentElement.classList.contains("ctc-mnav-open");
    if (isMobileOpen) {
      ticking = false;
      return;
    }

    // 2. Prevent jitter around the very top of the page
    if (Math.abs(lastScrollTop - scrollTop) <= delta) {
      ticking = false;
      return;
    }

    // 3. Logic: Scroll Down -> Hide, Scroll Up -> Show
    // Note: We check 'scrollTop > headerHeight' to avoid hiding it immediately at the very top
    if (scrollTop > lastScrollTop && scrollTop > headerHeight) {
      // Scrolling Down
      header.classList.remove("nav-up");
      header.classList.add("nav-down");
    } else {
      // Scrolling Up
      if (scrollTop + window.innerHeight < document.documentElement.scrollHeight) {
        header.classList.remove("nav-down");
        header.classList.add("nav-up");
      }
    }

    lastScrollTop = scrollTop;
    ticking = false;
  }

  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(updateHeader);
      ticking = true;
    }
  }, { passive: true });
});