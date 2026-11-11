// Während der Assistent arbeitet (das Modell braucht Sekunden bis Minuten), zeigt der Knopf, dass etwas passiert.
document.addEventListener('submit', (e) => {
  const k = e.submitter && e.submitter.dataset && e.submitter.dataset.laeuft ? e.submitter : e.target.querySelector('button[data-laeuft]');
  if (!k) return;
  setTimeout(() => { k.classList.add('laeuft'); k.textContent = k.dataset.laeuft; k.disabled = true; }, 0);
});
