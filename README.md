# yt-vidoe-notes

YouTube 學習筆記工作流（繁中）與可視化儀表板。

這個專案用來把影片內容整理成：
- 含時間戳逐字稿
- 深度閱讀 Markdown 筆記
- 可瀏覽、可刪除、可用 Git 還原的 Dashboard

## 功能

- 繁中筆記資料結構與索引（`data/notes-index.json`）
- Dashboard 閱讀介面（列表、搜尋、標籤篩選）
- Dashboard 直接刪除筆記（刪索引 + 刪 Markdown）
- 刪除後自動建立 Git commit（`chore(notes): delete ...`）
- Undo Delete（使用 `git revert` 還原）
  - 可回復最近 N 筆（預設 10 筆）
  - 重新整理後仍可回復（持久化狀態）

## 專案結構

```text
.
├─ data/
│  ├─ notes-index.json
│  └─ dashboard-undo-state.json   # runtime 狀態（已忽略版控）
├─ inputs/
│  ├─ audio/
│  └─ transcripts/
├─ notes/
│  └─ YYYY/*.md
├─ outputs/
├─ skills/yt-deep-note-pipeline/
│  ├─ assets/dashboard-template/
│  │  ├─ index.html
│  │  ├─ styles.css
│  │  └─ app.js
│  └─ scripts/
│     ├─ dashboard_server.py
│     └─ render_prompt.py
└─ run-local-test.ps1
```

## 需求

- Windows + PowerShell（目前流程以 Windows 為主）
- Python 3.10+
- Git

可選（做轉錄時常用）：
- `ffmpeg`
- `yt-dlp`
- `faster-whisper`
- `opencc-python-reimplemented`

## 快速開始

### 1) 啟動 Dashboard（請用這支，不要用 `python -m http.server`）

```powershell
cd D:\VibeCoding\yt-vidoe-notes
python .\skills\yt-deep-note-pipeline\scripts\dashboard_server.py --host 127.0.0.1 --port 8010
```

開啟：

```text
http://127.0.0.1:8010/skills/yt-deep-note-pipeline/assets/dashboard-template/
```

### 2) 本地測試資料流（可選）

```powershell
cd D:\VibeCoding\yt-vidoe-notes
.\run-local-test.ps1 -SourceType youtube -SourceValue "https://www.youtube.com/watch?v=demo"
```

## 技能包使用方式（yt-deep-note-pipeline）

本 repo 的核心技能包在：
- `skills/yt-deep-note-pipeline/SKILL.md`

典型使用流程：
1. 提供輸入來源（YouTube URL 或本地 MP4）。
2. 產生/整理時間戳逐字稿（必要時轉繁中）。
3. 依模板產生深度閱讀筆記（Markdown）。
4. 更新 `data/notes-index.json`。
5. 在 Dashboard 閱讀與管理。

若你在 Codex / Agent 對話中使用，建議明確下指令：
- 「使用 `$yt-deep-note-pipeline` 幫我處理這支影片 ...」

相關檔案：
- Prompt 渲染腳本：`skills/yt-deep-note-pipeline/scripts/render_prompt.py`
- 提示模板：`skills/yt-deep-note-pipeline/references/yt-note-prompt-zh-tw.md`
- 儀表板規格：`skills/yt-deep-note-pipeline/references/dashboard-spec.md`

## 儀表板顯示說明（UI）

### 左側側欄

- 搜尋框：即時過濾標題/摘要/標籤。
- Notes 統計：顯示「目前過濾結果 / 全部筆記」。
- Undo Delete 區塊：
  - 下拉可選最近刪除紀錄（預設最多 10 筆）
  - `Undo Selected` 會針對選到的刪除 commit 執行 `git revert`
- 標籤區：點擊標籤可快速篩選。

### 中間筆記卡片區

- 每張卡片顯示：標題、日期、來源型態、摘要。
- `Delete` 按鈕位於卡片右上角。
- 點卡片可在右側打開完整內容。

### 右側閱讀區

- 顯示所選筆記 Markdown 內容。
- 支援純文字/程式碼區塊顯示（`<pre>` 方式）。

## Dashboard 刪除與還原機制

### 刪除

在筆記卡片右上角按 `Delete`：
1. 從 `notes-index.json` 移除該 note
2. 刪除對應 `notes/...md`
3. 自動產生 Git commit（`chore(notes): delete <note_id>`）
4. 將刪除紀錄寫入 Undo 歷史（最多 10 筆）

### 還原（Undo Delete）

側欄常駐 Undo 區塊：
- 下拉選單可選要還原的刪除紀錄
- `Undo Selected` 呼叫 API，底層執行 `git revert --no-edit <delete_commit>`

> 還原是「新增一筆反向 commit」，不改寫歷史，適合長期使用。

## API（由 `dashboard_server.py` 提供）

- `GET /api/notes`
- `DELETE /api/notes/{note_id}`
- `GET /api/revert-delete-state`
- `POST /api/revert-delete`
  - body: `{ "commit_hash": "<hash>" }`（可省略，預設還原最近可還原刪除）

## Git 建議流程

### 查看刪除記錄

```powershell
git log --oneline --grep "^chore(notes): delete"
```

### 手動還原某筆刪除（與 UI 一樣，使用 revert）

```powershell
git revert --no-edit <delete_commit_hash>
```

## 注意事項

- `data/dashboard-undo-state.json` 是 runtime 狀態檔，已加入 `.gitignore`。
- 若只用 `python -m http.server`，刪除/還原 API 不會存在，Undo 功能無法使用。
- 檔名 `yt-vidoe-notes` 為既有 repo 名稱（保留現況）。

## License

可依你的需求補上（例如 MIT）。
