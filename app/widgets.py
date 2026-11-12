"""Table and label helpers; styling lives in theme.py."""
from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import QItemSelectionModel, Qt
from .components import BallDelegate, TableItemDelegate, TextLabel
from .i18n import tr


def label(text, role=None, *, reserve_wrapped_height=True):
    item = TextLabel(text, reserve_wrapped_height=reserve_wrapped_height)
    item.setWordWrap(True)
    if role:
        item.setObjectName(role)
    return item


class ResultTable(QTableWidget):
    def focusInEvent(self, event):
        super().focusInEvent(event)
        if event.reason() in (Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason):
            selected = [index.row() for index in self.selectionModel().selectedRows() if not self.isRowHidden(index.row())]
            row = self.currentRow()
            if selected and row not in selected:
                row = selected[0]
            if row < 0 or self.isRowHidden(row):
                row = next((r for r in range(self.rowCount()) if not self.isRowHidden(r)), -1)
            if row < 0:
                return
            if not selected:
                self.selectRow(row)
            index = self.model().index(row, 0)
            self.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
            self.scrollTo(index)

    def updateGeometries(self):
        if getattr(self, "_fitting_rows", False):
            return
        self._fitting_rows = True
        try:
            super().updateGeometries()
            height = self.viewport().height()
            row = self.rowAt(height - 1)
            if row >= 0:
                top = self.rowViewportPosition(row)
                if top > 0 and top + self.rowHeight(row) > height:
                    # Reserve the trailing partial row instead of slicing balls against the footer.
                    margins = self.viewportMargins()
                    self.setViewportMargins(margins.left(), margins.top(), margins.right(), height - top)
        finally:
            self._fitting_rows = False

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self.updateGeometries()

    def resize_ball_rows(self):
        if not hasattr(self, "ball_column"):
            return
        for row in range(self.rowCount()):
            item = self.item(row, self.ball_column)
            if item:
                self.setRowHeight(row, BallDelegate.row_height(item.text(), self.columnWidth(self.ball_column)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_ball_rows()


def table(headers, rows, ball_column=None):
    widget = ResultTable(len(rows), len(headers))
    widget.setHorizontalHeaderLabels([tr(text) for text in headers])
    for column, text in enumerate(headers):
        widget.horizontalHeaderItem(column).setData(Qt.ItemDataRole.UserRole + 2, text)
    widget.verticalHeader().hide()
    widget.setAlternatingRowColors(False)
    widget.setShowGrid(False)
    widget.setWordWrap(True)
    widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    widget.setMinimumWidth(0)
    widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    widget.setItemDelegate(TableItemDelegate(widget))
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    widget.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    widget.horizontalHeader().setMinimumSectionSize(32)
    if ball_column is not None:
        widget.setItemDelegateForColumn(ball_column, BallDelegate(widget))
        widget.ball_column = ball_column
    for i, row in enumerate(rows):
        widget.setRowHeight(i, 52)
        for j, value in enumerate(row):
            widget.setItem(i, j, QTableWidgetItem(str(value)))
    return widget


