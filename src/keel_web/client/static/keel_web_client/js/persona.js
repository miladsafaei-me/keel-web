/*
 * Persona avatar composer — Alpine component used by the avatar modal.
 *
 * Layout: live preview always visible on the left, mode tabs (Presets / Customize / Upload)
 * on the right. Customize uses sub-tabs ("layer pills") so only one layer's options are
 * shown at a time, in a clean grid. Picking an option updates state + preview + thumbnails.
 *
 * State on submit is decided by `mode`: persona JSON / file upload / clear.
 */
(function () {
  "use strict";

  var FOLDER = {
    bg: "Background",
    body: "Body",
    skin: "Skin",
    hair: "Hair",
    facialHair: "FacialHair",
    mouth: "Mouth",
    nose: "Nose",
    eyes: "Eyes",
  };

  var LABELS = {
    bg: "Background",
    body: "Body",
    skin: "Skin",
    hair: "Hair",
    facialHair: "Facial hair",
    mouth: "Mouth",
    nose: "Nose",
    eyes: "Eyes",
  };

  // Bottom → top paint order for stacked rendering.
  var PAINT_ORDER = ["bg", "body", "skin", "hair", "facialHair", "mouth", "nose", "eyes"];

  function readJsonScript(id, fallback) {
    var el = document.getElementById(id);
    if (!el) return fallback;
    try { return JSON.parse(el.textContent); }
    catch (e) { return fallback; }
  }

  function pickRandom(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  function personaComposer() {
    var prefix = readJsonScript("persona-static-prefix", "/static/client/img/personas/");
    var opts = {
      layerOrder: readJsonScript("persona-layer-order", []),
      choices: readJsonScript("persona-choices", {}),
      initial: readJsonScript("persona-initial", {}),
    };
    var initial = opts.initial || {};
    var hasInitial = PAINT_ORDER.some(function (k) { return !!initial[k]; });
    // URL of the user's previously uploaded avatar (if any). Used as the
    // preview fallback when persona state is empty and the user hasn't
    // chosen to clear or replace.
    var uploadedAvatarUrl = readJsonScript("persona-avatar-url", "");

    return {
      // ---- Reactive state used by Alpine bindings ----
      tab: hasInitial ? "customize" : "presets",
      mode: hasInitial ? "persona" : "none",
      layerOrder: opts.layerOrder,
      activeLayer: opts.layerOrder[0] || "bg",
      state: {
        bg: initial.bg || "",
        body: initial.body || "",
        skin: initial.skin || "",
        hair: initial.hair || "",
        facialHair: initial.facialHair || "",
        mouth: initial.mouth || "",
        nose: initial.nose || "",
        eyes: initial.eyes || "",
      },

      // ---- Lifecycle ----
      init: function () {
        var self = this;
        this.$nextTick(function () {
          self.renderActiveLayerGrid();
          self.refreshPreview();
        });
      },

      // ---- Helpers exposed to the template ----
      layerLabel: function (layer) { return LABELS[layer] || layer; },
      layerCount: function (layer) {
        var n = (opts.choices[layer] || []).length;
        if (!n) return "";
        // Subtract the empty sentinel for facialHair so the count matches "real" options.
        return (layer === "facialHair" ? n - 1 : n) + " options";
      },

      // ---- Layer pill switching ----
      setActiveLayer: function (layer) {
        this.activeLayer = layer;
        this.renderActiveLayerGrid();
      },

      // ---- Render only the currently-active layer's options ----
      renderActiveLayerGrid: function () {
        var grid = document.getElementById("layer-options");
        if (!grid) return;
        var self = this;
        var layer = this.activeLayer;
        var choices = opts.choices[layer] || [];
        grid.innerHTML = "";
        choices.forEach(function (file) {
          grid.appendChild(self.makePickButton(layer, file));
        });
        this.refreshActiveStates();
      },

      // ---- Pick button (single option) ----
      makePickButton: function (layer, file) {
        var self = this;
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className =
          "persona-pick relative aspect-square w-full overflow-hidden rounded-full " +
          "border-2 border-gray-200 bg-gray-100 transition " +
          "hover:-translate-y-0.5 hover:border-gray-400 hover:shadow-theme-sm " +
          "dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-500";
        btn.dataset.layer = layer;
        btn.dataset.file = file;

        if (file === "") {
          btn.innerHTML =
            '<span class="absolute inset-0 flex items-center justify-center text-[10px] font-semibold uppercase tracking-wider text-gray-400">None</span>';
        } else {
          btn.innerHTML = self.thumbnailHtml(layer, file);
        }

        btn.addEventListener("click", function () {
          self.state[layer] = file;
          self.mode = "persona";
          self.refreshPreview();
          self.refreshActiveStates();
          // Re-render thumbnails because the body/skin baseline used inside other
          // pickers may have changed; cheap because we only rebuild the active layer.
          self.renderActiveLayerGrid();
          var fileInput = document.getElementById("avatar-upload-input");
          if (fileInput) fileInput.value = "";
        });
        return btn;
      },

      // ---- Build a contextual thumbnail (mini-head with this layer overlaid) ----
      thumbnailHtml: function (layer, file) {
        var s = this.state;
        if (layer === "bg") {
          return img(prefix + "Background/" + file);
        }
        if (layer === "body") {
          return img(prefix + "Background/" + (s.bg || "white.svg")) +
                 img(prefix + "Body/" + file);
        }
        if (layer === "skin") {
          return img(prefix + "Background/" + (s.bg || "white.svg")) +
                 img(prefix + "Body/" + (s.body || "oval.svg")) +
                 img(prefix + "Skin/" + file);
        }
        // Face features (hair/mouth/nose/eyes/facialHair): layer over a neutral head.
        var html = img(prefix + "Background/" + (s.bg || "white.svg")) +
                   img(prefix + "Body/"       + (s.body || "oval.svg")) +
                   img(prefix + "Skin/"       + (s.skin || "head-skin1.svg"));
        html += img(prefix + FOLDER[layer] + "/" + file);
        return html;
      },

      refreshActiveStates: function () {
        var s = this.state;
        document.querySelectorAll(".persona-pick").forEach(function (btn) {
          var layer = btn.dataset.layer;
          var file = btn.dataset.file;
          var active = (s[layer] || "") === file;
          btn.classList.toggle("ring-2", active);
          btn.classList.toggle("ring-brand-500", active);
          btn.classList.toggle("border-brand-500", active);
        });
      },

      // ---- Live preview rendering ----
      refreshPreview: function () {
        var preview = document.getElementById("persona-preview");
        if (!preview) return;
        var s = this.state;
        var hasAny = PAINT_ORDER.some(function (k) { return !!s[k]; });
        if (hasAny) {
          var html = "";
          PAINT_ORDER.forEach(function (layer) {
            var file = s[layer];
            if (!file) return;
            html += img(prefix + FOLDER[layer] + "/" + file);
          });
          preview.innerHTML = html;
          return;
        }
        // No persona state: fall back to the previously uploaded image,
        // unless the user explicitly chose to clear it.
        if (uploadedAvatarUrl && this.mode !== "clear") {
          preview.innerHTML =
            '<img src="' + uploadedAvatarUrl + '" alt="" class="absolute inset-0 h-full w-full object-cover" aria-hidden="true">';
          return;
        }
        preview.innerHTML =
          '<span class="absolute inset-0 flex items-center justify-center text-xs text-gray-400 dark:text-gray-500">No avatar yet</span>';
      },

      // ---- Actions ----
      applyPreset: function (config) {
        var self = this;
        Object.keys(self.state).forEach(function (k) {
          self.state[k] = (config && config[k]) || "";
        });
        self.mode = "persona";
        self.tab = "customize";
        self.activeLayer = self.layerOrder[0] || "bg";
        self.$nextTick(function () {
          self.refreshPreview();
          self.renderActiveLayerGrid();
        });
        var fileInput = document.getElementById("avatar-upload-input");
        if (fileInput) fileInput.value = "";
      },

      randomLayer: function (layer) {
        var pool = (opts.choices[layer] || []).filter(function (f) { return f !== ""; });
        if (!pool.length) return;
        this.state[layer] = pickRandom(pool);
        this.mode = "persona";
        this.refreshPreview();
        this.renderActiveLayerGrid();
      },

      randomAll: function () {
        var self = this;
        opts.layerOrder.forEach(function (layer) {
          // 60% of "Surprise me" rolls keep facial hair off so most personas look clean.
          if (layer === "facialHair" && Math.random() < 0.6) {
            self.state[layer] = "";
            return;
          }
          var pool = (opts.choices[layer] || []).filter(function (f) { return f !== ""; });
          self.state[layer] = pool.length ? pickRandom(pool) : "";
        });
        self.mode = "persona";
        self.refreshPreview();
        self.renderActiveLayerGrid();
      },

      onFileChange: function (e) {
        var fileInput = e.target;
        if (!fileInput.files || !fileInput.files[0]) return;
        this.mode = "upload";
        var reader = new FileReader();
        reader.onload = function (ev) {
          var preview = document.getElementById("persona-preview");
          if (preview) {
            preview.innerHTML =
              '<img src="' + ev.target.result + '" class="absolute inset-0 h-full w-full object-cover" alt="">';
          }
        };
        reader.readAsDataURL(fileInput.files[0]);
      },

      onClear: function () {
        var self = this;
        self.mode = "clear";
        Object.keys(self.state).forEach(function (k) { self.state[k] = ""; });
        self.refreshPreview();
        self.renderActiveLayerGrid();
        var fileInput = document.getElementById("avatar-upload-input");
        if (fileInput) fileInput.value = "";
      },

      onSubmit: function (e) {
        var personaInput = document.getElementById("persona-config-input");
        var clearInput = document.getElementById("persona-clear-input");
        var fileInput = document.getElementById("avatar-upload-input");

        if (personaInput) personaInput.value = "";
        if (clearInput) clearInput.value = "";

        if (this.mode === "clear") {
          if (clearInput) clearInput.value = "1";
          if (fileInput) fileInput.value = "";
          return true;
        }
        if (this.mode === "upload") {
          if (!fileInput || !fileInput.files || !fileInput.files[0]) {
            e.preventDefault();
            return false;
          }
          return true;
        }
        if (this.mode === "persona") {
          if (personaInput) personaInput.value = JSON.stringify(this.state);
          if (fileInput) fileInput.value = "";
          return true;
        }
        e.preventDefault();
        return false;
      },
    };
  }

  function img(url) {
    return '<img src="' + url + '" class="absolute inset-0 h-full w-full" alt="" aria-hidden="true">';
  }

  // Expose globally so `x-data="personaComposer()"` resolves it regardless of
  // whether persona.js loads before or after Alpine.
  window.personaComposer = personaComposer;
})();
