import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import './WikiPanel.css';

export default function WikiPanel() {
  const [files, setFiles] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);

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
    const picked = Array.from(e.target.files || []);
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
        <span className="wiki-hint">added to every council prompt</span>
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

      {error && <div className="wiki-error">{error}</div>}

      <ul className="wiki-list">
        {files.length === 0 ? (
          <li className="wiki-empty">No files uploaded</li>
        ) : (
          files.map((f) => (
            <li key={f.name} className="wiki-item">
              <span className="wiki-name" title={f.name}>
                {f.name}
              </span>
              <span className="wiki-size">{(f.size / 1024).toFixed(1)} KB</span>
              <button
                className="wiki-delete"
                onClick={() => onDelete(f.name)}
                aria-label={`Remove ${f.name}`}
              >
                ×
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
