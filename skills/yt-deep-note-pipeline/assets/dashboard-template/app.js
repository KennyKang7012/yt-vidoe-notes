const listPanel = document.getElementById("listPanel");
const detailPanel = document.getElementById("detailPanel");
const searchInput = document.getElementById("searchInput");
const tagFilters = document.getElementById("tagFilters");
const noteCount = document.getElementById("noteCount");
const undoPinnedBtn = document.getElementById("undoPinnedBtn");
const undoInfo = document.getElementById("undoInfo");
const undoSelect = document.getElementById("undoSelect");

let allNotes = [];
let activeTag = "";
let selectedNoteId = "";
let undoState = { can_undo: false, entries: [] };

const API_BASE = "../../../../api";

const readMarkdown = async (path) => {
  const resp = await fetch(`../../../../${path}`);
  if (!resp.ok) throw new Error(`Failed to load ${path}`);
  return resp.text();
};

const escapeHtml = (text) =>
  text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

const buildUndoLabel = (entry) => {
  const title = entry.note_title || entry.note_id || "Unknown note";
  const hash = (entry.delete_commit_hash || "").slice(0, 7);
  return `${title} (${hash})`;
};

const renderUndoPanel = () => {
  if (!undoPinnedBtn || !undoInfo || !undoSelect) return;

  const entries = Array.isArray(undoState.entries) ? undoState.entries : [];
  undoSelect.innerHTML = "";

  if (entries.length > 0) {
    for (const entry of entries) {
      const option = document.createElement("option");
      option.value = entry.delete_commit_hash || "";
      option.textContent = buildUndoLabel(entry);
      undoSelect.appendChild(option);
    }
    undoSelect.disabled = false;
    undoPinnedBtn.disabled = false;
    undoInfo.textContent = `可還原 ${entries.length} 筆刪除（最多 ${undoState.max_entries || 10} 筆）。`;
  } else {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "目前沒有可還原的刪除";
    undoSelect.appendChild(option);
    undoSelect.disabled = true;
    undoPinnedBtn.disabled = true;
    undoInfo.textContent = "目前沒有可還原的刪除。";
  }
};

const loadUndoState = async () => {
  try {
    const resp = await fetch(`${API_BASE}/revert-delete-state`);
    if (!resp.ok) throw new Error("Failed to load undo state");
    const data = await resp.json();
    undoState = data || { can_undo: false, entries: [] };
  } catch {
    undoState = { can_undo: false, entries: [] };
  }
  renderUndoPanel();
};

const renderTags = (notes) => {
  const tags = [...new Set(notes.flatMap((n) => n.tags || []))].sort();
  tagFilters.innerHTML = "";
  for (const tag of tags) {
    const btn = document.createElement("button");
    btn.className = `tag${activeTag === tag ? " active" : ""}`;
    btn.textContent = tag;
    btn.onclick = () => {
      activeTag = activeTag === tag ? "" : tag;
      render();
    };
    tagFilters.appendChild(btn);
  }
};

const filterNotes = () => {
  const q = (searchInput.value || "").trim().toLowerCase();
  return allNotes.filter((n) => {
    const byTag = activeTag ? (n.tags || []).includes(activeTag) : true;
    const hay = `${n.title} ${n.summary} ${(n.tags || []).join(" ")}`.toLowerCase();
    const byQuery = q ? hay.includes(q) : true;
    return byTag && byQuery;
  });
};

const render = () => {
  const notes = filterNotes();
  noteCount.textContent = `Notes ${notes.length} / ${allNotes.length}`;
  renderTags(allNotes);
  renderList(notes);
};

