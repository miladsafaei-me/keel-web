/*
  The admin theme's behaviour: the sidebar (collapse on desktop, drawer on small
  screens), the light/dark switch, the user menu and the list-filter drawer.
  Everything is wired by data-kat-* attributes through one delegated listener.
*/
(function () {
  "use strict";

  var root = document.documentElement;
  var desktop = window.matchMedia("(min-width: 1024px)");
  var lastFocus = null;

  function store(key, value) {
    try {
      if (value === null) {
        window.localStorage.removeItem(key);
      } else {
        window.localStorage.setItem(key, value);
      }
    } catch (error) {
      /* Storage can be blocked; the page still works without it. */
    }
  }

  function setExpanded(selector, expanded) {
    document.querySelectorAll(selector).forEach(function (button) {
      button.setAttribute("aria-expanded", expanded ? "true" : "false");
    });
  }

  function syncSidebarState() {
    var expanded = desktop.matches
      ? !root.classList.contains("kat-sidebar-collapsed")
      : root.classList.contains("kat-sidebar-open");
    setExpanded("[data-kat-sidebar-toggle]", expanded);
  }

  function toggleSidebar() {
    if (desktop.matches) {
      var collapsed = root.classList.toggle("kat-sidebar-collapsed");
      store("keel-admin-sidebar", collapsed ? "collapsed" : null);
    } else {
      root.classList.toggle("kat-sidebar-open");
    }
    syncSidebarState();
  }

  function closeSidebar() {
    root.classList.remove("kat-sidebar-open");
    syncSidebarState();
  }

  function syncThemeButtons() {
    var dark = root.getAttribute("data-theme") === "dark";
    document.querySelectorAll("[data-kat-theme-toggle]").forEach(function (button) {
      button.setAttribute("aria-pressed", dark ? "true" : "false");
    });
  }

  function toggleTheme() {
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    store("keel-admin-theme", next);
    syncThemeButtons();
  }

  function menuPanel(button) {
    return document.getElementById(button.getAttribute("aria-controls"));
  }

  function closeMenus(except) {
    document.querySelectorAll("[data-kat-menu-toggle][aria-expanded='true']").forEach(function (button) {
      if (button === except) {
        return;
      }
      button.setAttribute("aria-expanded", "false");
      var panel = menuPanel(button);
      if (panel) {
        panel.hidden = true;
      }
    });
  }

  function toggleMenu(button) {
    var panel = menuPanel(button);
    if (!panel) {
      return;
    }
    var open = panel.hidden;
    closeMenus(button);
    panel.hidden = !open;
    button.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function openDrawer(button) {
    var drawer = document.getElementById(button.getAttribute("data-kat-drawer-open"));
    if (!drawer) {
      return;
    }
    lastFocus = button;
    drawer.hidden = false;
    root.classList.add("kat-drawer-open");
    button.setAttribute("aria-expanded", "true");
    var target = drawer.querySelector("[data-kat-drawer-close].kat-icon-btn, a, button");
    if (target) {
      target.focus();
    }
  }

  function closeDrawers() {
    document.querySelectorAll(".kat-drawer:not([hidden])").forEach(function (drawer) {
      drawer.hidden = true;
    });
    root.classList.remove("kat-drawer-open");
    setExpanded("[data-kat-drawer-open]", false);
    if (lastFocus) {
      lastFocus.focus();
      lastFocus = null;
    }
  }

  document.addEventListener("click", function (event) {
    var target = event.target;
    var control = target.closest("[data-kat-sidebar-toggle]");
    if (control) {
      toggleSidebar();
      return;
    }
    if (target.closest("[data-kat-sidebar-close]")) {
      closeSidebar();
      return;
    }
    if (target.closest("[data-kat-theme-toggle]")) {
      toggleTheme();
      return;
    }
    control = target.closest("[data-kat-menu-toggle]");
    if (control) {
      toggleMenu(control);
      return;
    }
    control = target.closest("[data-kat-drawer-open]");
    if (control) {
      openDrawer(control);
      return;
    }
    if (target.closest("[data-kat-drawer-close]")) {
      closeDrawers();
      return;
    }
    if (!target.closest("[data-kat-menu]")) {
      closeMenus(null);
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") {
      return;
    }
    closeMenus(null);
    closeDrawers();
    closeSidebar();
  });

  desktop.addEventListener("change", function () {
    root.classList.remove("kat-sidebar-open");
    syncSidebarState();
  });

  syncSidebarState();
  syncThemeButtons();
})();
