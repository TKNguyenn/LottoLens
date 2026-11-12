"""Build an isolated gradient study from the approved seven-page sidebar mockup."""
from pathlib import Path
import re

folder = Path(__file__).resolve().parent
source = (folder.parent / "vietlott-sidebar-toggle.html").read_text(encoding="utf-8")
source = source.replace('data-theme="light"', 'data-theme="dark" data-finish="gradient"', 1)
source = source.replace("Vietlott Desktop", "LottoLens")
source = source.replace("số lệch trên 2 độ lệch chuẩn", "số cao hơn trung bình ≥ 2 lần")
source = re.sub(r"<title>.*?</title>", "<title>LottoLens — Gradient study</title>", source, count=1)
source = source.replace('src="assets/', 'src="../assets/').replace('href="assets/', 'href="../assets/')
source = source.replace("frame.querySelector('.topline').prepend(toggle);", "rail.querySelector('.brand').append(toggle);")
source = source.replace("+ (collapsed ? '<path d=\"m13 9 3 3-3 3\"/>' : '<path d=\"m16 9-3 3 3 3\"/>')", "")

css = """
/* Gradient study. Keep the approved content, interactions and red identity. */
:root {
  --sans:"Segoe UI Variable Text","Segoe UI",Arial,sans-serif;
  --fg-subtle:#6F6D7A;
  --study-hero:linear-gradient(125deg,#FFF7F7 0%,#FFFFFF 45%,#F5F2F6 100%);
  --study-card:linear-gradient(145deg,#FFFFFF 5%,#FFFFFF 48%,#F5F4F8 100%);
  --study-edge:linear-gradient(145deg,#FFFFFF 0%,#E4DCE3 40%,#DFDFE8 100%);
  --study-glow:rgba(205,35,64,.09);
  --study-cta:linear-gradient(120deg,#D9324C 0%,#C71D38 55%,#A5122E 100%);
  --study-active:linear-gradient(100deg,#F8DFE5 0%,#FBEDEF 70%,#FFF6F7 100%);
  --study-shadow:0 5px 18px -12px rgba(44,21,37,.22),inset 0 1px 0 rgba(255,255,255,.95);
}
[data-theme="dark"] {
  --fg-subtle:#9A96A7; --fg-muted:#B3AFBE;
  --study-hero:linear-gradient(128deg,#2A1924 0%,#19151E 40%,#12131B 100%);
  --study-card:linear-gradient(140deg,#1B1A24 0%,#14141C 48%,#101117 100%);
  --study-edge:linear-gradient(140deg,#4B3544 0%,#34303F 37%,#24252E 100%);
  --study-glow:rgba(231,52,87,.13);
  --study-cta:linear-gradient(115deg,#FF7385 0%,#FF4D67 50%,#F23554 100%);
  --study-active:linear-gradient(100deg,#481E2B 0%,#2A1721 70%,#1F151D 100%);
  --study-shadow:0 7px 24px -14px rgba(0,0,0,.65),inset 0 1px 0 rgba(255,255,255,.035);
}
body { min-width:600px; }
.preview-head { height:72px; padding:0 26px; gap:11px; }
.preview-head > img { width:30px; height:30px; }
.preview-head strong { font-size:14px; letter-spacing:-.02em; }
.preview-head .note { font-size:11px; }
.preview-head .right { gap:12px; }
.study-tabs { display:flex; align-items:center; padding:3px; gap:2px; border:1px solid var(--border);
  border-radius:10px; background:var(--bg-sunken); }
.study-tabs button { border:0; border-radius:7px; padding:6px 12px; font:inherit; font-size:11px;
  font-weight:550; color:var(--fg-muted); background:transparent; cursor:pointer; }
.study-tabs button[aria-pressed="true"] { background:var(--bg-elevated); color:var(--fg); box-shadow:var(--sh-1); }
.study-tabs button:focus-visible { outline:2px solid var(--red); outline-offset:2px; }
.app { height:calc(100vh - 92px); margin-bottom:20px; }
.pagehead h1 { font-size:23px; font-weight:650; letter-spacing:-.035em; }
.pagehead p { font-size:12px; }
.pagehead { margin-bottom:2px; }
.preview-head .btn { gap:7px; }
#railMode { display:none; }
.study-swatch { display:inline-block; width:12px; height:12px; border-radius:50%;
  background:var(--study-cta); box-shadow:inset 0 0 0 1px rgba(255,255,255,.15); }
.study-meta { font-size:10px; color:var(--fg-subtle); }
.brand { gap:8px; height:50px; min-height:50px; }
.brand .bt { flex:1; }
.brand .sidebar-toggle { margin:0; }
.app.is-collapsed .brand { justify-content:center; padding-left:0; padding-right:0; }
.app.is-collapsed .brand > img { display:none; }

[data-finish="gradient"] body {
  background:radial-gradient(ellipse at 10% 0%,var(--study-glow),transparent 40%),var(--page);
}
[data-finish="gradient"] .app {
  border-color:transparent;
  background:linear-gradient(var(--bg),var(--bg)) padding-box,var(--study-edge) border-box;
  box-shadow:0 18px 58px -30px rgba(30,10,28,.30),0 1px 3px rgba(30,10,28,.06);
}
[data-theme="dark"][data-finish="gradient"] .app {
  box-shadow:0 22px 64px -28px rgba(0,0,0,.8),0 0 0 1px rgba(255,255,255,.025);
}
[data-finish="gradient"] .main {
  background:radial-gradient(ellipse at 80% -10%,var(--study-glow),transparent 53%),
    linear-gradient(160deg,var(--bg-sunken),var(--page));
}
[data-finish="gradient"] .titlebar {
  background:linear-gradient(100deg,var(--bg-sunken),var(--bg-elevated));
}
[data-finish="gradient"] .rail {
  background:linear-gradient(175deg,var(--bg) 0%,var(--bg) 65%,var(--red-soft) 170%);
}
[data-finish="gradient"] .topline {
  background:linear-gradient(105deg,var(--bg) 30%,var(--bg-elevated) 100%);
}
[data-finish="gradient"] .card {
  background:var(--study-card) padding-box,var(--study-edge) border-box;
  border:1px solid transparent; box-shadow:var(--study-shadow); border-radius:14px;
}
[data-finish="gradient"] .card.result-hero {
  background:var(--study-hero) padding-box,var(--study-edge) border-box;
}
[data-finish="gradient"] .result-hero .card-h .ico {
  background:linear-gradient(135deg,var(--red-soft),var(--gold-soft)); color:var(--red-ink);
}
[data-finish="gradient"] .nav button.on {
  background:var(--study-active); box-shadow:inset 0 1px 0 rgba(255,255,255,.08);
}
[data-finish="gradient"] .nav button.on::before {
  background:linear-gradient(180deg,var(--red-bright),var(--red));
}
[data-finish="gradient"] .btn-primary {
  background:var(--study-cta); border-color:transparent;
  box-shadow:0 7px 16px -9px rgba(200,30,51,.62),inset 0 1px 0 rgba(255,255,255,.18);
  color:#FFFFFF;
}
[data-theme="dark"][data-finish="gradient"] .btn-primary { color:#18050B; }
[data-finish="gradient"] .btn-primary:hover { filter:brightness(.95); border-color:transparent; }
[data-theme="dark"][data-finish="gradient"] .btn-primary:hover { filter:brightness(1.04); }
[data-finish="gradient"] .card-h .ico {
  background:linear-gradient(135deg,var(--red-soft),var(--bg-elevated));
}
[data-finish="gradient"] .meter i,
[data-finish="gradient"] .statusbar .bar i { background:var(--study-cta); }
[data-finish="gradient"] .meter i.dim { background:var(--border-strong); }
[data-finish="gradient"] .ball {
  background:linear-gradient(150deg,#FFFFFF 12%,#F5F2F6 55%,#E9E6EE 100%);
  border-color:#E4DEE7;
  box-shadow:inset 0 1px 0 #FFFFFF,0 3px 7px -4px rgba(35,16,29,.2);
}
[data-theme="dark"][data-finish="gradient"] .ball {
  background:linear-gradient(145deg,#35313E 0%,#24232D 47%,#16171F 100%);
  border-color:#45404F;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.09),0 3px 8px -3px rgba(0,0,0,.6);
}
[data-finish="gradient"] .ball--hit {
  background:linear-gradient(135deg,#DB3851,#C01A36 65%,#A8122D); border-color:transparent; color:white;
}
[data-theme="dark"][data-finish="gradient"] .ball--hit {
  background:linear-gradient(135deg,#FF7C8D,#FF4D67 60%,#F23554); border-color:transparent; color:#18050B;
}
[data-finish="gradient"] .ball--gold {
  background:linear-gradient(140deg,#FBE8BF,#EEC77C 52%,#D39B3F); color:#3A2705; border-color:transparent;
}
[data-finish="gradient"] .badge.red {
  background:linear-gradient(125deg,var(--red-soft),var(--bg-elevated));
  border-color:var(--red-soft);
}
[data-finish="gradient"] .tblwrap {
  background:var(--study-card) padding-box,var(--study-edge) border-box; border-color:transparent;
  box-shadow:var(--study-shadow);
}
[data-finish="gradient"] .tbl th,
[data-finish="gradient"] .tblfoot {
  background:linear-gradient(110deg,var(--bg-sunken),var(--bg-elevated));
}
[data-finish="gradient"] .callout.info {
  background:linear-gradient(115deg,var(--bg-sunken),var(--bg-elevated));
}
[data-finish="gradient"] .seg { background:linear-gradient(145deg,var(--bg-sunken),var(--page)); }
[data-finish="gradient"] .chip.on { background:var(--study-cta); border-color:transparent; }
[data-theme="dark"][data-finish="gradient"] .chip.on { color:#18050B; }
[data-finish="gradient"] .answer {
  background:linear-gradient(150deg,var(--bg-sunken),var(--bg));
}
[data-finish="gradient"] .hist .b {
  background:linear-gradient(0deg,var(--red),var(--red-bright)); opacity:.7;
}
[data-finish="gradient"] .heat .cell {
  background-image:linear-gradient(150deg,rgba(255,255,255,.055),transparent 75%);
}
[data-theme="dark"][data-finish="gradient"] .heat .cell.h0 { color:var(--fg-subtle); }
[data-theme="light"][data-finish="gradient"] .heat .cell.h4,
[data-theme="light"][data-finish="gradient"] .heat .cell.h5 { color:#18050B; }
[data-finish="gradient"] .stat .val { letter-spacing:-.04em; }
[data-finish="gradient"] .result-hero hr { border-color:var(--border); opacity:.75; }
[data-finish="gradient"] .statusbar { background:linear-gradient(100deg,var(--bg),var(--bg-elevated)); }
@media(max-width:1100px) { .study-meta { display:none; } .preview-head { padding:0 22px; } }
@media(max-width:760px) { .preview-head .note { display:none; } .preview-head .right { gap:6px; } .study-tabs button { padding:6px 8px; } }
@media(prefers-reduced-motion:reduce) { *,*::before,*::after { animation:none !important; transition:none !important; } }
"""

