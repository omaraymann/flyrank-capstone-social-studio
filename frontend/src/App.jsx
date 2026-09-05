import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";

const initialCampaign = {
  title: "",
  markdown: "",
  platforms: ["x", "linkedin"],
  generation_mode: "llm",
  audience: "data engineers",
  goal: "traffic",
  tone: "educational",
  call_to_action: "Read the complete article",
};

function StatusPill({ status }) {
  return <span className={`pill pill-${status}`}>{status}</span>;
}

function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("demo-password-2026");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "signup") await api("/auth/signup", { method: "POST", body: { email, password } });
      const result = await api("/auth/login", { method: "POST", body: { email, password } });
      onAuthenticated(result.access_token, email);
    } catch (reason) {
      setError(reason.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-story">
        <div className="brand"><span className="brand-mark">S</span> Social Media Studio</div>
        <p className="eyebrow">AI CAMPAIGN OPERATIONS</p>
        <h1>One article.<br /><em>Every channel.</em></h1>
        <p className="hero-copy">Generate, review, schedule, and observe platform-ready campaigns from one calm workspace.</p>
        <div className="flow-strip"><span>Source</span><b>→</b><span>Generate</span><b>→</b><span>Approve</span><b>→</b><span>Publish</span></div>
      </section>
      <form className="auth-card" onSubmit={submit}>
        <p className="eyebrow">WELCOME</p>
        <h2>{mode === "login" ? "Open your studio" : "Create your studio"}</h2>
        <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength="8" required /></label>
        {error && <div className="alert error">{error}</div>}
        <button className="button primary full" disabled={busy}>{busy ? "Working…" : mode === "login" ? "Sign in" : "Create account"}</button>
        <button type="button" className="text-button" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}>
          {mode === "login" ? "Need an account? Sign up" : "Already registered? Sign in"}
        </button>
      </form>
    </main>
  );
}

