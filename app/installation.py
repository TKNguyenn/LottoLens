"""Uninstall only this profile's daily tasks and, on request, its data child."""
import csv
import io
from pathlib import Path
import shutil
import stat

from . import scheduling
from .rules import RULES


def prepare_uninstall(root, *, purge=False):
    root = Path(root).resolve()
    data = root / "data"
    # Refuse a redirected data root; rmtree itself does not traverse nested Windows junctions.
    if data.exists() and (data.is_symlink() or data.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise ValueError("Refusing a redirected data directory.")

    def task_names():
        result = scheduling._run(["schtasks", "/Query", "/FO", "CSV", "/NH"])
        if result.returncode:
            raise RuntimeError("Cannot inspect Windows daily schedules.")
        return {row[0].lstrip("\\") for row in csv.reader(io.StringIO(result.stdout)) if row}

    owned = {scheduling._task_name(data / "ui_preferences.json", game) for game in RULES}
    for name in sorted(task_names() & owned):
        scheduling._run(["schtasks", "/End", "/TN", name])
        result = scheduling._run(["schtasks", "/Delete", "/TN", name, "/F"])
        if result.returncode:
            raise RuntimeError("Cannot remove a Windows daily schedule; app and data were kept.")
    if task_names() & owned:
        raise RuntimeError("A Windows daily schedule remains; app and data were kept.")
    if purge and data.exists():
        shutil.rmtree(data)
