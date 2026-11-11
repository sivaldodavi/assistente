const settings = document.querySelector('[data-profile-settings]');
function openPanel(name) {
  settings?.querySelectorAll('[data-profile-panel]').forEach((panel) => { panel.hidden = panel.dataset.profilePanel !== name; });
  settings?.querySelectorAll('[data-profile-tab]').forEach((button) => button.setAttribute('aria-current', button.dataset.profileTab === name ? 'page' : 'false'));
}
function panelFromHash() {
  const hash = location.hash.slice(1);
  openPanel(hash === 'terms' || hash === 'whatsapp' ? 'terms' : hash === 'profile' ? 'profile' : settings?.dataset.initialPanel || 'profile');
}
settings?.querySelectorAll('[data-profile-tab]').forEach((button) => button.addEventListener('click', () => { history.replaceState(null, '', `#${button.dataset.profileTab}`); openPanel(button.dataset.profileTab); }));
window.addEventListener('hashchange', panelFromHash);
panelFromHash();
