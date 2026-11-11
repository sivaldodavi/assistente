// Admin Dashboard JavaScript
// Handles: Health Check, Uso Global, Limites de Conta

document.addEventListener('DOMContentLoaded', () => {
  initAdminTabs();
  initHealthTab();
  initUsageTab();
  initLimitsTab();
});

// ──────────────────────────────────────────────
// Admin Tabs
// ──────────────────────────────────────────────

function initAdminTabs() {
  const tabButtons = document.querySelectorAll('.admin-tabs [role="tab"]');
  const tabPanels = document.querySelectorAll('.tab-panel[role="tabpanel"]');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;
      activateTab(tabId, tabButtons, tabPanels);
    });
  });

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
// Health Tab
// ──────────────────────────────────────────────

async function initHealthTab() {
  const btnRefresh = document.getElementById('btn-refresh-health');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', loadHealth);
  }
  await loadHealth();
}

async function loadHealth() {
  try {
    const res = await fetch('/admin/health');
    const data = await res.json();
    if (data.ok) {
      renderHealth(data.health);
    } else {
      renderHealthError('Erro ao carregar health check');
    }
  } catch (err) {
    renderHealthError('Erro de conexão');
  }
}

function renderHealth(health) {
  const dbEl = document.getElementById('health-db');
  const sessionsEl = document.getElementById('health-sessions');
  const diskEl = document.getElementById('health-disk');
  const notifEl = document.getElementById('health-notifications');

  if (dbEl) {
    const db = health.database || {};
    dbEl.innerHTML = `
      <dl class="health-dl">
        <dt>Integridade</dt><dd>${db.integrity || 'N/A'}</dd>
        <dt>Tamanho</dt><dd>${formatBytes(db.size_bytes || 0)}</dd>
        <dt>Notificações</dt><dd>${Object.entries(db.notifications || {}).map(([k,v]) => `${k}: ${v}`).join(', ') || 'Nenhuma'}</dd>
      </dl>
    `;
  }

  if (sessionsEl) {
    sessionsEl.innerHTML = `
      <p class="health-metric">${health.active_sessions_24h || 0} sessões ativas nas últimas 24h</p>
    `;
  }

  if (diskEl) {
    const disk = health.disk || {};
    diskEl.innerHTML = `
      <dl class="health-dl">
        <dt>Total</dt><dd>${formatBytes(disk.total_bytes || 0)}</dd>
        <dt>Livre</dt><dd>${formatBytes(disk.free_bytes || 0)}</dd>
        <dt>Usado</dt><dd>${disk.used_percent || 0}%</dd>
      </dl>
    `;
  }

  if (notifEl) {
    const stats = health.notifications || {};
    notifEl.innerHTML = `
      <dl class="health-dl">
        ${Object.entries(stats).map(([k,v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('') || '<dt>Sem dados</dt><dd>-</dd>'}
      </dl>
    `;
  }
}