const undoDelete = async () => {
  if (!undoSelect || undoSelect.disabled) {
    window.alert("目前沒有可還原的刪除。");
    return;
  }

  const hash = (undoSelect.value || "").trim();
  if (!hash) {
    window.alert("請先選擇要還原的刪除記錄。");
    return;
  }

  const ok = window.confirm(`要還原這筆刪除嗎？\n\nDelete commit: ${hash}`);
  if (!ok) return;

  if (undoPinnedBtn) {
    undoPinnedBtn.disabled = true;
    undoPinnedBtn.textContent = "Undoing...";
  }

  try {
    const resp = await fetch(`${API_BASE}/revert-delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ commit_hash: hash }),
    });
    const payload = await resp.json().catch(() => ({}));
    if (!resp.ok || !payload.ok) {
      throw new Error(payload.error || `HTTP ${resp.status}`);
    }

    await load();
    if (payload.undo_state) {
      undoState = payload.undo_state;
      renderUndoPanel();
    } else {
      await loadUndoState();
    }

    detailPanel.innerHTML = `
      <h2>還原完成</h2>
      <p class="meta">Reverted commit: <code>${payload.reverted_commit}</code></p>
      <p class="meta">New commit: <code>${payload.new_commit}</code></p>
    `;
  } catch (err) {
    window.alert(`還原失敗：${err.message}`);
    await loadUndoState();
  } finally {
    if (undoPinnedBtn) {
      undoPinnedBtn.textContent = "Undo Selected";
    }
  }
};

const deleteNote = async (note, event) => {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  const ok = window.confirm(`確定要刪除這篇筆記嗎？\n\n${note.title}`);
  if (!ok) return;

  const buttons = document.querySelectorAll(`[data-delete-id="${CSS.escape(note.id)}"]`);
  buttons.forEach((btn) => {
    btn.disabled = true;
    btn.textContent = "Deleting...";
  });

  try {
    const resp = await fetch(`${API_BASE}/notes/${encodeURIComponent(note.id)}`, {
      method: "DELETE",
    });
    const payload = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(payload.error || `HTTP ${resp.status}`);

    allNotes = allNotes.filter((n) => n.id !== note.id);

    if (selectedNoteId === note.id) {
      selectedNoteId = "";
      const gitMeta = payload.git && payload.git.committed
        ? `<p class="meta">Delete commit: <code>${payload.git.hash}</code></p>`
        : "";
      detailPanel.innerHTML = `
        <h2>刪除完成</h2>
        <p class="meta">已刪除：${note.title}</p>
        ${gitMeta}
      `;
    }

    if (payload.undo_state) {
      undoState = payload.undo_state;
      renderUndoPanel();
    } else {
      await loadUndoState();
    }
    render();
  } catch (err) {
    buttons.forEach((btn) => {
      btn.disabled = false;
      btn.textContent = "Delete";
    });
    window.alert(`刪除失敗：${err.message}`);
  }
};

const renderList = (notes) => {
  listPanel.innerHTML = "";

  if (notes.length === 0) {
    listPanel.innerHTML = `<p class="meta">目前沒有符合條件的筆記。</p>`;
    return;
  }

  for (const note of notes) {
    const card = document.createElement("div");
    card.className = `note-card${selectedNoteId === note.id ? " selected" : ""}`;
    card.innerHTML = `
      <div class="card-topbar">
        <h3>${note.title}</h3>
        <button class="card-delete" type="button" data-delete-id="${note.id}">Delete</button>
      </div>
      <p class="meta">${note.date} · ${note.source_type}</p>
      <p>${note.summary || ""}</p>
    `;

    card.onclick = () => renderDetail(note);

    const deleteBtn = card.querySelector(".card-delete");
    if (deleteBtn) {
      deleteBtn.onclick = (e) => deleteNote(note, e);
    }

    listPanel.appendChild(card);
  }
};

const renderDetail = async (note) => {
  selectedNoteId = note.id;
  render();

  detailPanel.innerHTML = `
    <h2>${note.title}</h2>
    <p class="meta">${note.date} · ${note.source_type}</p>
    <p class="meta">Loading...</p>
  `;

  try {
    const md = await readMarkdown(note.markdown_path);
    const escaped = escapeHtml(md);
    detailPanel.innerHTML = `
      <h2>${note.title}</h2>
      <p class="meta">${note.date} · ${note.source_type}</p>
      <pre>${escaped}</pre>
    `;
  } catch (err) {
    detailPanel.innerHTML = `
      <h2>${note.title}</h2>
      <p class="meta">Load failed: ${err.message}</p>
    `;
  }
};

const load = async () => {
  const resp = await fetch(`${API_BASE}/notes`);
  if (!resp.ok) throw new Error("Failed to load /api/notes");
  const data = await resp.json();
  allNotes = Array.isArray(data) ? data : [data];
  allNotes.sort((a, b) => (a.date < b.date ? 1 : -1));
  render();

  if (allNotes.length === 0) {
    detailPanel.innerHTML = `<h2>目前沒有筆記</h2><p class="meta">新增筆記後會出現在這裡。</p>`;
  }
};

if (undoPinnedBtn) {
  undoPinnedBtn.onclick = () => undoDelete();
}

searchInput.addEventListener("input", render);

Promise.all([load(), loadUndoState()]).catch((err) => {
  detailPanel.innerHTML = `<h2>Error</h2><p class="meta">${err.message}</p>`;
});
