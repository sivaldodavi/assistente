/**
 * Revisions Module - Assistente Acadêmico
 * Handles project revisions: list, diff, restore
 */

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&")
    .replaceAll("<", "<")
    .replaceAll(">", ">")
    .replaceAll('"', """)
    .replaceAll("'", "&#039;");
}

async function loadRevisions(revisionsUrl) {
  try {
    const res = await fetch(revisionsUrl);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Erro ao carregar revisões.");
    return data.revisions || [];
  } catch (err) {
    console.error("Failed to load revisions:", err);
    return [];
  }
}

function renderRevisionsList(revisions, container) {
  if (!revisions.length) {
    container.innerHTML = '<p class="field-hint">Nenhuma revisão encontrada.</p>';
    return;
  }
  container.innerHTML = revisions.map(r => `
    <article class="revision-card" data-revision="${r.revision}">
      <header>
        <strong>Revisão ${r.revision}</strong>
        <time>${new Date(r.created_at * 1000).toLocaleString("pt-BR")}</time>
      </header>
      <div class="revision-actions">
        <button type="button" class="text-button" data-diff="${r.revision}">Ver diff</button>
        <button type="button" class="text-button" data-restore="${r.revision}">Restaurar</button>
      </div>
    </article>
  `).join("");
}

async function showDiff(revision, revisionsUrl, diffContainer, readJson) {
  if (!diffContainer) return;
  diffContainer.hidden = false;
  diffContainer.innerHTML = '<p class="field-hint">Carregando diff…</p>';
  try {
    const res = await fetch(`${revisionsUrl}/${revision}/diff`);
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Erro ao carregar diff.");
    diffContainer.innerHTML = `<pre class="diff-output">${escapeHtml(data.diff)}</pre>`;
  } catch (err) {
    diffContainer.innerHTML = `<p class="field-hint error">${err.message}</p>`;
  }
}

async function restoreRevision(revision, revisionsUrl, currentRevision, form, readJson, setSaveState) {
  if (!confirm(`Tem certeza que deseja restaurar a revisão ${revision}? As alterações atuais não salvas serão perdidas.`)) return;
  try {
    const csrf = form.querySelector("[name=csrf_token]")?.value;
    if (!csrf) throw new Error("Sessão sem proteção CSRF.");
    const res = await fetch(`${revisionsUrl}/${revision}/restore`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({ revision: Number(currentRevision) })
    });
    const data = await readJson(res);
    if (!res.ok) throw new Error(data.error || "Erro ao restaurar.");
    window.location.reload();
  } catch (err) {
    setSaveState(err.message);
  }
}

export function initRevisions({ form, readJson, setSaveState }) {
  if (!form || !form.dataset.revisionsUrl) return;

  const toggle = form.querySelector("[data-revisions-toggle]");
  const panel = form.querySelector("[data-revisions-panel]");
  const listEl = form.querySelector("[data-revisions-list]");
  const diffEl = form.querySelector("[data-revision-diff]");

  if (!toggle || !panel || !listEl) return;

  toggle.addEventListener("click", async () => {
    const isHidden = panel.hidden;
    if (isHidden) {
      panel.hidden = false;
      listEl.innerHTML = '<p class="field-hint">Carregando…</p>';
      const revisions = await loadRevisions(form.dataset.revisionsUrl);
      renderRevisionsList(revisions, listEl);

      listEl.querySelectorAll("[data-diff]").forEach(btn => {
        btn.addEventListener("click", () => showDiff(btn.dataset.diff, form.dataset.revisionsUrl, diffEl, readJson));
      });
      listEl.querySelectorAll("[data-restore]").forEach(btn => {
        btn.addEventListener("click", () => restoreRevision(btn.dataset.revision, form.dataset.revisionsUrl, form.dataset.revision, form, readJson, setSaveState));
      });
    } else {
      panel.hidden = true;
    }
  });
}