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
})();
