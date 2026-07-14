"use client";

import { useState } from "react";

const STATS = [
  { v: "425", l: "synthetic compounds" },
  { v: "20", l: "substituent classes" },
  { v: "0.3 µM", l: "best modeled IC50" },
  { v: "CRBN", l: "primary target" },
];

const PILLARS = [
  { icon: "🔬", t: "Deep Research Intelligence", d: "Automated patent scraping and clinical-trials aggregation surface actionable insight in rare, high-value disease areas — ALS, cancer, Parkinson's, and pediatric targets." },
  { icon: "🧪", t: "Synthetic Compound Library", d: "A curated, growing library of 425 designed compounds engineered to hit specific biological targets, with modeled potency, binding energy, and drug-likeness for every entry." },
  { icon: "🕶️", t: "Molecular Dynamics on RP1", d: "Immersive virtual and augmented reality environments on RP1.com's open spatial internet for collaborative molecular visualization and personalized-medicine workflows." },
  { icon: "⚙️", t: "Research Tooling", d: "Optimized pipelines that connect patent data, clinical trials, and compound design into one streamlined discovery workflow." },
];

const ARTICLES = [
  {
    tag: "Drug Discovery",
    t: "Targeted Protein Degradation: Why CRBN Is a High-Value Handle in Oncology",
    d: "Cereblon (CRBN) is the substrate receptor of a CUL4 E3 ubiquitin ligase complex. Molecular glues and degraders that engage CRBN can redirect the cell's own disposal machinery toward disease-driving proteins — including targets long considered 'undruggable.' Our 425-compound library is built on an imidazo[4,5-c]pyridine scaffold designed to modulate CRBN and tip cancer cells toward apoptosis. This piece walks through the mechanism, why degradation beats inhibition for certain targets, and how we score candidates on potency (IC50), binding free energy (ΔG), and drug-likeness.",
    read: "8 min read",
  },
  {
    tag: "Research Strategy",
    t: "Rare, High-Value Targets: The Economics of Underserved Disease",
    d: "ALS, pediatric cancers, and Parkinson's share a hard truth — small patient populations and steep biology have kept them under-invested. But that same scarcity concentrates value: validated candidates in these areas face less crowding and clearer unmet need. We combine patent-landscape scraping with clinical-trials data to pinpoint where a designed compound can matter most, then build toward it deliberately.",
    read: "6 min read",
  },
  {
    tag: "Immersive Science",
    t: "Seeing the Bind: Molecular Dynamics in Extended Reality on RP1",
    d: "Static structures hide how a molecule actually behaves. On RP1.com's open spatial internet, teams step inside a binding pocket together, watch conformational change in real time, and reason about selectivity spatially rather than on a flat screen. This explainer covers how immersive molecular dynamics shortens the loop between hypothesis and refined candidate — and why collaboration in shared space changes the work.",
    read: "7 min read",
  },
  {
    tag: "Data & Pipelines",
    t: "From Patent to Pipeline: Turning Scattered Data Into Discovery Velocity",
    d: "Discovery stalls when patents, trials, and compound data live in separate silos. We connect them into one workflow: intelligence surfaces a target, the library proposes characterized candidates, and immersive tools validate them. This article breaks down the pipeline architecture and how each stage feeds the next.",
    read: "5 min read",
  },
];

const VIDEOS = [
  { t: "Platform Overview: How Science.Delivery Works", d: "A 3-minute tour of the full platform — from research intelligence to characterized compounds to immersive validation on RP1." },
  { t: "Inside the Compound Library", d: "Walk through the 425-compound CRBN-targeted library: SMILES structures, potency and binding metrics, and how to explore it in the secured app." },
  { t: "Molecular Dynamics in XR", d: "See immersive molecular dynamics on RP1 — stepping inside a binding pocket to reason about selectivity and refine candidates together." },
];

type Status = { kind: "idle" | "ok" | "err"; msg: string };

