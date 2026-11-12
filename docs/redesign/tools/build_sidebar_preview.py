"""Extract the approved interactive mockup and add an isolated sidebar experiment."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = (root / "vietlott-redesign.html").read_text(encoding="utf-8")
style = "\n".join(re.findall(r"<style>(.*?)</style>", source, re.S)[:2])
app_start = source.index('<div class="app" id="appFrame">')
app_end = source.index('\n  <p style="font-size:11px;color:var(--fg-subtle);margin-top:10px">', app_start)
app = source[app_start:app_end]
script = re.search(r"<script>(.*?)</script>", source, re.S).group(1)
script = re.sub(r'document.getElementById\("iconGrid"\).innerHTML = \[.*?\.join\(""\);', '', script, flags=re.S)
script = script.replace('if(e.key==="t"||e.key==="T")', 'if(!e.target.closest("input,textarea,select,[contenteditable]") && (e.key==="t"||e.key==="T"))')

extra_css = """
/* Sidebar experiment: keep the approved pages and tokens intact. */
body { min-width:600px; }
.preview-head { display:flex; align-items:center; gap:12px; height:66px; padding:0 24px; }
.preview-head > img { width:28px; height:28px; border-radius:7px; }
.preview-head strong { font-size:13px; font-weight:650; }
.preview-head .note { color:var(--fg-subtle); font-size:11.5px; }
.preview-head .right { margin-left:auto; display:flex; align-items:center; gap:10px; }
.preview-head .btn { height:30px; font-size:11.5px; }
.app { margin:0 20px 18px; height:calc(100vh - 84px); min-height:590px;
  grid-template-rows:40px minmax(0,1fr); grid-template-columns:236px minmax(0,1fr);
  transition:grid-template-columns 220ms cubic-bezier(.2,.7,.2,1); }
.app.is-collapsed { grid-template-columns:68px minmax(0,1fr); }
.titlebar { height:40px; }
.main { min-height:0; }
.topline, .statusbar { flex-shrink:0; }
.canvas { overflow:auto; min-height:0; scrollbar-gutter:stable; }
.rail { display:flex; min-height:0; padding:18px 12px 14px; }
.brand { min-height:58px; overflow:hidden; }
.brand > img { width:30px; height:30px; flex:0 0 30px; border-radius:8px; }
.brand .bt { white-space:nowrap; }
.nav button { position:relative; white-space:nowrap; flex-shrink:0; height:38px; }
.nav button > span { transition:opacity 120ms ease; }
.nav button > span:not(.count) { overflow:hidden; }
.nav button:focus-visible, #sidebarToggle:focus-visible, .sw:focus-visible {
  outline:2px solid var(--red); outline-offset:3px; }
.nav button.on::before { left:-12px; }
.sidebar-toggle { width:32px; height:32px; flex:0 0 32px; padding:0; margin-right:2px;
  background:transparent; border-color:transparent; color:var(--fg-muted); box-shadow:none; }
.sidebar-toggle:hover { background:var(--bg-sunken); border-color:var(--border); color:var(--fg); }
.sidebar-toggle svg { width:18px; height:18px; }
.rail .foot { min-width:0; }
.themeswitch { flex-shrink:0; }
.sw { outline-offset:4px; }
.app.is-collapsed .brand { gap:0; padding-left:7px; padding-right:7px; }
.app.is-collapsed .brand .bt { display:none; }
.app.is-collapsed .nav button { justify-content:center; gap:0; padding:0; }
.app.is-collapsed .nav button svg { width:18px; height:18px; }
.app.is-collapsed .nav button > span { display:none; }
.app.is-collapsed .foot { padding:12px 0 0; }
.app.is-collapsed .foot p { display:none; }
.app.is-collapsed .themeswitch { padding:0; border-color:transparent; background:transparent;
  justify-content:center; height:30px; }
.app.is-collapsed .themeswitch > span { display:none; }
.nav-tooltip { position:fixed; z-index:100; display:none; pointer-events:none;
  padding:8px 11px; border-radius:8px; background:var(--bg-elevated); color:var(--fg);
  border:1px solid var(--border-strong); box-shadow:var(--sh-2); font-size:12px;
  white-space:nowrap; transform:translateY(-50%); }
.nav-tooltip.visible { display:block; }
.preview-label { color:var(--fg-subtle); font-size:10.5px; }
@media(max-width:950px) {
  .app { grid-template-columns:236px minmax(0,1fr); }
  .app.is-collapsed { grid-template-columns:68px minmax(0,1fr); }
  .rail { display:flex; }
  .preview-head .note { display:none; }
}
@media(prefers-reduced-motion:reduce) {
  *, *::before, *::after { transition:none !important; animation:none !important; scroll-behavior:auto !important; }
}
"""

controls = """
<header class="preview-head">
  <img src="assets/generated/07-ticket-gold.png" alt="">
  <strong>Vietlott Desktop</strong>
  <span class="note">Thử thu gọn sidebar bằng nút cạnh tên trò chơi</span>
  <div class="right">
    <span class="preview-label" id="railMode">Sidebar 236px</span>
    <button class="btn" id="themeBtn" type="button"><span id="themeLabel">Nền tối</span></button>
  </div>
