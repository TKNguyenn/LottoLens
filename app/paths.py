"""Installed copies keep user files beside the EXE; source runs retain their paths."""
from pathlib import Path
import sys


def installed_data():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "data"
    return None
