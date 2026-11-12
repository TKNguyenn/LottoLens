"""Frozen GUI, headless daily task and installer cleanup entry points."""
import argparse
import ctypes
from pathlib import Path
import sys


def main():
    root = Path(sys.executable).resolve().parent
    if sys.argv[1:2] == ["--uninstall-cleanup"]:
        from app.installation import prepare_uninstall
        if any(arg != "--purge-data" for arg in sys.argv[2:]):
            return 2
        prepare_uninstall(root, purge="--purge-data" in sys.argv[2:])
        return 0
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenMutexW.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_wchar_p]
    kernel.OpenMutexW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    maintenance = kernel.OpenMutexW(0x100000, False, "LottoLens.Maintenance")
    if maintenance:
        kernel.CloseHandle(maintenance)
        return 3
    if sys.argv[1:2] == ["--scheduled"]:
        from app.rules import RULES
        from app.scheduled_sync import run_scheduled
        parser = argparse.ArgumentParser()
        parser.add_argument("--game", required=True, choices=tuple(RULES))
        parser.add_argument("--db", required=True, type=Path)
        parser.add_argument("--preferences", required=True, type=Path)
        args = parser.parse_args(sys.argv[2:])
        return run_scheduled(args.game, args.db, args.preferences)
    if sys.argv[1:2] == ["--check-install"]:
        from app.package_check import check_install
        try:
            return check_install(Path(sys.argv[2]))
        except Exception as error:
            import json
            import traceback
            Path(sys.argv[2]).write_text(json.dumps({"error": type(error).__name__,
                "detail": str(error) if isinstance(error, ImportError) else "See frames",
                "frames": [{"file": Path(frame.filename).name, "line": frame.lineno}
                           for frame in traceback.extract_tb(error.__traceback__)]}), encoding="utf-8")
            return 1
    if len(sys.argv) != 1:
        return 2
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    if not kernel.CreateMutexW(None, False, "LottoLens.App"):
        raise OSError("Cannot create application mutex.")
    from app.ui import main as desktop_main
    return desktop_main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        if len(sys.argv) == 1:
            ctypes.windll.user32.MessageBoxW(None,
                "Không mở được LottoLens. Kiểm tra quyền ghi thư mục cài hoặc cài lại.\n"
                "LottoLens could not start. Check installation folder write permissions or reinstall.",
                "LottoLens", 0x10)
        raise SystemExit(1)
