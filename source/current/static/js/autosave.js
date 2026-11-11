/**
 * Autosave Module - Assistente Acadêmico
 * Handles form change detection, debounced saving, conflict resolution
 */
export function createAutosave({ form, collectPayload, saveUrl, onStateChange }) {
  if (!form) return { flush: () => Promise.resolve(false) };

  const saveState = form.querySelector("[data-save-state]");
  const reloadButton = form.querySelector("[data-reload-editor]");
  let timer = null;
  let saveInFlight = false;
  let saveQueued = false;
  let changeSequence = 0;
  let savedSequence = 0;
  let lastSaveSucceeded = true;
  let hasConflict = false;

  function setSaveState(message) {
    if (saveState) saveState.textContent = message;
    onStateChange?.({ message, hasConflict, saving: saveInFlight });
  }

  function isAiControl(target) {
    return Boolean(target?.closest?.("[data-ai-field], [data-ai-instruction]"));
  }

  function queueSave(delay = 700) {
    if (!form || hasConflict) return;
    window.clearTimeout(timer);
    setSaveState("Alteração pendente…");
    timer = window.setTimeout(() => {
      timer = null;
      void save();
    }, delay);
  }

  function markDirty(event) {
    if (isAiControl(event?.target)) return;
    if (event?.target?.matches?.("[data-project-source]")) {
      form.querySelectorAll("[data-project-source]").forEach((input) => {
        if (input.value === event.target.value) input.checked = event.target.checked;
      });
    }
    changeSequence += 1;
    if (hasConflict) {
      setSaveState("Conflito: recarregue a versão do servidor antes de salvar.");
      return;
    }
    queueSave();
  }

  async function readJson(response) {
    const text = await response.text();
    if (!text) return {};
    try {
      return JSON.parse(text);
    } catch {
      return {};
    }
  }

  async function save() {
    if (!form || hasConflict) return;
    window.clearTimeout(timer);
    timer = null;
    if (saveInFlight) {
      saveQueued = true;
      setSaveState("Salvando…");
      return;
    }

    const requestSequence = changeSequence;
    const csrf = form.querySelector("[name=csrf_token]")?.value;
    if (!csrf) {
      setSaveState("Não foi possível salvar: sessão sem proteção CSRF.");
      return;
    }

    saveInFlight = true;
    saveQueued = false;
    setSaveState("Salvando…");
    let followUpDelay = null;

    try {
      const response = await fetch(saveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: JSON.stringify({ revision: Number(form.dataset.revision), payload: collectPayload() }),
      });
      const result = await readJson(response);

      if (!response.ok) {
        const error = new Error(result.error || "save_failed");
        error.code = result.error;
        error.status = response.status;
        error.revision = result.revision;
        throw error;
      }
      if (result.revision === undefined || result.revision === null) {
        const error = new Error("save_failed");
        error.code = "save_failed";
        throw error;
      }

      savedSequence = requestSequence;
      lastSaveSucceeded = true;
      form.dataset.revision = String(result.revision);
      if (reloadButton) reloadButton.hidden = true;

      if (requestSequence < changeSequence) {
        setSaveState("Salvo; salvando alterações recentes…");
        followUpDelay = 0;
      } else {
        setSaveState("Salvo agora");
      }
    } catch (error) {
      lastSaveSucceeded = false;
      if (error.code === "project_conflict" || error.status === 409) {
        hasConflict = true;
        window.clearTimeout(timer);
        timer = null;
        saveQueued = false;
        if (reloadButton) reloadButton.hidden = false;
        const revision = error.revision === undefined ? "mais recente" : `revisão ${error.revision}`;
        setSaveState(`Conflito: o servidor tem a ${revision}. Recarregue antes de continuar.`);
      } else {
        if (requestSequence < changeSequence) followUpDelay = 700;
        setSaveState(requestSequence < changeSequence
          ? "Não foi possível salvar; suas alterações continuam pendentes."
          : "Não foi possível salvar.");
      }
    } finally {
      saveInFlight = false;
      if ((saveQueued || followUpDelay !== null) && !hasConflict) {
        saveQueued = false;
        if (followUpDelay !== null) queueSave(followUpDelay);
      }
    }
  }

  async function flushSave() {
    window.clearTimeout(timer);
    timer = null;
    while (saveInFlight) await new Promise((resolve) => window.setTimeout(resolve, 30));
    if (hasConflict) return false;
    if (savedSequence < changeSequence) await save();
    while (saveInFlight) await new Promise((resolve) => window.setTimeout(resolve, 30));
    return !hasConflict && lastSaveSucceeded && savedSequence >= changeSequence;
  }

  // Bind events
  form.addEventListener("input", markDirty);
  form.addEventListener("change", markDirty);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (hasConflict) {
      setSaveState("Conflito: recarregue a versão do servidor antes de salvar.");
      return;
    }
    window.clearTimeout(timer);
    timer = null;
    void save();
  });
  reloadButton?.addEventListener("click", () => window.location.reload());

  window.addEventListener("beforeunload", (event) => {
    if (saveInFlight || savedSequence < changeSequence || hasConflict) {
      event.preventDefault();
      event.returnValue = "";
    }
  });

  return { markDirty, save, flushSave, hasConflict: () => hasConflict };
}