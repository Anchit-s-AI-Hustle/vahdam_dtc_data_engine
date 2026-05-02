"""
Replace sidebar with clean version:
- Remove all count badges and meta pills
- Each sidebar tile shows a thin proportional bar at its bottom edge
  indicating relative content density. Longer = more content on that page.
- No text labels. Just the bar.
"""
import re, pathlib

HTML = pathlib.Path(r"c:\Users\Archit Tandon\Desktop\vahdam-dtc-data-engine\reports\strategy.html")
html = HTML.read_text(encoding="utf-8")

# Remove the count CSS we added last time
html = re.sub(r'/\* ── SIDEBAR COUNT BADGES ──[\s\S]+?\.sb-tier-row \{[\s\S]+?\}\n', '', html)

DENSITY_CSS = """
/* ── SIDEBAR DENSITY BARS ── */
.sb-bar {
  height: 3px;
  border-radius: 2px;
  margin: 5px 16px 2px;
  background: var(--border);
  overflow: hidden;
}
.sb-bar-fill {
  height: 100%;
  border-radius: 2px;
  opacity: .55;
}
details.sb-sec > summary { padding-bottom: 4px; }

.sb-tier-row {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 16px 2px 20px;
  font-size: .67rem; font-weight: 700;
  color: var(--text3);
  border-top: 1px solid var(--border);
  margin-top: 4px;
  text-transform: uppercase; letter-spacing: .06em;
}
.sb-tier-dot {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}
.sb-meta { display: none; }
.sb-count { display: none; }
"""
html = html.replace("</style>", DENSITY_CSS + "\n</style>", 1)

def chev():
    return '<svg class="sb-chevron" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="3,5 7,9 11,5"/></svg>'

def bar(pct, color):
    """Thin proportional bar. pct = 0–100 relative to densest section."""
    return f'<div class="sb-bar"><div class="sb-bar-fill" style="width:{pct}%;background:{color}"></div></div>'

# Densities (relative, max=100):
# Questions groups — normalised over max 5 cards
# Strategies — based on content volume (workflows + funnels + SQL blocks)
# Sections — estimated reading weight