function renderHealthError(msg) {
  ['health-db', 'health-sessions', 'health-disk', 'health-notifications'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<p class="field-hint error">${msg}</p>`;
  });
}

// ──────────────────────────────────────────────
// Usage Tab
// ──────────────────────────────────────────────

async function initUsageTab() {
  const btnRefresh = document.getElementById('btn-refresh-usage');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', loadUsage);
  }
  await loadUsage();
}

async function loadUsage() {
  try {
    const res = await fetch('/admin/usage');
    const data = await res.json();
    if (data.ok) {
      renderUsage(data.usage);
    } else {
      renderUsageError('Erro ao carregar uso global');
    }
  } catch (err) {
    renderUsageError('Erro de conexão');
  }
}

function renderUsage(usage) {
  const reservationsEl = document.getElementById('usage-reservations');
  const providersEl = document.getElementById('usage-providers');
  const deepseekEl = document.getElementById('usage-deepseek');

  if (reservationsEl) {
    const r = usage.reservations || {};
    reservationsEl.innerHTML = `
      <dl class="health-dl">
        <dt>Total</dt><dd>${r.total_reservations || 0}</dd>
        <dt>Completas</dt><dd>${r.completed || 0}</dd>
        <dt>Reembolsadas</dt><dd>${r.refunded || 0}</dd>
        <dt>Reservadas</dt><dd>${r.reserved || 0}</dd>
      </dl>
    `;
  }

  if (providersEl) {
    const providers = usage.by_provider || [];
    if (providers.length) {
      providersEl.innerHTML = `
        <table class="admin-table">
          <thead><tr><th>Provedor</th><th>Operação</th><th>Chamadas</th><th>Tokens In</th><th>Tokens Out</th></tr></thead>
          <tbody>
            ${providers.map(p => `
              <tr>
                <td>${p.provider}</td>
                <td>${p.operation}</td>
                <td>${p.calls}</td>
                <td>${p.total_input_tokens || 0}</td>
                <td>${p.total_output_tokens || 0}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    } else {
      providersEl.innerHTML = '<p class="field-hint">Nenhum dado de uso por provedor.</p>';
    }
  }

  if (deepseekEl) {
    const d = usage.deepseek || {};
    deepseekEl.innerHTML = `
      <dl class="health-dl">
        <dt>Chamadas</dt><dd>${d.calls || 0}</dd>
        <dt>Tokens Entrada</dt><dd>${d.total_input_tokens || 0}</dd>
        <dt>Tokens Saída</dt><dd>${d.total_output_tokens || 0}</dd>
        <dt>Custo Estimado (USD)</dt><dd>$${(d.total_cost || 0).toFixed(4)}</dd>
      </dl>
    `;
  }
}

function renderUsageError(msg) {
  ['usage-reservations', 'usage-providers', 'usage-deepseek'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = `<p class="field-hint error">${msg}</p>`;
  });
}

// ──────────────────────────────────────────────
// Limits Tab
// ──────────────────────────────────────────────

async function initLimitsTab() {
  const searchForm = document.getElementById('limits-search-form');
  const editForm = document.getElementById('limits-edit-form');
  const cancelBtn = document.getElementById('btn-cancel-limits');
  const statusEl = document.getElementById('limits-status');

  if (searchForm) {
    searchForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('limits-account-email').value.trim();
      await loadAccountLimits(email);
    });
  }

  if (editForm) {
    editForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const accountId = document.getElementById('limits-account-id').value;
      const payload = {
        ai_analysis_limit: parseInt(document.getElementById('limits-ai-analysis').value, 10),
        deepseek_explanation_limit: parseInt(document.getElementById('limits-deepseek-explanation').value, 10),
        is_admin: document.getElementById('limits-is-admin').checked
      };
      await saveAccountLimits(accountId, payload);
    });
  }

  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      document.getElementById('limits-edit-form').hidden = true;
      document.getElementById('limits-search-form').hidden = false;
      statusEl.hidden = true;
    });
  }
}

async function loadAccountLimits(email) {
  const statusEl = document.getElementById('limits-status');
  const searchForm = document.getElementById('limits-search-form');
  const editForm = document.getElementById('limits-edit-form');

  try {
    // Search account by email
    const res = await fetch(`/admin/accounts`);
    const html = await res.text();
    // Parse accounts from the page - simpler approach: use a search endpoint if available
    // For now, we'll need an API endpoint. Let's check if we can get account by email
    // Actually, we need to add an endpoint for this. For now, let's use a workaround.
    showStatus(statusEl, 'Funcionalidade de busca por email precisa de endpoint adicional.', 'error');
  } catch (err) {
    showStatus(statusEl, 'Erro de conexão.', 'error');
  }
}

async function saveAccountLimits(accountId, payload) {
  const statusEl = document.getElementById('limits-status');
  try {
    const res = await fetch(`/admin/accounts/${accountId}/limits`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.ok) {
      showStatus(statusEl, 'Limites atualizados com sucesso.', 'success');
    } else {
      showStatus(statusEl, data.message || 'Erro ao salvar limites.', 'error');
    }
  } catch (err) {
    showStatus(statusEl, 'Erro de conexão.', 'error');
  }
}

// ──────────────────────────────────────────────
// Utility
// ──────────────────────────────────────────────

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showStatus(el, message, type) {
  if (!el) return;
  el.textContent = message;
  el.className = type === 'success' ? 'notice success' : 'notice error';
  el.hidden = false;
  setTimeout(() => { el.hidden = true; }, 5000);
}