"""PromoFinder Studio — Streamlit UI for timestamped microdrama promo discovery.

No confidential source screenplay files are bundled or persisted by this application.
"""
import io
import re
import tempfile
import zipfile
from pathlib import Path

import streamlit as st
from src.promofinder import run

st.set_page_config(
    page_title="PromoFinder Studio | Microdrama Intelligence",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root {--accent:#c8fc65;--ink:#e9edf5;--muted:#9ea9bd;}
html,body,[class*="css"],.stApp {font-family:'DM Sans',sans-serif;}
.stApp {background:radial-gradient(circle at 90% 2%,rgba(92,103,170,.15),transparent 28%),#0b1020;color:#ecf1fa;}
[data-testid="stSidebar"] {background:#10192b;border-right:1px solid #27344b;}
[data-testid="stHeader"] {background:rgba(11,16,32,.85);}
.block-container {padding-top:2.1rem;padding-bottom:3rem;max-width:1330px;}
h1,h2,h3,h4 {font-family:'Space Grotesk',sans-serif;letter-spacing:-.025em;}
h1 {font-size:2.65rem!important;} h3 {font-size:1.22rem!important;}
.hero {padding:27px 32px;border:1px solid #374359;border-radius:22px;background:linear-gradient(112deg,#192644,#111b2f 65%,#172d29);margin-bottom:18px;}
.eyebrow {font-size:.7rem;letter-spacing:.19em;font-weight:800;color:var(--accent);text-transform:uppercase;}
.hero h1 {margin:11px 0 8px;color:#fff;line-height:1.08;}
.hero p {font-size:1rem;color:#b7c3d5;max-width:730px;margin:0;line-height:1.6;}
.hero .chips {margin-top:20px;display:flex;gap:9px;flex-wrap:wrap;}
.chip {font-size:.73rem;font-weight:700;border:1px solid #43536b;border-radius:20px;padding:6px 11px;color:#cdd8e7;}
.section-kicker {color:#a3b3cb;letter-spacing:.12em;text-transform:uppercase;font-size:.72rem;font-weight:800;margin-bottom:5px;}
.metric-card {border:1px solid #2f3c52;background:#121d31;border-radius:16px;padding:16px 20px;min-height:115px;}
.metric-label {color:#9daec3;font-size:.78rem;font-weight:700;}
.metric-value {font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:700;color:#eff6ff;margin-top:5px;}
.promo-card {padding:20px 23px;border:1px solid #34415a;border-radius:17px;background:linear-gradient(100deg,#18243b,#101b2e);margin-bottom:11px;}
.promo-kicker {font-size:.72rem;letter-spacing:.09em;color:#baccdf;font-weight:700;text-transform:uppercase;}
.promo-title {font-size:1.22rem;font-weight:800;color:#f0f4fb;line-height:1.45;margin:7px 0;}
.promo-meta {color:#b7c6d9;font-size:.8rem;}
.score-tag {display:inline-block;background:rgba(200,252,101,.11);color:#d8ffa3;border:1px solid #617d46;border-radius:9px;padding:4px 9px;font-size:.85rem;font-weight:800;}
.small-note {font-size:.8rem;color:#aebbd0;line-height:1.6;}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"] {background:#c8fc65!important;color:#14200a!important;border:0!important;font-weight:800!important;border-radius:10px!important;}
.stButton>button {border-radius:10px!important;}
[data-testid="stFileUploader"] {border-radius:12px;}
[data-testid="stTabs"] button {font-weight:700;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)


def escape_html(value):
    """Escape untrusted source text before inserting into custom HTML cards."""
    import html
    return html.escape(str(value), quote=True)


def extract_scripts(payload, destination):
    """Extract only matching screenplay TXT members, limiting unsafe ZIP payloads."""
    if len(payload) > 15 * 1024 * 1024:
        raise ValueError("ZIP is too large (15 MB upload limit).")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        valid = [
            member for member in archive.infolist()
            if not member.is_dir()
            and re.fullmatch(r"episode-\d+-[^/\\]*\.txt", Path(member.filename).name, re.IGNORECASE)
        ]
        if not valid:
            raise ValueError("No files named episode-001-*.txt, episode-002-*.txt, etc. were found.")
        if len(valid) > 200:
            raise ValueError("Too many screenplay files (maximum 200).")
        if sum(member.file_size for member in valid) > 25 * 1024 * 1024:
            raise ValueError("Uncompressed screenplay content exceeds 25 MB.")
        names = set()
        for member in valid:
            basename = Path(member.filename).name
            if basename.casefold() in names:
                raise ValueError(f"Duplicate screenplay filename: {basename}")
            names.add(basename.casefold())
            if member.file_size > 5 * 1024 * 1024:
                raise ValueError(f"A screenplay exceeds 5 MB: {basename}")
            with archive.open(member) as source:
                (destination / basename).write_bytes(source.read())
        return len(valid)


def analyze(payload, count):
    with tempfile.TemporaryDirectory(prefix="promofinder_") as tmp:
        root = Path(tmp)
        scripts = root / "scripts"
        scripts.mkdir()
        extract_scripts(payload, scripts)
        results, audit = run(scripts, root / "outputs", top=count)
        outputs = {
            "ranked_csv": (root / "outputs/promos_ranked.csv").read_bytes(),
            "ranked_json": (root / "outputs/promos_ranked.json").read_bytes(),
            "per_episode": (root / "outputs/best_per_episode.json").read_bytes(),
            "audit_json": (root / "outputs/quality_audit.json").read_bytes(),
        }
    return results, audit, outputs


def metric(label, value):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{escape_html(label)}</div>'
                f'<div class="metric-value">{escape_html(value)}</div></div>', unsafe_allow_html=True)


st.markdown("""
<div class="hero">
  <div class="eyebrow">✦ Kuku • Editorial Intelligence Prototype</div>
  <h1>Find the moment.<br><span style="color:#c8fc65">Make them watch.</span></h1>
  <p>Turn timestamped microdrama screenplays into a shortlist of high-impact promo clips.
  Discover sharp hooks, unresolved endings, and self-contained stories—without manually combing through episodes.</p>
  <div class="chips"><span class="chip">⚡ Hook-first ranking</span><span class="chip">◷ 20–60 second clips</span><span class="chip">◎ Explainable scores</span><span class="chip">⇩ Export-ready results</span></div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🎬 PromoFinder Studio")
    st.caption("SCREENPLAY → PROMO SHORTLIST")
    st.divider()
    st.markdown("#### 01  ·  Input screenplay")
    upload = st.file_uploader("Episode screenplay ZIP", type=["zip"], help="ZIP containing episode-001-*.txt, episode-002-*.txt, etc.")
    st.markdown("#### 02  ·  Output settings")
    count = st.slider("Top promos to recommend", 5, 40, 20, step=5)
    run_clicked = st.button("⚡ Analyze screenplays", type="primary", use_container_width=True, disabled=upload is None)
    if st.button("↺ Clear previous results", use_container_width=True):
        for key in ("pf_results", "pf_audit", "pf_outputs", "pf_filename"):
            st.session_state.pop(key, None)
        st.rerun()
    st.divider()
    st.markdown("#### HOW IT WORKS")
    st.caption("1  Parse screenplay timestamps\n\n2  Generate 20–60s clip candidates\n\n3  Score hook, cliffhanger & clarity\n\n4  Diversify and rank suggestions")
    st.info("Scores are editorial heuristics, **not** estimates of views, retention, or conversion.", icon="ℹ️")

if run_clicked:
    try:
        with st.spinner("Reading episodes, generating clips and ranking the strongest moments…"):
            result, audit, output_files = analyze(upload.getvalue(), count)
        st.session_state["pf_results"] = result
        st.session_state["pf_audit"] = audit
        st.session_state["pf_outputs"] = output_files
        st.session_state["pf_filename"] = upload.name
        st.toast("Promo analysis complete!", icon="✅")
    except (ValueError, zipfile.BadZipFile, UnicodeError, OSError, AssertionError) as exc:
        st.error(f"Could not analyze the archive: {exc}")
    except Exception:
        st.error("Analysis failed. Check screenplay filenames and timestamps before retrying.")

if "pf_results" not in st.session_state:
    st.markdown('<div class="section-kicker">Welcome to your workspace</div>', unsafe_allow_html=True)
    st.subheader("Your next breakout moment starts with a screenplay.")
    a, b, c = st.columns(3)
    with a:
        metric("01 / INPUT", "Upload ZIP")
        st.caption("Use timestamped episode screenplay TXT files.")
    with b:
        metric("02 / ANALYSIS", "Rank clips")
        st.caption("Evaluate hooks, suspense and standalone clarity.")
    with c:
        metric("03 / EXPORT", "CSV + JSON")
        st.caption("Save promo recommendations and quality checks.")
    st.warning("**Confidentiality:** Kuku supplied the screenplays for this assignment. Do not upload them to an externally hosted service unless Kuku permits that processing. For a public demo, use synthetic data.")
else:
    results = st.session_state["pf_results"]
    audit = st.session_state["pf_audit"]
    downloads = st.session_state["pf_outputs"]
    promos = results["top_promos"]
    st.markdown('<div class="section-kicker">Analysis dashboard / completed run</div>', unsafe_allow_html=True)
    st.caption(f"Input: {st.session_state.get('pf_filename', 'Screenplay upload')} · Method: deterministic heuristic ranking")
    m1, m2, m3, m4 = st.columns(4)
    with m1: metric("Episodes scanned", audit["total_episodes"])
    with m2: metric("Timestamped events", f"{audit['total_events']:,}")
    with m3: metric("Candidate clips", f"{audit['candidate_count_after_local_dedup']:,}")
    with m4: metric("Recommended promos", len(promos))

    tab1, tab2, tab3 = st.tabs(["✨  Ranked promos", "📊  Episode insights", "⬇  Exports & quality"])
    with tab1:
        st.markdown("### Your top-ranked promo moments")
        st.caption("Prioritized to support editorial review—not an automated publishing decision.")
        f1, f2, f3 = st.columns([1.2, 1, 1])
        with f1:
            search = st.text_input("Search in hook / ending", placeholder="e.g. betrayal, secret, poison")
        with f2:
            episode_options = sorted({int(p["episode"]) for p in promos})
            ep_filter = st.selectbox("Filter episode", ["All episodes"] + episode_options)
        with f3:
            sort_order = st.selectbox("Sort clips", ["Highest score", "Episode order", "Longest duration"])
        selected = [p for p in promos if (ep_filter == "All episodes" or int(p["episode"]) == ep_filter)
                    and (not search or search.casefold() in (str(p.get("hook", "")) + " " + str(p.get("cliffhanger", "")) + " " + str(p.get("reason", ""))).casefold())]
        if sort_order == "Episode order":
            selected.sort(key=lambda p: (int(p["episode"]), p["start_seconds"]))
        elif sort_order == "Longest duration":
            selected.sort(key=lambda p: -p["duration_seconds"])
        else:
            selected.sort(key=lambda p: int(p["rank"]))
        st.caption(f"Showing {len(selected)} of {len(promos)} recommendations")
        if not selected:
            st.info("No clips match these filters. Try another search or episode.")
        for p in selected:
            title = escape_html(str(p.get("hook", "")).strip() or "Untitled promo")
            title = title[:185] + ("…" if len(title) > 185 else "")
            st.markdown(f'''<div class="promo-card">
                <div class="promo-kicker">RANK #{int(p['rank']):02d} &nbsp;•&nbsp; EPISODE {int(p['episode']):02d}</div>
                <div class="promo-title">{title}</div>
                <div class="promo-meta">◷ {escape_html(p['start'])} → {escape_html(p['end'])} &nbsp;·&nbsp; {float(p['duration_seconds']):.1f} seconds &nbsp;&nbsp; <span class="score-tag">★ {float(p['score']):.1f}/100</span></div>
            </div>''', unsafe_allow_html=True)
            with st.expander(f"See edit decision & score breakdown · Rank #{int(p['rank'])}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**🎯 Opening hook**")
                    st.write(p["hook"])
                with c2:
                    st.markdown("**⏳ Cliffhanger / final beat**")
                    st.write(p["cliffhanger"])
                st.markdown("**Why this clip could work**")
                st.write(p["reason"])
                s1, s2, s3 = st.columns(3)
                s1.metric("Hook score", f"{float(p['hook_score']):.1f}")
                s2.metric("Cliffhanger score", f"{float(p['cliffhanger_score']):.1f}")
                s3.metric("Standalone score", f"{float(p['standalone_score']):.1f}")

    with tab2:
        st.markdown("### Episode coverage & clip profiles")
        st.caption("Quality audit from the current screenplay run. Charts describe parsed inputs and heuristic output—not audience behavior.")
        table = audit["episode_summary"]
        graph_rows = [{"Episode": f"E{int(row['episode']):02d}", "Events": int(row["events"]), "Dialogue": int(row["dialogue_events"]), "Actions": int(row["action_events"])} for row in table]
        if graph_rows:
            st.bar_chart(graph_rows, x="Episode", y=["Dialogue", "Actions"], use_container_width=True)
        st.markdown("**Per-episode analysis**")
        st.dataframe(graph_rows, hide_index=True, use_container_width=True)
        st.markdown("**Selected promo duration distribution**")
        if promos:
            st.bar_chart([{"Promo": f"#{p['rank']}", "Seconds": float(p["duration_seconds"])} for p in promos], x="Promo", y="Seconds", use_container_width=True)

    with tab3:
        st.markdown("### Download your deliverables")
        st.caption("Raw exports reflect the unedited output of this run. Screenplay excerpts may be present in JSON/CSV files.")
        d1, d2 = st.columns(2)
        with d1:
            st.download_button("↓ Ranked promos · CSV", downloads["ranked_csv"], file_name="promos_ranked.csv", mime="text/csv", use_container_width=True, type="primary")
            st.download_button("↓ Ranked promos · JSON", downloads["ranked_json"], file_name="promos_ranked.json", mime="application/json", use_container_width=True)
        with d2:
            st.download_button("↓ Best promo per episode · JSON", downloads["per_episode"], file_name="best_per_episode.json", mime="application/json", use_container_width=True)
            st.download_button("↓ Full quality audit · JSON", downloads["audit_json"], file_name="quality_audit.json", mime="application/json", use_container_width=True)
        st.markdown("### Quality guardrails")
        checks = [
            ("All suggested clips are 20–60 seconds", all(20 <= p["duration_seconds"] <= 60 for p in promos)),
            ("No invalid parsed timestamp bounds", audit["invalid_event_bounds"] == 0),
            ("No episodes with zero parsed events", not audit["zero_parsed_events"]),
        ]
        for label, ok in checks:
            st.write(("✅" if ok else "⚠️") + " " + label)
        with st.expander("Known limitations and editorial failure modes", expanded=True):
            for item in audit["limitations"]:
                st.write("• " + item)
        st.warning("**Editorial review required:** Confirm the first 3 seconds, self-contained story, continuity, exact frame cuts and cliffhanger in the original footage before publishing.")
        st.info("**Privacy reminder:** Do not publish confidential original scripts or exported dialogue snippets in a public GitHub repository.")

st.markdown('<p class="small-note" style="text-align:center;margin-top:35px">PROMOFINDER STUDIO &nbsp;·&nbsp; Built for editorial discovery &nbsp;·&nbsp; Transparent heuristic prototype</p>', unsafe_allow_html=True)
