/*
 * Profile page client-side helpers.
 *
 * - Password show/hide toggle for password/email modals.
 * - phonePicker Alpine component: country dropdown + digits-only national input,
 *   with a shared phoneHelp modal that explains how to fill the field on bad input.
 */
(function () {
  "use strict";

  // ---------- Password toggle (legacy, kept for any remaining .password-toggle buttons) ----------
  document.querySelectorAll(".password-toggle").forEach(function (toggle) {
    toggle.addEventListener("click", function (e) {
      e.preventDefault();
      var targetId = toggle.getAttribute("data-target");
      if (!targetId) return;
      var input = document.getElementById(targetId);
      if (!input) return;
      var icon = toggle.querySelector("i");
      if (input.type === "password") {
        input.type = "text";
        if (icon) { icon.classList.remove("ti-eye"); icon.classList.add("ti-eye-off"); }
        toggle.setAttribute("aria-label", "Hide password");
      } else {
        input.type = "password";
        if (icon) { icon.classList.remove("ti-eye-off"); icon.classList.add("ti-eye"); }
        toggle.setAttribute("aria-label", "Show password");
      }
    });
  });

  // ---------- Telegram input — strip non-Latin characters in real time ----------
  var telegramInput = document.getElementById("id_telegram_id");
  if (telegramInput) {
    telegramInput.addEventListener("input", function () {
      var v = telegramInput.value;
      var cleaned = v.replace(/[^A-Za-z0-9_@]/g, "");
      if (cleaned !== v) {
        var caret = telegramInput.selectionStart - (v.length - cleaned.length);
        telegramInput.value = cleaned;
        try { telegramInput.setSelectionRange(caret, caret); } catch (e) {}
      }
    });
  }

  // ---------- Country list source ----------
  function loadPhoneCountries() {
    var node = document.getElementById("phone-countries-data");
    if (!node) return [];
    try {
      return JSON.parse(node.textContent || "[]");
    } catch (e) {
      return [];
    }
  }

  // ---------- Alpine component registration ----------
  document.addEventListener("alpine:init", function () {
    var ALL = loadPhoneCountries();
    var BY_ALPHA2 = {};
    ALL.forEach(function (c) { BY_ALPHA2[c.alpha2] = c; });

    function phoneHelpFor(country, label, customMessage) {
      var msg;
      if (customMessage) {
        msg = customMessage;
      } else if (country && country.sample_digits) {
        msg = "For " + country.name +
              ", enter " + country.sample_digits.length + " digits. Example: " +
              country.dial + " " + country.sample_national + ".";
      } else if (country) {
        msg = "Enter a valid phone number for " + country.name + ".";
      } else {
        msg = "Pick a country, then enter your number in digits only.";
      }
      return msg;
    }

    window.Alpine.data("phonePicker", function (opts) {
      opts = opts || {};
      return {
        all: ALL,
        open: false,
        search: "",
        selected: BY_ALPHA2[(opts.alpha2 || "").toUpperCase()] || ALL[0] || { alpha2: "", flag: "", dial: "", name: "", sample_digits: "", sample_national: "" },
        label: opts.label || "Phone",

        init: function () {
          var self = this;
          this.$nextTick(function () {
            // Apply maxlength on first paint based on the selected country.
            if (self.$refs.national) {
              self.$refs.national.setAttribute("maxlength", String(self.maxDigits()));
            }
            // If server returned an error for this field, auto-open the help modal
            // explaining how to format input for the currently selected country.
            var fieldId = self.$refs.national && self.$refs.national.id;
            if (!fieldId) return;
            var slug = fieldId.replace(/^id_/, "").replace(/_national$/, "");
            var serverError = document.querySelector('[data-phone-server-error="' + slug + '"]');
            if (serverError) {
              self.openHelp(serverError.textContent.trim());
            }
          });
        },

        get options() {
          if (!this.search) return this.all;
          var q = this.search.toLowerCase().trim();
          return this.all.filter(function (c) {
            return c.name.toLowerCase().indexOf(q) !== -1
                || c.alpha2.toLowerCase().indexOf(q) !== -1
                || c.dial.indexOf(q) !== -1
                || String(c.dial_code).indexOf(q.replace(/^\+/, "")) !== -1;
          });
        },

        select: function (c) {
          this.selected = c;
          this.open = false;
          this.search = "";
          // Truncate any over-length input to the new country's max, then re-validate.
          var el = this.$refs.national;
          if (el) {
            var max = this.maxDigits();
            el.setAttribute("maxlength", String(max));
            if (el.value && el.value.length > max) {
              el.value = el.value.slice(0, max);
            }
            if (el.value) this.validateLength();
          }
        },

        maxDigits: function () {
          var sample = this.selected && this.selected.sample_digits;
          return (sample && sample.length) || 15;
        },

        onNationalInput: function (ev) {
          // Strip non-digits AND any leading zeros in real-time. The country code
          // already handles the trunk prefix (e.g. UK 020 → enter 20, IR 0912 → enter 912).
          var el = ev.target;
          var before = el.value;
          var after = before.replace(/\D+/g, "").replace(/^0+/, "");
          // Cap at the selected country's expected digit count (E.164 max 15).
          var max = this.maxDigits();
          if (after.length > max) after = after.slice(0, max);
          if (before !== after) {
            var caret = el.selectionStart - (before.length - after.length);
            if (caret < 0) caret = 0;
            el.value = after;
            try { el.setSelectionRange(caret, caret); } catch (e) {}
          }
        },

        onNationalBlur: function () {
          var el = this.$refs.national;
          if (!el || !el.value) return;
          this.validateLength();
        },

        validateLength: function () {
          var el = this.$refs.national;
          if (!el) return;
          var val = el.value;
          var country = this.selected;
          if (!val) return;
          if (!country || !country.sample_digits) return;
          var expected = country.sample_digits.length;
          // Heuristic: warn if length is off by more than 1 from sample. Real validation
          // happens server-side via libphonenumber.
          var diff = Math.abs(val.length - expected);
          if (diff > 1) {
            this.openHelp();
          }
        },

        openHelp: function (customMessage) {
          var msg = phoneHelpFor(this.selected, this.label, customMessage);
          // Bubble to the page-level phoneHelp Alpine state.
          window.dispatchEvent(new CustomEvent("phone-help-open", {
            detail: {
              label: this.label,
              country: this.selected,
              message: msg,
            },
          }));
        },
      };
    });
  });
})();
