const listPanel = document.getElementById("listPanel");
const detailPanel = document.getElementById("detailPanel");
const searchInput = document.getElementById("searchInput");
const tagFilters = document.getElementById("tagFilters");
const noteCount = document.getElementById("noteCount");

let allNotes = [];
let activeTag = "";
let selectedNoteId = "";

const API_BASE = "../../../../api";

const readMarkdown = async (path) => {
  const resp = await fetch(`../../../../${path}`);
  if (!resp.ok) throw new Error(`Failed to load ${path}`);
  return resp.text();
};

const escapeHtml = (text) =>
  text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

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
        ? `<p class="meta">Git commit: <code>${payload.git.hash}</code></p>`
        : "";
      detailPanel.innerHTML = `
        <h2>????</h2>
        <p class="meta">????${note.title}</p>
        ${gitMeta}
      `;
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

searchInput.addEventListener("input", render);
load().catch((err) => {
  detailPanel.innerHTML = `<h2>Error</h2><p class="meta">${err.message}</p>`;
});
