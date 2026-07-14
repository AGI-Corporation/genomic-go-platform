import { useEffect, useState, useCallback } from "react";
import { login, listCompounds, getCompound, getFacets, getToken, clearToken } from "./api";
import Structure from "./Structure";

const COLUMNS = [
  { key: "compound_id", label: "ID" },
  { key: "substituent", label: "Substituent" },
  { key: "molecular_weight", label: "MW" },
  { key: "logp", label: "LogP" },
  { key: "binding_dg_kcal_mol", label: "ΔG" },
  { key: "ic50_um", label: "IC50 (µM)" },
  { key: "goodness_score", label: "Score" },
];

function Login({ onDone }) {
  const [u, setU] = useState("researcher");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try { await login(u, p); onDone(); }
    catch (ex) { setErr(ex.message); }
    finally { setBusy(false); }
  };
  return (
    <div className="center">
      <form className="panel login" onSubmit={submit}>
        <div className="brand" style={{ marginBottom: 8 }}><span className="dot" /> AGI Compound Library</div>
        <p>Secured access — sign in to browse the synthetic compound library.</p>
        {err && <div className="err">{err}</div>}
        <div className="field"><label>Username</label>
          <input value={u} onChange={(e) => setU(e.target.value)} autoFocus /></div>
        <div className="field"><label>Password</label>
          <input type="password" value={p} onChange={(e) => setP(e.target.value)} /></div>
        <button className="btn" style={{ width: "100%" }} disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </div>
  );
}

function Detail({ id, onBack }) {
  const [c, setC] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { getCompound(id).then(setC).catch((e) => setErr(e.message)); }, [id]);
  if (err) return <div className="panel">{err}</div>;
  if (!c) return <div className="panel">Loading…</div>;
  const rows = [
    ["Compound ID", c.compound_id],
    ["Substituent", c.substituent || "—"],
    ["Molecular weight", c.molecular_weight != null ? `${c.molecular_weight} g/mol` : "—"],
    ["LogP", c.logp ?? "—"],
    ["ΔG binding", c.binding_dg_kcal_mol != null ? `${c.binding_dg_kcal_mol} kcal/mol` : "—"],
    ["IC50", c.ic50_um != null ? `${c.ic50_um} µM` : "—"],
    ["Goodness score", c.goodness_score ?? "—"],
    ["Target", c.target_protein || "—"],
    ["Mechanism", c.mechanism || "—"],
    ["Therapeutic area", c.therapeutic_area || "—"],
  ];
  return (
    <div>
      <button className="back" onClick={onBack}>← Back to library</button>
      <div className="panel">
        <h2 style={{ marginTop: 0 }}>{c.compound_id}</h2>
        <div className="detail-grid">
          <div><Structure smiles={c.smiles} /></div>
          <div>
            <div className="kv">
              {rows.map(([k, v]) => (<><div className="k">{k}</div><div>{v}</div></>))}
            </div>
            <div style={{ marginTop: 16 }}>
              <label>SMILES</label>
              <div className="mono panel" style={{ padding: 10, wordBreak: "break-all" }}>{c.smiles}</div>
            </div>
            {c.description && <p style={{ color: "var(--muted)", marginTop: 16 }}>{c.description}</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function Library({ onOpen }) {
  const [data, setData] = useState({ total: 0, results: [] });
  const [facets, setFacets] = useState(null);
  const [q, setQ] = useState("");
  const [sub, setSub] = useState("");
  const [ic50Max, setIc50Max] = useState("");
  const [sort, setSort] = useState("compound_id");
  const [order, setOrder] = useState("asc");
  const [offset, setOffset] = useState(0);
  const limit = 50;

  useEffect(() => { getFacets().then(setFacets).catch(() => {}); }, []);
  const load = useCallback(() => {
    const params = { sort, order, limit, offset };
    if (q) params.q = q;
    if (sub) params.substituent = sub;
    if (ic50Max) params.ic50_max = ic50Max;
    listCompounds(params).then(setData).catch(() => {});
  }, [q, sub, ic50Max, sort, order, offset]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { setOffset(0); }, [q, sub, ic50Max]);

  const toggleSort = (key) => {
    if (sort === key) setOrder(order === "asc" ? "desc" : "asc");
    else { setSort(key); setOrder("asc"); }
  };
  const fmt = (v) => (v == null ? "—" : v);

  return (
    <div>
      <div className="controls">
        <div><label>Search (ID, SMILES, substituent, text)</label>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Cl, kinase, AGI-1" /></div>
        <div><label>Substituent</label>
          <select value={sub} onChange={(e) => setSub(e.target.value)}>
            <option value="">All</option>
            {facets?.substituents.map(([s, n]) => (
              <option key={s} value={s === "—" ? "" : s}>{s} ({n})</option>))}
          </select></div>
        <div><label>Max IC50 (µM)</label>
          <input value={ic50Max} onChange={(e) => setIc50Max(e.target.value)} placeholder="e.g. 0.5" /></div>
        <div><label>Sort</label>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            {COLUMNS.map((c) => (<option key={c.key} value={c.key}>{c.label}</option>))}</select></div>
        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <button className="btn ghost" onClick={() => setOrder(order === "asc" ? "desc" : "asc")}>
            {order === "asc" ? "↑ Asc" : "↓ Desc"}</button></div>
      </div>

      <div className="panel" style={{ overflowX: "auto" }}>
        <table>
          <thead><tr>
            {COLUMNS.map((c) => (
              <th key={c.key} onClick={() => toggleSort(c.key)}>
                {c.label}{sort === c.key ? (order === "asc" ? " ↑" : " ↓") : ""}</th>))}
            <th>SMILES</th>
          </tr></thead>
          <tbody>
            {data.results.map((c) => (
              <tr key={c.compound_id} className="rowlink" onClick={() => onOpen(c.compound_id)}>
                <td><strong>{c.compound_id}</strong></td>
                <td><span className="pill">{c.substituent || "—"}</span></td>
                <td>{fmt(c.molecular_weight)}</td>
                <td>{fmt(c.logp)}</td>
                <td>{fmt(c.binding_dg_kcal_mol)}</td>
                <td>{fmt(c.ic50_um)}</td>
                <td>{fmt(c.goodness_score)}</td>
                <td className="mono smiles">{c.smiles}</td>
              </tr>))}
          </tbody>
        </table>
        <div className="footer">
          <span>{data.total} compounds{q || sub || ic50Max ? " (filtered)" : ""}</span>
          <span>
            <button className="btn ghost" disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - limit))}>Prev</button>{" "}
            <span style={{ margin: "0 8px" }}>{offset + 1}–{Math.min(offset + limit, data.total)}</span>
            <button className="btn ghost" disabled={offset + limit >= data.total}
              onClick={() => setOffset(offset + limit)}>Next</button>
          </span>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [openId, setOpenId] = useState(null);
  if (!authed) return <div className="app"><Login onDone={() => setAuthed(true)} /></div>;
  return (
    <div className="app">
      <div className="topbar">
        <div className="brand"><span className="dot" /> AGI Compound Library
          <span className="sub">Genomic.go · secured research access</span></div>
        <button className="btn ghost" onClick={() => { clearToken(); setAuthed(false); }}>Sign out</button>
      </div>
      {openId
        ? <Detail id={openId} onBack={() => setOpenId(null)} />
        : <Library onOpen={setOpenId} />}
    </div>
  );
}
