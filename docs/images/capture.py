"""Refresh public README screenshots with synthetic data and networking blocked."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import Random
import socket
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.domain import Draw
from app.rules import get_rule
from app.ui import Desktop


def main():
    def offline(*args, **kwargs):
        raise AssertionError('README capture must not access the network')
    socket.create_connection = offline
    socket.socket.connect = offline
    application = QApplication([])
    output = Path(__file__).resolve().parent
    with TemporaryDirectory() as directory:
        root = Path(directory)
        window = Desktop(root/'history.sqlite3', root/'config.json')
        try:
            rng = Random(420)
            rule = get_rule('mega')
            end = datetime(2026, 11, 10, 11, tzinfo=timezone.utc)
            records = []
            for index in range(100):
                at = (end-timedelta(days=2*(99-index))).isoformat()
                records.append(Draw('mega', rule.mode_id, rule.rule_version, f'{1487+index:05}', at,
                    {'main':sorted(rng.sample(range(1,46),6))}, 'https://example.invalid/illustration', at, 'a'*64))
            window.store.add_draws(rule, records)
            window.refresh()
            window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            window.resize(1440, 960)
            window.show()
            shots = [('overview-dark',0,'dark'), ('overview-light',0,'light'),
                     ('history-light',1,'light'), ('stats-dark',2,'dark'),
                     ('ai-dark',6,'dark'), ('settings-light',7,'light')]
            for language in ('vi','en'):
                window.language_choice.setCurrentIndex(window.language_choice.findData(language))
                window.apply_language(language)
                for name, page, theme in shots:
                    window.set_theme(theme)
                    QTest.qWait(window.theme_button.animation.duration() + 50)
                    window.nav.setCurrentRow(page)
                    window.pages.currentWidget().verticalScrollBar().setValue(0)
                    window.notice.setText('Ảnh minh họa — dữ liệu mẫu, không phải kết quả chính thức.' if language=='vi'
                        else 'Illustration — sample data, not official draw results.')
                    for _ in range(4): application.processEvents()
                    assert not window.key.text() and window.worker is None
                    image = window.grab()
                    assert image.width() >= 1440 and image.height() >= 960
                    assert image.save(str(output/f'{language}-{name}.png'))
            assert not (root/'config.json').exists()
            print('Captured 12 README screenshots: synthetic data, empty API key, networking blocked.')
        finally:
            window.close()


if __name__ == '__main__':
    main()