function ContactForm({ investor = false }: { investor?: boolean }) {
  const [status, setStatus] = useState<Status>({ kind: "idle", msg: "" });
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = Object.fromEntries(new FormData(form).entries()) as Record<string, string>;
    if (!data.name || !data.email || !data.message) {
      setStatus({ kind: "err", msg: "Please fill in your name, email, and message." });
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
      setStatus({ kind: "err", msg: "Please enter a valid email address." });
      return;
    }
    setBusy(true);
    setStatus({ kind: "idle", msg: "" });
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data, kind: investor ? "investor" : "general" }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body?.detail || "Send failed");
      setStatus({ kind: "ok", msg: "Thanks — your message is on its way. We'll be in touch shortly." });
      form.reset();
    } catch {
      setStatus({ kind: "err", msg: "We couldn't send that just now. Please email us directly at agi@science.delivery." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="form">
      <div className="row2">
        <div className="field"><label>Full name *</label><input name="name" required placeholder="Jane Researcher" /></div>
        <div className="field"><label>Work email *</label><input name="email" type="email" required placeholder="jane@lab.org" /></div>
      </div>
      <div className="row2">
        <div className="field"><label>Organization</label><input name="organization" placeholder="Institute / company / fund" /></div>
        <div className="field"><label>{investor ? "Intended investment" : "Area of interest"}</label>
          {investor ? (
            <input name="interest" placeholder="e.g. $250,000" />
          ) : (
            <select name="interest" defaultValue="">
              <option value="">Select…</option>
              <option>Compound library access</option>
              <option>Research intelligence / data</option>
              <option>Molecular dynamics on RP1</option>
              <option>Partnership / collaboration</option>
              <option>Other</option>
            </select>
          )}
        </div>
      </div>
      <div className="field"><label>{investor ? "Tell us about your fund / thesis *" : "How can we help? *"}</label>
        <textarea name="message" rows={5} required placeholder={investor ? "Fund, check size, timeline, and what you'd like to review…" : "Tell us about your program, targets, or questions…"} /></div>
      <button className="btn btn-lg" type="submit" disabled={busy}>{busy ? "Sending…" : investor ? "Request the SAFE & data room →" : "Send message →"}</button>
      {status.msg && <p className={`form-status ${status.kind === "ok" ? "ok" : status.kind === "err" ? "err" : ""}`}>{status.msg}</p>}
    </form>
  );
}

export default function Home() {
  const compoundAppUrl = process.env.NEXT_PUBLIC_COMPOUND_APP_URL || "#contact";
  return (
    <main className="site">
      <header className="nav">
        <div className="wrap nav-inner">
          <a className="logo" href="#top"><span className="dot" /> Science<span className="logo-accent">.Delivery</span></a>
          <nav className="nav-links">
            <a href="#platform">Platform</a>
            <a href="#library">Library</a>
            <a href="#insights">Insights</a>
            <a href="#videos">Videos</a>
            <a href="#invest">Invest</a>
            <a className="btn btn-sm" href="#contact">Work with us</a>
          </nav>
        </div>
      </header>

      <section className="hero" id="top">
        <div className="wrap">
          <div className="eyebrow">Computational drug discovery · part of the AGI network</div>
          <h1>Turn scientific data into <span className="grad">discovery velocity</span>.</h1>
          <p className="lede">Science Delivery unifies a growing synthetic compound library, deep research intelligence from patents and clinical trials, and immersive molecular dynamics — so researchers move from hypothesis to validated candidate faster.</p>
          <div className="cta-row">
            <a className="btn btn-lg" href="#contact">Work with us →</a>
            <a className="btn btn-lg btn-ghost" href="#invest">Back the mission</a>
          </div>
          <div className="hero-stats">
            {STATS.map((s) => (<div key={s.l}><strong>{s.v}</strong><span>{s.l}</span></div>))}
          </div>
        </div>
      </section>

      <section id="platform" className="section">
        <div className="wrap">
          <h2 className="section-title">One platform, four capabilities</h2>
          <p className="section-sub">Each pillar feeds the others — data becomes compounds, compounds become validated candidates.</p>
          <div className="grid grid-4">
            {PILLARS.map((p) => (<article className="card" key={p.t}><div className="ic">{p.icon}</div><h3>{p.t}</h3><p>{p.d}</p></article>))}
          </div>
        </div>
      </section>

      <section id="library" className="section section-alt">
        <div className="wrap split">
          <div>
            <div className="eyebrow">Flagship dataset</div>
            <h2 className="section-title left">A CRBN-targeted library, fully characterized</h2>
            <p>Every one of the 425 AGI compounds is designed on an imidazo[4,5-c]pyridine scaffold and modeled for how it modulates the CRBN E3 ubiquitin ligase to induce apoptosis in cancer cells. Each entry carries its SMILES structure, substituent, molecular weight, LogP, binding free energy (ΔG), predicted IC50, and a drug-likeness goodness score.</p>
            <ul className="checklist">
              <li>Searchable, filterable, sortable by potency and drug-likeness</li>
              <li>2D structure rendering for every compound</li>
              <li>Semantic search across mechanism and target</li>
              <li>Secured, access-controlled — data stays protected</li>
            </ul>
            <a className="btn" href={compoundAppUrl}>Request secured access →</a>
          </div>
          <div className="stat-panel">
            {[["Compounds","425"],["Substituent classes","20"],["Best modeled IC50","0.3 µM"],["MW range","286–397 g/mol"],["Primary target","CRBN"],["Therapeutic focus","Oncology"]].map(([k,v]) => (
              <div className="stat-row" key={k}><span>{k}</span><strong>{v}</strong></div>
            ))}
          </div>
        </div>
      </section>

      <section id="insights" className="section">
        <div className="wrap">
          <h2 className="section-title">Insights & articles</h2>
          <p className="section-sub">Deep dives on the science, strategy, and tools behind the platform.</p>
          <div className="grid grid-2">
            {ARTICLES.map((a) => (
              <article className="article" key={a.t}>
                <div className="article-top"><span className="pill">{a.tag}</span><span className="muted small">{a.read}</span></div>
                <h3>{a.t}</h3>
                <p>{a.d}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="videos" className="section section-alt">
        <div className="wrap">
          <h2 className="section-title">Watch & learn</h2>
          <p className="section-sub">Explainers on how the platform works — from data to characterized compounds to immersive validation.</p>
          <div className="grid grid-3">
            {VIDEOS.map((v) => (
              <article className="video" key={v.t}>
                <div className="video-thumb"><span className="play">▶</span><span className="soon">Coming soon</span></div>
                <h3>{v.t}</h3>
                <p>{v.d}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="invest" className="section invest">
        <div className="wrap narrow">
          <div className="eyebrow center">Invest in the mission</div>
          <h2 className="section-title center">Back science that reaches underserved disease</h2>
          <p className="section-sub center">We're raising <strong>$10M on a $75M post-money valuation cap</strong> via SAFE to bring our tools and compound datasets into an intuitive interface and a fully operational fabric on RP1.</p>
          <div className="raise-stats">
            <div><strong>$10M</strong><span>target raise</span></div>
            <div><strong>$75M</strong><span>post-money cap</span></div>
            <div><strong>SAFE</strong><span>post-money, valuation cap</span></div>
          </div>
          <div className="invest-cta">
            <a className="btn btn-lg" href="/downloads/Science-Delivery-SAFE-draft.pdf" target="_blank" rel="noopener">Download the SAFE draft (PDF)</a>
            <a className="btn btn-lg btn-ghost" href="#invest-form">Request the data room →</a>
          </div>
          <p className="disclaimer">The SAFE is a draft for review and not legal advice or an offer to sell securities. Investing involves risk. Consult your own legal and financial advisors; any investment is subject to a definitive executed agreement.</p>
          <div id="invest-form" className="invest-form">
            <h3 className="center">Investor inquiry</h3>
            <ContactForm investor />
          </div>
        </div>
      </section>

      <section id="contact" className="section contact">
        <div className="wrap narrow">
          <div className="eyebrow center">Get in touch</div>
          <h2 className="section-title center">Let's move your program forward</h2>
          <p className="section-sub center">Tell us what you're working on. We'll get back to you at the email you provide.</p>
          <ContactForm />
        </div>
      </section>

      <footer className="footer">
        <div className="wrap footer-inner">
          <div>
            <div className="logo"><span className="dot" /> Science<span className="logo-accent">.Delivery</span></div>
            <p className="muted small">A W3 LLC series corp in the AGI network. Computational drug discovery, synthetic compound design, and immersive molecular science.</p>
          </div>
          <div className="foot-links">
            <a href="#platform">Platform</a><a href="#library">Library</a><a href="#insights">Insights</a>
            <a href="#invest">Invest</a><a href="mailto:agi@science.delivery">agi@science.delivery</a>
          </div>
        </div>
        <div className="wrap sub-foot muted small">© {new Date().getFullYear()} Science Delivery. All rights reserved.</div>
      </footer>
    </main>
  );
}