</header>
"""

extra_js = """
const frame = document.getElementById('appFrame');
const rail = frame.querySelector('.rail');
rail.id = 'sidebar'; rail.setAttribute('aria-label', 'Điều hướng chính');
const logo = rail.querySelector('.brand > svg');
logo.outerHTML = '<img src="assets/generated/07-ticket-gold.png" alt="">';
const toggle = document.createElement('button');
toggle.id = 'sidebarToggle'; toggle.type = 'button'; toggle.className = 'btn sidebar-toggle';
toggle.setAttribute('aria-controls', 'sidebar');
frame.querySelector('.topline').prepend(toggle);
const tooltip = document.createElement('div');
tooltip.id = 'navTooltip'; tooltip.className = 'nav-tooltip'; tooltip.setAttribute('role', 'tooltip');
document.body.append(tooltip);

function hideNavTooltip() { tooltip.classList.remove('visible'); }
function setSidebarCollapsed(collapsed) {
  frame.classList.toggle('is-collapsed', collapsed);
  const label = collapsed ? 'Mở rộng thanh điều hướng' : 'Thu gọn thanh điều hướng';
  toggle.setAttribute('aria-expanded', String(!collapsed));
  toggle.setAttribute('aria-label', label); toggle.title = label;
  toggle.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    + '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9 4v16"/>'
    + (collapsed ? '<path d="m13 9 3 3-3 3"/>' : '<path d="m16 9-3 3 3 3"/>') + '</svg>';
  document.getElementById('railMode').textContent = collapsed ? 'Sidebar 68px · thêm 168px nội dung' : 'Sidebar 236px';
  hideNavTooltip();
}
toggle.addEventListener('click', () => setSidebarCollapsed(!frame.classList.contains('is-collapsed')));

function decorateNav() {
  document.querySelectorAll('#nav button').forEach(button => {
    const page = PAGES.find(page => page.id === button.dataset.page);
    button.setAttribute('aria-label', page.label);
    if(button.classList.contains('on')) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
}
function showNavTooltip(event) {
  const button = event.target.closest('#nav button');
  if(!button || !frame.classList.contains('is-collapsed')) return;
  const badge = button.querySelector('.count');
  tooltip.textContent = button.getAttribute('aria-label') + (badge ? ' · ' + badge.textContent + ' kỳ' : '');
  const rect = button.getBoundingClientRect();
  tooltip.style.left = (rect.right + 18) + 'px';
  tooltip.style.top = (rect.top + rect.height / 2) + 'px';
  tooltip.classList.add('visible');
  button.setAttribute('aria-describedby', 'navTooltip');
}
const nav = document.getElementById('nav');
nav.addEventListener('pointerover', showNavTooltip);
nav.addEventListener('focusin', showNavTooltip);
nav.addEventListener('pointerleave', hideNavTooltip);
nav.addEventListener('focusout', hideNavTooltip);
nav.addEventListener('click', hideNavTooltip);
new MutationObserver(decorateNav).observe(nav, {childList:true});
window.addEventListener('resize', hideNavTooltip);
document.addEventListener('keydown', event => { if(event.key === 'Escape') hideNavTooltip(); });
const themeSwitch = document.getElementById('sw');
themeSwitch.tabIndex = 0; themeSwitch.setAttribute('aria-label', 'Giao diện tối');
themeSwitch.addEventListener('keydown', event => {
  if(event.key === 'Enter' || event.key === ' ') { event.preventDefault(); themeSwitch.click(); }
});
decorateNav(); setSidebarCollapsed(false);
"""

output = '<!doctype html>\n<html lang="vi" data-theme="light">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>Vietlott — Thử sidebar thu gọn</title>\n<link rel="icon" href="assets/generated/07-ticket-gold.ico">\n<style>' + style + extra_css + '</style>\n</head>\n<body>\n' + controls + app + '\n<script>\n' + script + extra_js + '\n</script>\n</body>\n</html>\n'
target = root / 'vietlott-sidebar-toggle.html'
target.write_text(output, encoding='utf-8')
assert output.count('id="appFrame"') == 1
assert len(re.findall(r'function pg(?:Overview|History|Stats|Odds|Suggest|Verify|AI)\(', output)) == 7
assert 'id="iconGrid"' not in output
print(target)
