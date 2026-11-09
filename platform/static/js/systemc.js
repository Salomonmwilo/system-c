/* SYSTEM-C Platform : confirmation des actions irréversibles (audit A1).
   Un formulaire ou un bouton portant data-confirm demande confirmation avant l'envoi.
   Sans JavaScript, le formulaire reste utilisable : le serveur applique toujours ses règles. */
(function () {
  "use strict";
  document.addEventListener("submit", function (event) {
    var form = event.target;
    var submitter = event.submitter;
    var message = (submitter && submitter.getAttribute("data-confirm")) || form.getAttribute("data-confirm");
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });
})();
