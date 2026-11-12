from base64 import b64encode
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path
from random import Random
import sys
from tempfile import TemporaryDirectory

from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QPushButton, QWidget

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.domain import Draw
from app.rules import BASE, get_rule
from app.ui import Desktop

app = QApplication([])
images = {}


def export(image, marks=()):
    buffer = BytesIO()
    image.save(buffer, format='WEBP', lossless=True, method=4)
    return [b64encode(buffer.getvalue()).decode(), image.width, image.height, list(marks)]


with TemporaryDirectory() as temp:
    directory = Path(temp)
    w = Desktop(directory / 'history.db', directory / 'config.json')
    try:
        rule = get_rule('mega')
        rng = Random(420)
        draws = []
        for i in range(100):
            at = (datetime(2026, 11, 10, 11, tzinfo=timezone.utc) - timedelta(days=2*(99-i))).isoformat()
            draws.append(Draw('mega', rule.mode_id, rule.rule_version, f'{1487+i:05}',
                              at, {'main': sorted(rng.sample(range(1,46), 6))},
                              BASE+rule.result_path, at, 'a'*64))
        w.store.add_draws(rule, draws)
        w.refresh()
        w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        w.resize(1140, 780)
        w.show()
        w.resize(1140, 780)

        def settle():
            for _ in range(4):
                app.processEvents()

        def widget_rect(widget):
            point = widget.mapTo(w, QPoint(0, 0))
            return point.x(), point.y(), widget.width(), widget.height()

        def button(source):
            return next(b for b in w.pages.currentWidget().findChildren(QPushButton)
                        if b.property('i18n_setText') == source and b.isVisible())

        def screenshot():
            pixmap = w.grab()
            raw = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBX8888)
            assert pixmap.devicePixelRatio() == 3.0
            assert raw.width() == 3*w.width() and raw.height() == 3*w.height(), (raw.size(), w.size())
            return Image.frombytes('RGB', (raw.width(), raw.height()), bytes(raw.bits()), 'raw', 'RGBX')

        def crop(rect, targets):
            left, top, right, bottom = rect
            marks = []
            for target in targets:
                x, y, width, height = widget_rect(target) if isinstance(target, QWidget) else target
                x1, y1 = max(x, left), max(y, top)
                x2, y2 = min(x+width, right), min(y+height, bottom)
                assert x2 > x1 and y2 > y1, (target, rect)
                marks.append([3*(x1-left), 3*(y1-top), 3*(x2-x1), 3*(y2-y1)])
            return screenshot().crop(tuple(3*value for value in rect)), marks

        w.method.setCurrentIndex(w.method.findData('uniform_v1'))
        w.make_suggestions()
        for lang in ('vi', 'en'):
            w.apply_language(lang)
            for theme in ('dark', 'light'):
                w.set_theme(theme)
                prefix = f'{lang}-{theme}'
                for page, name in enumerate(('overview','history','stats','odds','suggest','verify','ai','auto')):
                    w.resize(1140, 780)
                    w.nav.setCurrentRow(page)
                    scroll = w.pages.currentWidget().verticalScrollBar()
                    scroll.setValue(0)
                    settle()
                    x, right = w.sidebar.width()+12, w.width()-17
                    if page == 0:
                        targets = [w.game, button('Cập nhật lịch sử')]
                        image, marks = crop((x, 6, right, 256), targets)
                        home, _ = crop((w.sidebar.width(), 56, w.width(), w.height()-34), [])
                        images[prefix+'-home'] = export(home)
                    elif page == 1:
                        tx,ty,tw,th = widget_rect(w.history_table)
                        image, marks = crop((x,68,right,ty+153), [w.history_search, (tx+3,ty+42,tw-10,48)])
                    elif page == 2:
                        hx,hy,hw,hh = widget_rect(w.heatmap)
                        image, marks = crop((x,68,right,min(hy+hh+14,492)), [w.stats_segments, (hx,hy,hw,min(hh,140))])
                    elif page == 3:
                        tx,ty,tw,th = widget_rect(w.odds_table)
                        image, marks = crop((x,68,right,ty+230), [(tx+2,ty+44,tw-9,142)])
                    elif page == 4:
                        bx,by,bw,bh = widget_rect(button('Tạo bộ số tham khảo'))
                        image, marks = crop((x,68,right,min(max(by+bh+16,392),740)), [w.method, button('Tạo bộ số tham khảo')])
                    elif page == 5:
                        sx,sy,sw,sh = widget_rect(w.verify_setup)
                        image, marks = crop((x,68,right,min(sy+sh+12,740)), [w.verify_method, button('Chạy kiểm chứng')])
                    elif page == 6:
                        w.resize(1140, 1100)
                        settle()
                        tx,ty,tw,th = widget_rect(button('Test model'))
                        bx,by,bw,bh = widget_rect(w.base)
                        kx,ky,kw,kh = widget_rect(w.key)
                        image, marks = crop((bx-20,by-30,bx+bw+18,ty+th+15),
                                            [w.key,w.fetch_models_button,w.model,button('Test model')])
                    else:
                        w.resize(1140, 780)
                        settle()
                        switch, clock = w.auto_update_inputs['mega'], w.auto_time_inputs['mega']
                        switch.setChecked(True)
                        settle()
                        sx,sy,sw,sh = widget_rect(switch)
                        cx,cy,cw,ch = widget_rect(clock)
                        top, top_marks = crop((sx-18, sy-54, cx+cw+18, max(sy+sh,cy+ch)+9), [switch, clock])
                        scroll.setValue(scroll.maximum())
                        settle()
                        px,py,pw,ph = widget_rect(w.preferences_save_button)
                        bottom, bottom_marks = crop((px-82,py-12,px+pw+15,py+ph+12), [w.preferences_save_button])
                        image = Image.new('RGB', (top.width, top.height+bottom.height+30), w.tokens['page'])
                        image.paste(top,(0,0))
                        ox,oy = image.width-bottom.width,top.height+30
                        image.paste(bottom,(ox,oy))
                        marks = top_marks + [[a+ox,b+oy,c,d] for a,b,c,d in bottom_marks]
                        switch.setChecked(False)
                    images[prefix+'-'+name] = export(image, marks)
        assert len(images) == 36
        import re
        path = Path(__file__).with_name('lottolens-onboarding.html')
        source = path.read_text(encoding='utf-8')
        updated, count = re.subn(r'(<script id="captures" type="application/json">).*?(</script>)',
                                lambda m: m[1]+json.dumps(images,separators=(',',':'))+m[2], source, flags=re.S)
        assert count == 1
        path.write_text(updated,encoding='utf-8')
        print(len(images), 'lossless screenshots at 3x;', path.stat().st_size, 'bytes', flush=True)
    finally:
        w.close()
