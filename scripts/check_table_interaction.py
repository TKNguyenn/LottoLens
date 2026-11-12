"""Table focus/row clipping regression on temporary data; no network/AI."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QStyle,QStyleOptionViewItem
from PySide6.QtGui import QFontDatabase
from app.ui import Desktop
from check_max_bingo_generation import history
from check_redesign import check_page


def settle():
    for _ in range(4):QApplication.processEvents()


def full_last_row(table):
    viewport=table.viewport().rect()
    row=table.rowAt(viewport.bottom())
    if row>=0 and table.rowHeight(row)<=viewport.height():
        rect=table.visualRect(table.model().index(row,0))
        assert rect.bottom()<=viewport.bottom(),("partial last row",row,rect.getRect(),viewport.getRect())


def main():
    app=QApplication.instance() or QApplication([])
    if not QFontDatabase.families():
        for name in ("SegUIVar.ttf","segoeui.ttf","seguisb.ttf","segoeuib.ttf","CascadiaMono.ttf"):
            QFontDatabase.addApplicationFont("C:/Windows/Fonts/"+name)
    out=Path(__file__).resolve().parents[1]/"docs/redesign/reviews/table-interaction"
    capture="--capture" in sys.argv
    if capture:out.mkdir(exist_ok=True,parents=True)
    with tempfile.TemporaryDirectory() as directory,patch("app.ai._send") as send,patch("app.ui.OfficialSource.fetch_history") as fetch:
        folder=Path(directory);w=Desktop(folder/"history.db",folder/"config.json")
        try:
            w.game.setCurrentIndex(w.game.findData("bingo18"))
            w.store.add_draws(w.rule,history(w.rule,200));w.refresh()
            w.method.setCurrentIndex(w.method.findData("uniform_v1"));w.make_suggestions()
            for theme in ("light","dark"):
                w.set_theme(theme)
                for size in ((1440,960),(1000,700)):
                    w.resize(*size);w.show();settle()
                    for page,name,table in ((1,"history",w.history_table),(2,"stats",w.stats_table),(3,"odds",w.odds_table),(4,"suggestions",w.suggestion_table)):
                        w.nav.setCurrentRow(page);settle()
                        # The final row that fits the viewport must not be sliced by the footer.
                        full_last_row(table)
                        table.clearSelection();table.setCurrentCell(-1,-1);table.clearFocus()
                        table.setFocus(Qt.FocusReason.TabFocusReason);settle()
                        assert table.selectionModel().selectedRows(),"Tab focus must have a visible selected row"
                        index=table.model().index(min(2,table.rowCount()-1),0)
                        table.scrollTo(index);settle()
                        table.clearFocus();settle();geometry=table.viewport().geometry()
                        QTest.mouseClick(table.viewport(),Qt.MouseButton.LeftButton,pos=table.visualRect(index).center());settle()
                        assert table.hasFocus() and table.selectionModel().selectedRows()
                        assert table.viewport().geometry()==geometry,"Click focus changes the table frame"
                        for column in range(table.columnCount()):
                            cell=table.model().index(index.row(),column)
                            option=QStyleOptionViewItem();option.initFrom(table)
                            option.state|=QStyle.StateFlag.State_HasFocus|QStyle.StateFlag.State_Selected
                            table.itemDelegateForIndex(cell).initStyleOption(option,cell)
                            assert not option.state&QStyle.StateFlag.State_HasFocus,(name,column,"native cell focus")
                            assert option.state&QStyle.StateFlag.State_Selected
                        previous=table.currentRow();QTest.keyClick(table,Qt.Key.Key_Down);settle()
                        if previous+1<table.rowCount():assert table.currentRow()==previous+1
                        full_last_row(table);check_page(w)
                        if capture and size==(1440,960):w.grab().save(str(out/f"{name}-{theme}-selected.png"))
                        if page==1:
                            for value in (0,11,table.verticalScrollBar().maximum()):
                                table.verticalScrollBar().setValue(value);settle();full_last_row(table)
                            last=table.visualRect(table.model().index(table.rowCount()-1,0))
                            assert table.viewport().rect().contains(last),"The final record must remain reachable"
                            if capture:w.grab().save(str(out/f"history-{theme}-{size[0]}-bottom.png"))
            w.nav.setCurrentRow(1)
            for clear in (True,False):
                w.history_table.setCurrentCell(80,0);w.history_table.selectRow(80)
                w.history_table.verticalScrollBar().setValue(0)
                if clear:w.history_table.clearSelection()
                w.history_search.setFocus();settle()
                w.history_table.setFocus(Qt.FocusReason.TabFocusReason);settle()
                rect=w.history_table.visualRect(w.history_table.model().index(80,0))
                assert w.history_table.viewport().rect().contains(rect),"Tab focus row must be on screen"
            w.history_table.selectRow(199)
            w.history_search.setText("200");w.history_search.setFocus();settle()
            w.history_table.setFocus(Qt.FocusReason.TabFocusReason);settle()
            assert any(not w.history_table.isRowHidden(i.row()) for i in w.history_table.selectionModel().selectedRows()),"Tab should select a visible filtered row"
            w.history_search.clear();settle()
            # Grouped Max rows have a different height; resizing/scrolling must still work.
            w.game.setCurrentIndex(w.game.findData("max3dpro"));w.store.add_draws(w.rule,history(w.rule,20));w.refresh()
            w.nav.setCurrentRow(1);settle()
            for value in (0,3,w.history_table.verticalScrollBar().maximum()):
                w.history_table.verticalScrollBar().setValue(value);settle();full_last_row(w.history_table)
            send.assert_not_called();fetch.assert_not_called()
        finally:w.close()
    print("Tables OK: no frame/cell focus border, row selection/keyboard intact, full bottom rows, all tables/themes/sizes/grouped results; offline")


if __name__=="__main__":main()
