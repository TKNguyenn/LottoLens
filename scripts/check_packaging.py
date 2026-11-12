"""Offline packaging boundaries; only temporary directories and mocked tasks."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import paths, scheduling, installation


def main():
    with tempfile.TemporaryDirectory(prefix="LottoLens build check ") as directory:
        root = Path(directory)
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(root / "LottoLens.exe")):
            assert paths.installed_data() == root / "data"
            xml = ET.fromstring(scheduling._task_xml("mega", {"time": "20:00"}, root/"data/history.sqlite3", root/"data/ui_preferences.json", "S-1-5-21-123"))
            ns = {"t": scheduling._NS}
            assert xml.find(".//t:Command", ns).text == str(root/"LottoLens.exe")
            assert xml.find(".//t:Arguments", ns).text.startswith('--scheduled --game mega ')
            assert xml.find(".//t:WorkingDirectory", ns).text == str(root)
        assert paths.installed_data() is None

        data = root/"data"; data.mkdir()
        (data/"history.sqlite3").write_bytes(b"keep history")
        (root/"unrelated.txt").write_text("keep", encoding="utf-8")
        calls = []
        present = {scheduling._task_name(data/"ui_preferences.json", game) for game in ("mega", "bingo18")}
        def run(args):
            calls.append(args)
            if "/TN" not in args:
                return subprocess.CompletedProcess(args, 0, '\n'.join('"\\'+name+'","ready"' for name in present), "")
            task = args[args.index("/TN")+1]
            if "/Delete" in args: present.discard(task)
            return subprocess.CompletedProcess(args, 0 if task in present or "/Delete" in args else 1, "", "")
        with patch.object(scheduling, "_run", side_effect=run):
            installation.prepare_uninstall(root, purge=False)
        assert not present and (data/"history.sqlite3").exists()
        assert all(args[args.index('/TN')+1].startswith(scheduling._task_name(data/'ui_preferences.json', 'mega').rsplit('-',1)[0]+'-') for args in calls if '/TN' in args)
        with patch.object(scheduling, "_run", return_value=subprocess.CompletedProcess([], 1, "", "")):
            try: installation.prepare_uninstall(root, purge=True)
            except RuntimeError: pass
            else: raise AssertionError("Failed task deletion must abort uninstall")
        assert (data/"history.sqlite3").exists()
        present.add("OtherAppDaily")
        with patch.object(scheduling, "_run", side_effect=run):
            installation.prepare_uninstall(root, purge=True)
        assert present == {"OtherAppDaily"}
        assert not data.exists() and (root/"unrelated.txt").read_text() == "keep"

        outside = root/"outside"; outside.mkdir(); (outside/"private").write_text("keep")
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(data), str(outside)], check=True, capture_output=True)
            with patch.object(scheduling, "_run", side_effect=run):
                try: installation.prepare_uninstall(root, purge=True)
                except ValueError: pass
                else: raise AssertionError("Do not purge a data junction")
            assert (outside/"private").read_text() == "keep"
            data.rmdir()
        data.mkdir(); (data/"nested").mkdir()
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", str(data/"nested/link"), str(outside)], check=True, capture_output=True)
        with patch.object(scheduling, "_run", side_effect=run):
            installation.prepare_uninstall(root, purge=True)
        assert (outside/"private").read_text() == "keep"
    print("Packaging boundaries passed: paths, scheduler, keep/purge, failures, unrelated files and junctions.")


if __name__ == "__main__":
    main()