function Composer({ token, onCreated, notify }) {
  const [form, setForm] = useState(initialCampaign);
  const [busy, setBusy] = useState(false);
  const update = (field, value) => setForm((current) => ({ ...current, [field]: value }));

  function togglePlatform(platform) {
    update("platforms", form.platforms.includes(platform)
      ? form.platforms.filter((item) => item !== platform)
      : [...form.platforms, platform]);
  }

  async function generate(event) {
    event.preventDefault();
    if (!form.platforms.length) return notify("Choose at least one platform", "error");
    setBusy(true);
    try {
      const post = await api("/posts", { token, method: "POST", body: { title: form.title, markdown: form.markdown } });
      await api(`/posts/${post.id}/variants`, {
        token,
        method: "POST",
        body: {
          platforms: form.platforms,
          generation_mode: form.generation_mode,
          audience: form.audience,
          goal: form.goal,
          tone: form.tone,
          call_to_action: form.call_to_action,
        },
      });
      notify(`${form.generation_mode === "llm" ? "Gemini" : "Template"} drafts created`);
      setForm((current) => ({ ...initialCampaign, generation_mode: current.generation_mode }));
      onCreated(post.id);
    } catch (reason) {
      notify(reason.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel composer" onSubmit={generate}>
      <div className="section-heading"><div><p className="eyebrow">NEW CAMPAIGN</p><h2>Turn a story into a campaign</h2></div><span className="step-number">01</span></div>
      <div className="field-grid two">
        <label>Article title<input value={form.title} onChange={(e) => update("title", e.target.value)} placeholder="What is your article about?" required /></label>
        <label>Audience<input value={form.audience} onChange={(e) => update("audience", e.target.value)} required /></label>
      </div>
      <label>Article content<textarea className="source-input" value={form.markdown} onChange={(e) => update("markdown", e.target.value)} placeholder="Paste at least 20 characters of Markdown…" minLength="20" required /></label>
      <div className="field-grid three">
        <label>Generator<select value={form.generation_mode} onChange={(e) => update("generation_mode", e.target.value)}><option value="llm">Gemini 2.5 Flash</option><option value="deterministic">Deterministic templates</option></select></label>
        <label>Goal<select value={form.goal} onChange={(e) => update("goal", e.target.value)}>{["awareness", "engagement", "traffic", "conversion"].map((v) => <option key={v}>{v}</option>)}</select></label>
        <label>Tone<select value={form.tone} onChange={(e) => update("tone", e.target.value)}>{["professional", "friendly", "educational", "energetic"].map((v) => <option key={v}>{v}</option>)}</select></label>
      </div>
      <label>Call to action<input value={form.call_to_action} onChange={(e) => update("call_to_action", e.target.value)} required /></label>
      <div className="composer-footer">
        <div className="platform-picker">{["x", "linkedin", "discord"].map((platform) => <button type="button" key={platform} className={form.platforms.includes(platform) ? "platform active" : "platform"} onClick={() => togglePlatform(platform)}>{platform === "x" ? "𝕏" : platform === "linkedin" ? "in" : "◉"} {platform}</button>)}</div>
        <button className="button primary" disabled={busy}>{busy ? "Generating…" : "Generate campaign →"}</button>
      </div>
    </form>
  );
}

function VariantCard({ variant, schedule, token, refresh, notify }) {
  const [content, setContent] = useState(variant.content);
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [publishAt, setPublishAt] = useState(() => {
    const date = new Date(Date.now() + 5 * 60 * 1000);
    return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  });
  const [busy, setBusy] = useState("");
  const limit = variant.platform === "x" ? 280 : variant.platform === "discord" ? 2000 : 3000;

  async function action(name, request) {
    setBusy(name);
    try { await request(); notify(`${name} complete`); await refresh(); }
    catch (reason) { notify(reason.message, "error"); }
    finally { setBusy(""); }
  }

  return (
    <article className="variant-card">
      <header><div className={`platform-icon ${variant.platform}`}>{variant.platform === "x" ? "𝕏" : variant.platform === "linkedin" ? "in" : "◉"}</div><div><h3>{variant.platform}</h3><StatusPill status={variant.status} /></div></header>
      <textarea value={content} disabled={variant.status !== "draft"} onChange={(e) => setContent(e.target.value)} />
      <div className="character-count"><span>{content.length} / {limit}</span><span>{content.split(/\s+/).filter((word) => word.startsWith("#")).length} hashtags</span></div>
      {variant.status === "draft" && <div className="button-row">
        <button className="button subtle" disabled={!!busy || content === variant.content} onClick={() => action("Save", () => api(`/variants/${variant.id}`, { token, method: "PATCH", body: { content } }))}>Save edit</button>
        <button className="button approve" disabled={!!busy} onClick={() => action("Approval", () => api(`/variants/${variant.id}/approve`, { token, method: "POST" }))}>Approve ✓</button>
        <button className="button reject" disabled={!!busy} onClick={() => setShowReject((visible) => !visible)}>Reject</button>
      </div>}
      {variant.status === "draft" && showReject && <div className="reject-box">
        <input value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="Why is this draft unsuitable?" minLength="3" />
        <button className="button reject" disabled={!!busy || rejectReason.trim().length < 3} onClick={() => action("Rejection", () => api(`/variants/${variant.id}/reject`, { token, method: "POST", body: { reason: rejectReason.trim() } }))}>Confirm reject</button>
      </div>}
      {variant.status === "rejected" && variant.rejection_reason && <div className="rejection-note"><b>Rejection reason</b><span>{variant.rejection_reason}</span></div>}
      {variant.status === "approved" && <div className="schedule-box">
        <input type="datetime-local" value={publishAt} onChange={(e) => setPublishAt(e.target.value)} />
        <button className="button approve" disabled={!!busy} onClick={() => action("Scheduling", () => api(`/variants/${variant.id}/schedule`, { token, method: "POST", body: { publish_at: new Date(publishAt).toISOString() } }))}>Schedule</button>
      </div>}
      {schedule && <div className="schedule-state"><span>Schedule #{schedule.id}</span><StatusPill status={schedule.status} />{schedule.status === "pending" && <button className="text-button" onClick={() => action("Publishing", () => api(`/schedules/${schedule.id}/publish`, { token, method: "POST" }))}>Publish now</button>}</div>}
    </article>
  );
}

function Workspace({ token, email, logout }) {
  const [posts, setPosts] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [variants, setVariants] = useState([]);
  const [generations, setGenerations] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [publishHistory, setPublishHistory] = useState([]);
  const [notice, setNotice] = useState(null);

  const notify = useCallback((message, type = "success") => {
    setNotice({ message, type });
    window.setTimeout(() => setNotice(null), 4500);
  }, []);

  const refreshAll = useCallback(async (preferredId) => {
    try {
      const [postRows, scheduleRows, historyRows] = await Promise.all([
        api("/posts", { token }), api("/schedules", { token }), api("/publish-history", { token }),
      ]);
      setPosts(postRows); setSchedules(scheduleRows); setPublishHistory(historyRows);
      const id = preferredId || selectedId || postRows[0]?.id;
      setSelectedId(id || null);
      if (id) {
        const [variantRows, generationRows] = await Promise.all([
          api(`/posts/${id}/variants`, { token }), api(`/posts/${id}/generations`, { token }),
        ]);
        setVariants(variantRows); setGenerations(generationRows);
      } else { setVariants([]); setGenerations([]); }
    } catch (reason) { notify(reason.message, "error"); }
  }, [token, selectedId, notify]);

  useEffect(() => { refreshAll(); }, []); // Load once; actions perform explicit refreshes.
  const schedulesByVariant = useMemo(() => Object.fromEntries(schedules.map((item) => [item.variant_id, item])), [schedules]);
  const selectedPost = posts.find((post) => post.id === selectedId);

  return (
    <div className="app-shell">
      <nav><div className="brand"><span className="brand-mark">S</span><span>Social Media Studio<small>Campaign operations</small></span></div><div className="nav-actions"><span className="api-live"><i /> API live</span><span className="user-chip">{email.slice(0, 1).toUpperCase()}</span><button className="text-button" onClick={logout}>Sign out</button></div></nav>
      {notice && <div className={`toast ${notice.type}`}>{notice.message}</div>}
      <main className="dashboard">
        <header className="page-heading"><div><p className="eyebrow">WORKSPACE</p><h1>Campaign control room</h1><p>From source article to published post—with every decision visible.</p></div><div className="metric-row"><div><b>{posts.length}</b><span>Campaigns</span></div><div><b>{variants.length}</b><span>Drafts</span></div><div><b>{publishHistory.length}</b><span>Deliveries</span></div></div></header>
        <Composer token={token} notify={notify} onCreated={(id) => refreshAll(id)} />

        <section className="workspace-grid">
          <aside className="panel campaign-list"><div className="section-heading compact"><div><p className="eyebrow">LIBRARY</p><h2>Campaigns</h2></div><span>{posts.length}</span></div>{posts.map((post) => <button key={post.id} className={selectedId === post.id ? "campaign active" : "campaign"} onClick={() => refreshAll(post.id)}><b>{post.title}</b><small>#{post.id} · {new Date(post.created_at).toLocaleDateString()}</small></button>)}{!posts.length && <p className="empty">Your generated campaigns will appear here.</p>}</aside>
          <section className="campaign-detail">
            <div className="section-heading"><div><p className="eyebrow">REVIEW QUEUE</p><h2>{selectedPost?.title || "No campaign selected"}</h2></div><span className="step-number">02</span></div>
            <div className="variant-grid">{variants.map((variant) => <VariantCard key={variant.id} variant={variant} schedule={schedulesByVariant[variant.id]} token={token} refresh={() => refreshAll(selectedId)} notify={notify} />)}{!variants.length && <div className="empty large">Create a campaign above to review its platform drafts.</div>}</div>
          </section>
        </section>

        <section className="insights-grid">
          <div className="panel"><div className="section-heading compact"><div><p className="eyebrow">AI OBSERVABILITY</p><h2>Generation audit</h2></div><span className="step-number">03</span></div>{generations.map((run) => <div className="audit-row" key={run.id}><div><b>{run.model}</b><span>{run.platforms} · {run.prompt_version}</span></div><div className="audit-metrics"><span>{run.input_tokens ?? "—"} in</span><span>{run.output_tokens ?? "—"} out</span><span>{run.latency_ms ? `${(run.latency_ms / 1000).toFixed(1)}s` : "—"}</span><StatusPill status={run.status} /></div></div>)}{!generations.length && <p className="empty">LLM runs for this campaign will appear here.</p>}</div>
          <div className="panel"><div className="section-heading compact"><div><p className="eyebrow">DELIVERY LOG</p><h2>Publish history</h2></div><button className="text-button" onClick={() => refreshAll(selectedId)}>Refresh</button></div>{publishHistory.slice(0, 6).map(({ delivery, attempts }) => <div className="audit-row" key={delivery.id}><div><b>{delivery.platform} · delivery #{delivery.id}</b><span>{attempts.length} attempt{attempts.length === 1 ? "" : "s"}</span></div><StatusPill status={delivery.status} /></div>)}{!publishHistory.length && <p className="empty">Published posts and attempts will appear here.</p>}</div>
        </section>
      </main>
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem("studio_token"));
  const [email, setEmail] = useState(() => localStorage.getItem("studio_email") || "user");
  function authenticated(nextToken, nextEmail) { localStorage.setItem("studio_token", nextToken); localStorage.setItem("studio_email", nextEmail); setToken(nextToken); setEmail(nextEmail); }
  function logout() { localStorage.removeItem("studio_token"); localStorage.removeItem("studio_email"); setToken(null); }
  return token ? <Workspace token={token} email={email} logout={logout} /> : <AuthScreen onAuthenticated={authenticated} />;
}
