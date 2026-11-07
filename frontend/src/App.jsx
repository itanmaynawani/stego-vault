import { useEffect, useRef, useState } from "react";

const GLYPHS = "▓▒░#%&@01<>/\\";

// Scrambles text, then resolves it left to right: the one dramatic moment.
function Decrypting({ text }) {
  const [shown, setShown] = useState("");
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return setShown(text);
    let frame = 0;
    const t = setInterval(() => {
      frame++;
      const settled = Math.floor(frame / 2);
      setShown(
        text.split("").map((c, i) =>
          i < settled || c === " " || c === "\n" ? c : GLYPHS[Math.floor(Math.random() * GLYPHS.length)]
        ).join("")
      );
      if (settled >= text.length) clearInterval(t);
    }, 30);
    return () => clearInterval(t);
  }, [text]);
  return <p className="plain" aria-label={text}>{shown}</p>;
}

function Drop({ file, onFile, hint }) {
  const input = useRef();
  const [over, setOver] = useState(false);
  const preview = file ? URL.createObjectURL(file) : null;
  return (
    <div
      className={`drop ${over ? "over" : ""}`}
      onClick={() => input.current.click()}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); onFile(e.dataTransfer.files[0]); }}
    >
      <input ref={input} type="file" accept="image/*" hidden onChange={(e) => onFile(e.target.files[0])} />
      {preview ? <img src={preview} alt="Selected" /> : <span>{hint}</span>}
    </div>
  );
}

export default function App() {
  const [mode, setMode] = useState("seal");
  const [file, setFile] = useState(null);
  const [key, setKey] = useState("");
  const [message, setMessage] = useState("");
  const [capacity, setCapacity] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sealedUrl, setSealedUrl] = useState("");
  const [revealed, setRevealed] = useState(null);

  const reset = () => { setError(""); setSealedUrl(""); setRevealed(null); };

  async function pick(f) {
    reset(); setFile(f || null); setCapacity(null);
    if (!f) return;
    const fd = new FormData(); fd.append("image", f);
    const r = await fetch("/api/capacity", { method: "POST", body: fd });
    if (r.ok) setCapacity((await r.json()).bytes);
    else setError((await r.json()).error);
  }

  async function submit() {
    reset(); setBusy(true);
    const fd = new FormData();
    fd.append("image", file); fd.append("key", key);
    if (mode === "seal") fd.append("message", message);
    try {
      const r = await fetch(`/api/${mode}`, { method: "POST", body: fd });
      if (!r.ok) throw new Error((await r.json()).error);
      if (mode === "seal") setSealedUrl(URL.createObjectURL(await r.blob()));
      else setRevealed((await r.json()).message);
    } catch (e) { setError(e.message); }
    setBusy(false);
  }

  const bytes = new TextEncoder().encode(message).length;
  const ready = file && key && (mode === "reveal" || message) && !busy;

  return (
    <main>
      <h1>There is something in this picture.</h1>
      <p className="sub">Hide a message in an image's pixels. Only the right key can bring it back.</p>

      <div className="tabs" role="tablist">
        {[["seal", "Hide a message"], ["reveal", "Reveal a message"]].map(([m, label]) => (
          <button key={m} role="tab" aria-selected={mode === m} onClick={() => { setMode(m); reset(); }}>{label}</button>
        ))}
      </div>

      <Drop file={file} onFile={pick} hint={mode === "seal" ? "Drop a cover image, or click to choose" : "Drop a sealed PNG, or click to choose"} />
      {mode === "seal" && capacity !== null && <p className="note">This image can hold about {capacity.toLocaleString()} bytes.</p>}

      {mode === "seal" && (
        <label>Secret message
          <textarea rows="4" value={message} onChange={(e) => setMessage(e.target.value)} />
          {capacity !== null && <span className={`note ${bytes > capacity ? "bad" : ""}`}>{bytes} / {capacity.toLocaleString()} bytes</span>}
        </label>
      )}

      <label>Key
        <input type="password" value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" />
      </label>

      <button className="go" disabled={!ready} onClick={submit}>
        {busy ? "Working…" : mode === "seal" ? "Seal message in image" : "Reveal message"}
      </button>

      {error && <p className="error" role="alert">{error}</p>}
      {sealedUrl && (
        <div className="result">
          <img src={sealedUrl} alt="Sealed result" />
          <a className="go" href={sealedUrl} download="sealed.png">Download sealed.png</a>
          <p className="note">Keep it as PNG. Re-saving as JPEG or sharing through apps that recompress it will destroy the message.</p>
        </div>
      )}
      {revealed !== null && <div className="result"><Decrypting text={revealed} /></div>}
    </main>
  );
}
