/*
 * Deferred CSRF submit helper.
 *
 * Pairs with keel_web.csrf_defer.views.csrf_token_view (mounted at
 * /csrf-token/ — see keel_web/csrf_defer/urls.py). A page that opts a form
 * into this ships with NO {% csrf_token %} and NO CSRF cookie at all, which
 * is what lets the page itself be cached at the edge; this script fetches a
 * real token on demand and injects it right before the form actually posts.
 *
 * Only appropriate for a form that is incidental to the page it lives on (a
 * newsletter box, a header search field) — see the trade-off explained in
 * keel_web/csrf_defer/views.py. A page whose purpose IS the form should keep
 * the ordinary {% csrf_token %} and not use this at all.
 *
 * Usage — plain, non-JS-framework <form method="post">, no inline handlers:
 *
 *   <form method="post" action="/newsletter/" data-keel-deferred-csrf>
 *     <input type="hidden" name="csrfmiddlewaretoken" value="">
 *     <input type="email" name="email">
 *     <button type="submit">Subscribe</button>
 *   </form>
 *
 * Load this file itself with a plain <script src>, registered through the
 * host project's normal css-bundles/static pipeline — never an inline
 * <script> block and never an inline event attribute on the form.
 *
 * Behaviour:
 *   - On first focus inside the form, the token is prefetched in the
 *     background so the round trip is hidden behind the visitor's own
 *     typing.
 *   - On submit, if a token is already sitting in the hidden input (the
 *     common case once prefetch has had time to land), the form posts
 *     immediately, unmodified.
 *   - Otherwise the submit is held, the token is fetched inline, and the
 *     form is submitted once it lands.
 *   - If the fetch fails, the submission is never sent — a visible error is
 *     appended to the form instead of silently posting a request that would
 *     just 403. Style the ".keel-deferred-csrf-error" node from the host's
 *     own stylesheet if the default appearance needs to match a design.
 */
(function () {
  "use strict";

  var ENDPOINT = "/csrf-token/";
  var FORM_SELECTOR = "form[data-keel-deferred-csrf]";
  var TOKEN_FIELD = "csrfmiddlewaretoken";
  var ERROR_CLASS = "keel-deferred-csrf-error";

  function tokenInput(form) {
    return form.querySelector('input[name="' + TOKEN_FIELD + '"]');
  }

  function fetchToken(form) {
    if (form._keelCsrfPromise) {
      return form._keelCsrfPromise;
    }
    var promise = fetch(ENDPOINT, {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("deferred CSRF: token endpoint returned " + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        if (!data || !data.csrfToken) {
          throw new Error("deferred CSRF: token endpoint returned no csrfToken");
        }
        var input = tokenInput(form);
        if (input) {
          input.value = data.csrfToken;
        }
        return data.csrfToken;
      })
      .catch(function (error) {
        // Let a later attempt (another focus, another submit) retry from
        // scratch rather than being stuck replaying the same failure.
        form._keelCsrfPromise = null;
        throw error;
      });
    form._keelCsrfPromise = promise;
    return promise;
  }

  function showError(form, error) {
    var existing = form.querySelector("." + ERROR_CLASS);
    if (existing) {
      existing.parentNode.removeChild(existing);
    }
    var message =
      form.getAttribute("data-keel-deferred-csrf-error") ||
      "This form could not be prepared for submission. Please try again.";
    var node = document.createElement("p");
    node.className = ERROR_CLASS;
    node.setAttribute("role", "alert");
    node.textContent = message;
    form.appendChild(node);
    if (window.console && console.error) {
      console.error("keel deferred CSRF submit failed:", error);
    }
  }

  function onFocusIn(event) {
    var target = event.target;
    if (!target || typeof target.closest !== "function") {
      return;
    }
    var form = target.closest(FORM_SELECTOR);
    if (!form || form._keelCsrfPromise) {
      return;
    }
    // Prefetch only — a failure here is silent because the visitor has not
    // tried to submit yet; the submit handler below fetches again (and
    // surfaces the error) if this attempt did not land in time.
    fetchToken(form)["catch"](function () {});
  }

  function onSubmit(event) {
    var form = event.target;
    if (!form || typeof form.matches !== "function" || !form.matches(FORM_SELECTOR)) {
      return;
    }
    var input = tokenInput(form);
    if (input && input.value) {
      // Prefetch already landed — let the normal submit proceed unmodified.
      return;
    }
    event.preventDefault();
    fetchToken(form)
      .then(function () {
        // HTMLFormElement.submit() bypasses the "submit" event entirely, so
        // this does not re-enter onSubmit.
        form.submit();
      })
      ["catch"](function (error) {
        showError(form, error);
      });
  }

  document.addEventListener("focusin", onFocusIn, true);
  document.addEventListener("submit", onSubmit, true);
})();
