/* SYSTEM-C Platform : petits comportements progressifs, sans dépendance.
   - Confirmation des actions irréversibles (audit A1) : attribut data-confirm.
   - Retour d'envoi : le bouton signale l'envoi en cours et évite un double envoi.
   - Résumé d'erreurs : reçoit le focus après un envoi refusé.
   Sans JavaScript, tout reste utilisable : le serveur applique toujours ses règles. */
(function () {
  "use strict";

  document.addEventListener("submit", function (event) {
    var form = event.target;
    var submitter = event.submitter;
    var message = (submitter && submitter.getAttribute("data-confirm")) || form.getAttribute("data-confirm");
    if (message && !window.confirm(message)) {
      event.preventDefault();
      return;
    }
    if (form.method && form.method.toLowerCase() === "post" && submitter) {
      // Après la construction des données du formulaire, pour garder la valeur du bouton.
      window.setTimeout(function () {
        submitter.setAttribute("aria-busy", "true");
        submitter.setAttribute("aria-disabled", "true");
      }, 0);
    }
  });

  window.addEventListener("pageshow", function () {
    // Retour arrière : le navigateur peut restaurer la page avec un bouton resté occupé.
    document.querySelectorAll('[aria-busy="true"]').forEach(function (button) {
      button.removeAttribute("aria-busy");
      button.removeAttribute("aria-disabled");
    });
  });

  var summary = document.querySelector("[data-error-summary]");
  if (summary) {
    summary.focus();
  }

  // Recherche : Ctrl K (⌘ K sur Mac) place le curseur dans le champ de la barre du haut.
  var search = document.querySelector("[data-search-shortcut]");
  if (search) {
    var mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
    var label = document.querySelector("[data-shortcut-label]");
    if (label && mac) { label.textContent = "\u2318 K"; }
    document.addEventListener("keydown", function (event) {
      if ((mac ? event.metaKey : event.ctrlKey) && (event.key === "k" || event.key === "K")) {
        event.preventDefault();
        search.focus();
        search.select();
      }
    });
  }

  // Graphiques : infobulle au survol et au clavier (flèches), texte posé avec textContent.
  var tip = null;
  function showTip(chart, index) {
    var zones = chart.querySelectorAll("[data-tip]");
    if (!zones.length) { return; }
    index = Math.max(0, Math.min(zones.length - 1, index));
    chart.setAttribute("data-current", String(index));
    var zone = zones[index];
    if (!tip) {
      tip = document.createElement("div");
      tip.className = "sc-tip";
      tip.setAttribute("role", "status");
      document.body.appendChild(tip);
    }
    tip.textContent = zone.getAttribute("data-tip");
    tip.hidden = false;
    var cross = chart.querySelector(".sc-crosshair");
    if (cross) {
      cross.setAttribute("x1", zone.getAttribute("data-x"));
      cross.setAttribute("x2", zone.getAttribute("data-x"));
      chart.classList.add("is-active");
    }
    var box = zone.getBoundingClientRect();
    var left = window.scrollX + box.left + box.width / 2 - tip.offsetWidth / 2;
    left = Math.max(window.scrollX + 8, Math.min(left, window.scrollX + document.documentElement.clientWidth - tip.offsetWidth - 8));
    tip.style.left = left + "px";
    tip.style.top = (window.scrollY + box.top - tip.offsetHeight - 8) + "px";
  }
  function hideTip(chart) {
    if (tip) { tip.hidden = true; }
    chart.classList.remove("is-active");
  }
  document.querySelectorAll("[data-chart]").forEach(function (chart) {
    chart.addEventListener("pointerover", function (event) {
      var zone = event.target.closest("[data-tip]");
      if (zone) { showTip(chart, parseInt(zone.getAttribute("data-index"), 10)); }
    });
    chart.addEventListener("pointerleave", function () { hideTip(chart); });
    chart.addEventListener("focus", function () {
      var zones = chart.querySelectorAll("[data-tip]");
      showTip(chart, parseInt(chart.getAttribute("data-current") || String(zones.length - 1), 10));
    });
    chart.addEventListener("blur", function () { hideTip(chart); });
    chart.addEventListener("keydown", function (event) {
      var current = parseInt(chart.getAttribute("data-current") || "0", 10);
      if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        event.preventDefault();
        showTip(chart, current + (event.key === "ArrowRight" ? 1 : -1));
      } else if (event.key === "Escape") {
        hideTip(chart);
      }
    });
  });
})();
