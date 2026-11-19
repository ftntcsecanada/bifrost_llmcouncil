import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import './WikiPanel.css';

export default function WikiPanel() {
  const [files, setFiles] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);
  const folderRef = useRef(null);
  // Folders start collapsed; open[folder] === true means expanded.
  const [open, setOpen] = useState({});

  const refresh = async () => {
    try {
      setFiles(await api.listWiki());
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const onPick = async (e) => {
    // folder picks include non-text files (images, etc.); keep wiki text only
    const picked = Array.from(e.target.files || []).filter((f) =>
      /\.(md|markdown|txt)$/i.test(f.name)
    );
    e.target.value = '';
    if (!picked.length) return;
    setBusy(true);
    setError('');
    for (const file of picked) {
      try {
        await api.uploadWiki(file);
      } catch (err) {
        setError(`${file.name}: ${err.message}`);
      }
    }
    setBusy(false);
    refresh();
  };

  const onDeleteFolder = async (folder, count) => {
    if (!window.confirm(`Remove folder "${folder}" and its ${count} file(s)?`)) return;
    try {
      await api.deleteWikiFolder(folder);
      refresh();
    } catch (e) {
      setError(e.message);
    }
  };

  // Group files by top-level folder; loose files go under a null key.
  const groups = [];
  for (const f of files) {
    const i = f.name.indexOf('/');
    const folder = i === -1 ? null : f.name.slice(0, i);
    let g = groups.find((x) => x.folder === folder);
    if (!g) groups.push((g = { folder, files: [] }));
    g.files.push(f);
  }

  const onDelete = async (name) => {
    try {
      await api.deleteWiki(name);
      refresh();
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="wiki-panel">
      <div className="wiki-title">
        LLM Wiki / SKILL.md
        <span className="wiki-hint">full if small, else most relevant pages</span>
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".md,.markdown,.txt"
        onChange={onPick}
        hidden
      />
      <button
        className="wiki-upload-btn"
        onClick={() => inputRef.current?.click()}
        disabled={busy}
      >
        {busy ? 'Uploading…' : '+ Upload files'}
      </button>

      <input
        ref={folderRef}
        type="file"
        webkitdirectory=""
        directory=""
        multiple
        onChange={onPick}
        hidden
      />
      <button
        className="wiki-upload-btn"
        onClick={() => folderRef.current?.click()}
        disabled={busy}
      >
        + Upload wiki folder
      </button>

      {error && <div className="wiki-error">{error}</div>}

      <ul className="wiki-list">
        {files.length === 0 ? (
          <li className="wiki-empty">No files uploaded</li>
        ) : (
          groups.map((g) => (
            <li key={g.folder ?? '__root__'} className="wiki-group">
              {g.folder && (
                <div className="wiki-item wiki-folder">
                  <button
                    className="wiki-toggle"
                    onClick={() =>
                      setOpen((o) => ({ ...o, [g.folder]: !o[g.folder] }))
                    }
                    aria-expanded={!!open[g.folder]}
                    title={open[g.folder] ? 'Collapse' : 'Expand'}
                  >
                    <span className="wiki-chevron">
                      {open[g.folder] ? '▾' : '▸'}
                    </span>
                    <span className="wiki-name">📁 {g.folder}/</span>
                  </button>
                  <span className="wiki-size">{g.files.length} files</span>
                  <button
                    className="wiki-delete"
                    onClick={() => onDeleteFolder(g.folder, g.files.length)}
                    aria-label={`Remove folder ${g.folder}`}
                    title="Remove folder"
                  >
                    🗑
                  </button>
                </div>
              )}
              <ul
                className={g.folder ? 'wiki-sublist' : 'wiki-list'}
                hidden={!!g.folder && !open[g.folder]}
              >
                {g.files.map((f) => (
                  <li key={f.name} className="wiki-item">
                    <span className="wiki-name" title={f.name}>
                      {g.folder ? f.name.slice(g.folder.length + 1) : f.name}
                    </span>
                    <span className="wiki-size">
                      {(f.size / 1024).toFixed(1)} KB
                    </span>
                    <button
                      className="wiki-delete"
                      onClick={() => onDelete(f.name)}
                      aria-label={`Remove ${f.name}`}
                    >
                      ×
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