toolbar = """
<header class="preview-head">
  <img src="../assets/generated/07-ticket-gold.png" alt="">
  <strong>LottoLens</strong><span class="note">Bản thử gradient</span>
  <div class="right">
    <span class="study-meta">Dữ liệu xem thử</span><span id="railMode" hidden></span>
    <div class="study-tabs" role="group" aria-label="So sánh kiểu nền">
      <button type="button" id="flatBtn" aria-pressed="false">Phẳng</button>
      <button type="button" id="gradientBtn" aria-pressed="true"><span class="study-swatch" aria-hidden="true"></span> Gradient</button>
    </div>
    <button class="btn" id="themeBtn" type="button"><span id="themeLabel">Nền sáng</span></button>
  </div>
</header>
"""
source = re.sub(r'<header class="preview-head">.*?</header>', toolbar, source, count=1, flags=re.S)
source = source.replace('</style>', css + '\n</style>', 1)
source = source.replace('document.getElementById("page").innerHTML = (R[S.page]||pgOverview)();', 'document.getElementById("page").innerHTML = (R[S.page]||pgOverview)();\n  if(S.page === "overview") document.querySelector("#page .bento > .card")?.classList.add("result-hero");')
runtime = """
function setFinish(finish) {
  document.documentElement.dataset.finish = finish;
  document.getElementById('flatBtn').setAttribute('aria-pressed', String(finish === 'flat'));
  document.getElementById('gradientBtn').setAttribute('aria-pressed', String(finish === 'gradient'));
}
document.getElementById('flatBtn').onclick = () => setFinish('flat');
document.getElementById('gradientBtn').onclick = () => setFinish('gradient');
setTheme('dark');
"""
source = source.replace('</script>', runtime + '\n</script>', 1)
target = folder / 'lottolens-gradient.html'
target.write_text(source, encoding='utf-8')
assert source.count('id="appFrame"') == 1
assert all('function pg' + name + '(' in source for name in ('Overview', 'History', 'Stats', 'Odds', 'Suggest', 'Verify', 'AI'))
assert 'Vietlott Desktop' not in source
assert '.hist{display:flex' in source and '.h6{' in source, 'Missing histogram or heat scale styles'
print(target)
