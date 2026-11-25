// Améliorations progressives : le site reste lisible sans JavaScript.
(function () {
  // Filtre de la bibliothèque (page d'accueil)
  var filter = document.getElementById('filter');
  if (filter) {
    filter.addEventListener('input', function () {
      var q = filter.value.toLowerCase();
      document.querySelectorAll('#library .card').forEach(function (li) {
        li.hidden = li.textContent.toLowerCase().indexOf(q) === -1;
      });
    });
  }

  // Enchaîne vers le chapitre suivant à la fin de l'audio
  var chapterAudio = document.querySelector('.chapter audio');
  var nextChapter = document.querySelector('a[rel="next"]');
  if (chapterAudio && nextChapter) {
    chapterAudio.addEventListener('ended', function () {
      window.setTimeout(function () {
        if (chapterAudio.ended) window.location.href = nextChapter.href;
      }, 2000);
    });
  }

  // Notes : un clic sur [note] ouvre la note dans une boîte de dialogue
  var refs = document.querySelectorAll('a.note-ref');
  if (!refs.length || typeof HTMLDialogElement === 'undefined') return;
  var dlg = document.createElement('dialog');
  dlg.id = 'note-dialog';
  document.body.appendChild(dlg);
  dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });
  refs.forEach(function (a) {
    a.addEventListener('click', function (e) {
      var note = document.querySelector(a.getAttribute('href'));
      if (!note) return;
      e.preventDefault();
      dlg.innerHTML = note.innerHTML + '<form method="dialog"><button>Fermer</button></form>';
      dlg.showModal();
    });
  });
})();
