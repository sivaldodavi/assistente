// Account tabs and sub-tabs functionality
// Handles: Meus Projetos, Minha Biblioteca, Minha Conta, Administração

document.addEventListener('DOMContentLoaded', () => {
  initAccountTabs();
  initAccountSubtabs();
  initSharingPreferences();
  initDeletion();
  initGrants();
});

// ──────────────────────────────────────────────
// Main Account Tabs (Meus Projetos, Minha Biblioteca, Minha Conta, Administração)
// ──────────────────────────────────────────────

function initAccountTabs() {
  const tabButtons = document.querySelectorAll('.account-tabs [role="tab"]');
  const tabPanels = document.querySelectorAll('.tab-panel[role="tabpanel"]');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      activateTab(tabId, tabButtons, tabPanels);
    });
  });

  // Activate first tab by default
  if (tabButtons[0]) {
    activateTab(tabButtons[0].dataset.tab, tabButtons, tabPanels);
  }
}

function activateTab(tabId, tabButtons, tabPanels) {
  tabButtons.forEach(btn => {
    const isActive = btn.dataset.tab === tabId;
    btn.setAttribute('aria-selected', isActive);
    btn.classList.toggle('is-active', isActive);
  });

  tabPanels.forEach(panel => {
    const isActive = panel.id === `tab-${tabId}`;
    panel.hidden = !isActive;
    panel.setAttribute('aria-hidden', !isActive);
  });
}

// ──────────────────────────────────────────────
// Account Sub-tabs (Perfil, Compartilhamento, Créditos, Excluir conta)
// ──────────────────────────────────────────────

function initAccountSubtabs() {
  const tabButtons = document.querySelectorAll('.account-subtabs [role="tab"]');
  const tabPanels = document.querySelectorAll('.subtab-panel[role="tabpanel"]');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.subtab;
      activateSubtab(tabId, tabButtons, tabPanels);
    });
  });

  // Activate first subtab by default
  if (tabButtons[0]) {
    activateSubtab(tabButtons[0].dataset.subtab, tabButtons, tabPanels);
  }
}

function activateSubtab(tabId, tabButtons, tabPanels) {
  tabButtons.forEach(btn => {
    const isActive = btn.dataset.subtab === tabId;
    btn.setAttribute('aria-selected', isActive);
    btn.classList.toggle('is-active', isActive);
  });

  tabPanels.forEach(panel => {
    const isActive = panel.id === `subtab-${tabId}`;
    panel.hidden = !isActive;
    panel.setAttribute('aria-hidden', !isActive);
  });
}

// ──────────────────────────────────────────────
// Sharing Preferences
// ──────────────────────────────────────────────

async function initSharingPreferences() {
  const form = document.getElementById('sharing-prefs-form');
  const statusEl = document.getElementById('sharing-prefs-status');
  const allowView = document.getElementById('allow_admin_view');
  const allowComments = document.getElementById('allow_admin_comments');

  if (!form) return;

  // Load current preferences
  await loadSharingPreferences();

  // Disable comments checkbox if view is not checked
  allowView?.addEventListener('change', () => {
    if (allowComments) {
      allowComments.disabled = !allowView.checked;
      if (!allowView.checked) {
        allowComments.checked = false;
      }
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const payload = {
      allow_admin_view: formData.get('allow_admin_view') === 'on',
      allow_admin_comments: formData.get('allow_admin_comments') === 'on',
      inherit_account_default: formData.get('inherit_account_default') === 'on'
    };

    try {
      const res = await fetch('/account/sharing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': formData.get('csrf_token') },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (data.ok) {
        showStatus(statusEl, 'Preferências salvas com sucesso.', 'success');
        // Update UI to reflect saved values
        allowView.checked = data.preferences.allow_admin_view;
        allowComments.checked = data.preferences.allow_admin_comments;
        allowComments.disabled = !data.preferences.allow_admin_view;
        document.getElementById('inherit_account_default').checked = data.preferences.inherit_default;
      } else {
        showStatus(statusEl, data.message || 'Erro ao salvar preferências.', 'error');
      }
    } catch (err) {
      showStatus(statusEl, 'Erro de conexão.', 'error');
    }
  });
}

async function loadSharingPreferences() {
  try {
    const res = await fetch('/account/sharing');
    const data = await res.json();
    if (data.ok) {
      const prefs = data.preferences;
      document.getElementById('allow_admin_view').checked = prefs.allow_admin_view;
      document.getElementById('allow_admin_comments').checked = prefs.allow_admin_comments;
      document.getElementById('allow_admin_comments').disabled = !prefs.allow_admin_view;
      document.getElementById('inherit_account_default').checked = prefs.inherit_default;
    }
  } catch (err) {
    console.error('Failed to load sharing preferences:', err);
  }
}

// ──────────────────────────────────────────────
// Self Deletion
// ──────────────────────────────────────────────

async function initDeletion() {
  const statusEl = document.getElementById('deletion-status');
  const actionsEl = document.getElementById('deletion-actions');
  const btnRequest = document.getElementById('btn-request-deletion');
  const btnCancel = document.getElementById('btn-cancel-deletion');
  const btnConfirm = document.getElementById('btn-confirm-deletion');

  if (!statusEl) return;

  // Check for pending deletion request
  await checkDeletionStatus();

  // Forms use native submission, just handle UI state
  const formRequest = document.getElementById('form-request-deletion');
  const formCancel = document.getElementById('form-cancel-deletion');
  const formConfirm = document.getElementById('form-confirm-deletion');

  if (formRequest) {
    formRequest.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const res = await fetch('/account/deletion/request', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': new FormData(formRequest).get('csrf_token') }
        });
        const data = await res.json();
        if (data.ok) {
          updateDeletionUI('pending');
        } else {
          showStatus(statusEl, data.message || 'Erro ao solicitar exclusão.', 'error');
        }
      } catch (err) {
        showStatus(statusEl, 'Erro de conexão.', 'error');
      }
    });
  }

  if (formCancel) {
    formCancel.addEventListener('submit', async (e) => {
      e.preventDefault();
      try {
        const res = await fetch('/account/deletion/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': new FormData(formCancel).get('csrf_token') }
        });
        const data = await res.json();
        if (data.ok) {
          updateDeletionUI('none');
        } else {
          showStatus(statusEl, data.message || 'Erro ao cancelar.', 'error');
        }
      } catch (err) {
        showStatus(statusEl, 'Erro de conexão.', 'error');
      }
    });
  }

  if (formConfirm) {
    formConfirm.addEventListener('submit', async (e) => {
      // Let the native confirm dialog handle confirmation
      // If user confirms, form submits normally
    });
  }
}