NEW_SIDEBAR = f"""<aside id="sidebar">
  <div class="sb-brand">VAHDAM &nbsp;<strong>DTC Analytics</strong></div>

  <!-- KEY QUESTIONS -->
  <details class="sb-sec" open>
    <summary>
      <span class="sb-sec-icon">❓</span>
      <span class="sb-sec-label">Key Questions</span>
      {chev()}
    </summary>
    {bar(100, '#7c3aed')}
    <div class="sb-sec-body">
      <a class="sb-link sb-top" href="#questions">All Questions</a>
      <div class="sb-divider"></div>
      <a class="sb-link" href="#qg-revenue">💰 Revenue &amp; Margin</a>
      {bar(80, '#d97706')}
      <a class="sb-link" href="#qg-economics">📐 Customer Economics</a>
      {bar(80, '#0d9488')}
      <a class="sb-link" href="#qg-retention">🔁 Retention &amp; Churn</a>
      {bar(100, '#7c3aed')}
      <a class="sb-link" href="#qg-channel">📧 Channel &amp; Email</a>
      {bar(40, '#16a34a')}
      <a class="sb-link" href="#qg-conversion">🛒 Conversion &amp; Mix</a>
      {bar(80, '#2563eb')}
    </div>
  </details>

  <!-- METRICS FRAMEWORK -->
  <details class="sb-sec" open>
    <summary>
      <span class="sb-sec-icon">📊</span>
      <span class="sb-sec-label">Metrics Framework</span>
      {chev()}
    </summary>
    {bar(85, '#d97706')}
    <div class="sb-sec-body">
      <a class="sb-link sb-top" href="#overview">Overview &amp; Pyramid</a>
      <div class="sb-divider"></div>
      <div class="sb-tier-row"><span class="sb-tier-dot" style="background:#d97706"></span>Tier 1 — Business Health</div>
      <a class="sb-link" href="#metric-m1"><span class="sb-dot" style="background:#d97706"></span>M1 · Net Revenue by Market</a>
      <a class="sb-link" href="#metric-m2"><span class="sb-dot" style="background:#d97706"></span>M2 · New vs Returning</a>
      <a class="sb-link" href="#metric-m3"><span class="sb-dot" style="background:#0d9488"></span>M3 · LTV:CAC by Channel</a>
      <a class="sb-link" href="#metric-m4"><span class="sb-dot" style="background:#7c3aed"></span>M4 · Repeat Rate 90d</a>
      <a class="sb-link" href="#metric-m5"><span class="sb-dot" style="background:#d97706"></span>M5 · Gross Margin %</a>
      <div class="sb-tier-row"><span class="sb-tier-dot" style="background:#0d9488"></span>Tier 2 — Growth Levers</div>
      <a class="sb-link" href="#metric-m6"><span class="sb-dot" style="background:#0d9488"></span>M6 · CAC by Channel</a>
      <a class="sb-link" href="#metric-m7"><span class="sb-dot" style="background:#7c3aed"></span>M7 · Email Revenue %</a>
      <a class="sb-link" href="#metric-m8"><span class="sb-dot" style="background:#d97706"></span>M8 · AOV Trend MoM</a>
      <a class="sb-link" href="#metric-m9"><span class="sb-dot" style="background:#2563eb"></span>M9 · Checkout Funnel</a>
      <a class="sb-link" href="#metric-m10"><span class="sb-dot" style="background:#e11d48"></span>M10 · Subscription Mix</a>
      <div class="sb-tier-row"><span class="sb-tier-dot" style="background:#7c3aed"></span>Tier 3 — Retention Intel</div>
      <a class="sb-link" href="#metric-m11"><span class="sb-dot" style="background:#7c3aed"></span>M11 · Cohort Retention</a>
      <a class="sb-link" href="#metric-m12"><span class="sb-dot" style="background:#7c3aed"></span>M12 · Time to 2nd Purchase</a>
      <a class="sb-link" href="#metric-m13"><span class="sb-dot" style="background:#7c3aed"></span>M13 · Churn Risk</a>
      <a class="sb-link" href="#metric-m14"><span class="sb-dot" style="background:#e11d48"></span>M14 · At-Risk Revenue</a>
      <a class="sb-link" href="#metric-m15"><span class="sb-dot" style="background:#e11d48"></span>M15 · Product Repeat Rate</a>
      <a class="sb-link" href="#metric-bonus"><span class="sb-dot" style="background:#0d9488"></span>BONUS · LTV by Market</a>
    </div>
  </details>

  <!-- STRATEGIES -->
  <details class="sb-sec" open>
    <summary>
      <span class="sb-sec-icon">🗺</span>
      <span class="sb-sec-label">Strategies</span>
      {chev()}
    </summary>
    {bar(90, '#e11d48')}
    <div class="sb-sec-body">
      <a class="sb-link sb-top" href="#s1"><span class="sb-strat" style="background:#7c3aed">S1</span>Retention Engine</a>
      {bar(65, '#7c3aed')}
      <a class="sb-link sb-top" href="#s2"><span class="sb-strat" style="background:#0d9488">S2</span>Channel Efficiency</a>
      {bar(90, '#0d9488')}
      <a class="sb-link sb-top" href="#s3"><span class="sb-strat" style="background:#d97706">S3</span>Geo Expansion</a>
      {bar(50, '#d97706')}
      <a class="sb-link sb-top" href="#s4"><span class="sb-strat" style="background:#e11d48">S4</span>Subscription Flywheel</a>
      {bar(80, '#e11d48')}
      <a class="sb-link sb-top" href="#s5"><span class="sb-strat" style="background:#2563eb">S5</span>Funnel Conversion</a>
      {bar(75, '#2563eb')}
    </div>
  </details>

  <div class="sb-divider"></div>
  <a class="sb-standalone" href="#arch">🏗 &nbsp;Data Architecture</a>
  {bar(95, '#2563eb')}
  <a class="sb-standalone" href="#roadmap">🗓 &nbsp;Roadmap</a>
  {bar(40, '#d97706')}
</aside>"""

old = re.search(r'<aside id="sidebar">[\s\S]+?</aside>', html)
if not old:
    print("ERROR: sidebar not found"); exit(1)

html = html[:old.start()] + NEW_SIDEBAR + html[old.end():]

HTML.write_text(html, encoding="utf-8")
bars = len(re.findall(r'class="sb-bar"', html))
print(f"Done. {bars} density bars. {round(len(html)/1024,1)} KB")
