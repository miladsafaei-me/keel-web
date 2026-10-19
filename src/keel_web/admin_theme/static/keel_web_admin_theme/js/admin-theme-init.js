/*
  Runs in <head>, before the first paint: sets the light or dark theme and the
  collapsed sidebar from what this browser chose last time, so neither flashes.
*/
(function () {
  "use strict";
  var root = document.documentElement;
  var stored = null;
  var collapsed = null;
  try {
    stored = window.localStorage.getItem("keel-admin-theme");
    collapsed = window.localStorage.getItem("keel-admin-sidebar");
  } catch (error) {
    stored = null;
  }
  var choice = stored || root.getAttribute("data-theme-default") || "auto";
  if (choice !== "light" && choice !== "dark") {
    choice = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  root.setAttribute("data-theme", choice);
  if (collapsed === "collapsed") {
    root.classList.add("kat-sidebar-collapsed");
  }
})();