async function checkDeletionStatus() {
  try {
    const res = await fetch('/account/sharing'); // Reusing endpoint that returns account info including deletion_request_pending
    const data = await res.json();
    if (data.ok && data.account) {
      const account = data.account;
      if (account.deletion_request_pending) {
        updateDeletionUI('pending');
      } else {
        updateDeletionUI('none');
      }
    }
  } catch (err) {
    console.error('Failed to check deletion status:', err);
  }
}

function updateDeletionUI(state) {
  const statusEl = document.getElementById('deletion-status');
  const btnRequest = document.getElementById('btn-request-deletion');
  const btnCancel = document.getElementById('btn-cancel-deletion');
  const btnConfirm = document.getElementById('btn-confirm-deletion');
  const formRequest = document.getElementById('form-request-deletion');
  const formCancel = document.getElementById('form-cancel-deletion');
  const formConfirm = document.getElementById('form-confirm-deletion');

  if (state === 'pending') {
    statusEl.textContent = '⚠️ Solicitação de exclusão pendente. Você pode cancelar ou confirmar a exclusão definitiva.';
    statusEl.className = 'deletion-status warning';
    if (formRequest) formRequest.style.display = 'none';
    if (formCancel) formCancel.style.display = 'inline';
    if (formConfirm) formConfirm.style.display = 'inline';
  } else {
    statusEl.textContent = 'Nenhuma solicitação de exclusão pendente.';
    statusEl.className = 'deletion-status';
    if (formRequest) formRequest.style.display = 'inline';
    if (formCancel) formCancel.style.display = 'none';
    if (formConfirm) formConfirm.style.display = 'none';
  }
}

// ──────────────────────────────────────────────
// Grants (Créditos)
// ──────────────────────────────────────────────

async function initGrants() {
  const listEl = document.getElementById('grants-list');
  if (!listEl) return;

  try {
    const res = await fetch('/account/grants');
    const data = await res.json();
    if (data.ok && data.grants) {
      renderGrants(data.grants, listEl);
    } else {
      listEl.innerHTML = '<p class="field-hint">Nenhum grant encontrado.</p>';
    }
  } catch (err) {
    listEl.innerHTML = '<p class="field-hint error">Erro ao carregar grants.</p>';
  }
}

function renderGrants(grants, container) {
  if (!grants.length) {
    container.innerHTML = '<p class="field-hint">Nenhum crédito concedido ainda.</p>';
    return;
  }

  container.innerHTML = grants.map(g => `
    <div class="grant-card">
      <div class="grant-header">
        <strong>${g.plan_code === 'livre' ? 'Sem plano' : g.plan_code}</strong>
        <span class="grant-date">Concedido em ${new Date(g.created_at * 1000).toLocaleDateString('pt-BR')}</span>
      </div>
      <div class="grant-credits">
        <span class="credit ${g.project_remaining > 0 ? 'has-credit' : ''}">Projetos: ${g.project_remaining}/${g.project_credits}</span>
        <span class="credit ${g.ai_analysis_remaining > 0 ? 'has-credit' : ''}">Análise IA: ${g.ai_analysis_remaining}/${g.ai_analysis_credits}</span>
        <span class="credit ${g.deepseek_explanation_remaining > 0 ? 'has-credit' : ''}">Explicação DeepSeek: ${g.deepseek_explanation_remaining}/${g.deepseek_explanation_credits}</span>
      </div>
      ${g.expires_at ? `<p class="grant-expiry">Expira em ${new Date(g.expires_at * 1000).toLocaleDateString('pt-BR')}</p>` : ''}
    </div>
  `).join('');
}

// ──────────────────────────────────────────────
// Utility
// ──────────────────────────────────────────────

function showStatus(el, message, type) {
  if (!el) return;
  el.textContent = message;
  el.className = type === 'success' ? 'notice success' : 'notice error';
  el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 5000);
}