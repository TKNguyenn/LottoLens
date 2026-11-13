"""Real disposable Windows install/keep/reinstall/purge test; no provider requests."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import __version__, scheduling
from app.preferences import default_preferences, save_preferences
from app.rules import get_rule
from app.storage import Store
from check_analysis_core import history


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', type=Path, default=ROOT/'dist'/f'LottoLens-Setup-{__version__}.exe')
    args = parser.parse_args()
    setup = args.setup.resolve(strict=True)
    base = ROOT/'build'; base.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='installer-smoke-', dir=base)).resolve()
    assert work.is_relative_to(base.resolve())
    folder = work/'LottoLens Ứng dụng'; data = folder/'data'
    exe = folder/'LottoLens.exe'
    flags = ['/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART']

    def install():
        subprocess.run([str(setup), *flags, '/LANG=english', '/DIR='+str(folder), '/LOG='+str(work/'setup.log')], check=True, timeout=120)
        assert exe.is_file() and list(folder.glob('unins*.exe'))

    def uninstall(*extra):
        uninstaller = max(folder.glob('unins*.exe'), key=lambda path: path.stat().st_mtime)
        subprocess.run([str(uninstaller), *flags, *extra], check=True, timeout=120)

    def diagnose(name):
        report = work/name
        subprocess.run([str(exe), '--check-install', str(report)], check=True, timeout=60)
        result = json.loads(report.read_text(encoding='utf-8'))
        assert result['pages'] == 8 and result['version'] == __version__
        assert Path(result['data_directory']) == data
        assert Path(result['config_path']) == data/'config.json'
        return result

    install()
    assert not data.exists(), 'Never ship user data in setup'
    diagnostic = diagnose('first-install.json')
    with closing(Store(data/'history.sqlite3')) as store:
        store.add_draws(get_rule('mega'), history(3))
    config = data/'config.json'
    config.write_text(json.dumps({'base_url':'https://api.openai.com/v1', 'model':'gpt-6.1-sol', 'api_key':'synthetic-test-key'}), encoding='utf-8')
    prefs_path = data/'ui_preferences.json'
    prefs = default_preferences(); save_preferences(prefs_path, prefs)
    (data/'policy-acceptance.txt').write_text('synthetic receipt')
    (folder/'unrelated.txt').write_text('User-owned file must survive both modes')
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in data.iterdir() if p.is_file()}
    enabled = default_preferences(); enabled['auto_updates']['mega'] = {'enabled':True, 'time':'23:59'}
    task_name = scheduling._task_name(prefs_path, 'mega')
    try:
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', str(exe)):
            scheduling.configure_schedules(enabled, data/'history.sqlite3', prefs_path, prefs)
        query = scheduling._run(['schtasks','/Query','/TN',task_name,'/XML'])
        assert query.returncode == 0 and '--scheduled' in query.stdout
        # On-disk opt-in stays false: the real headless command exits without network or DB writes.
        subprocess.run([str(exe), '--scheduled', '--game','mega','--db',str(data/'history.sqlite3'), '--preferences',str(prefs_path)], check=True, timeout=30)
        uninstall('/LOG='+str(work/'keep.log'))
        assert not exe.exists() and not (folder/'_internal').exists()
        assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in data.iterdir() if p.is_file()} == before
        assert scheduling._run(['schtasks','/Query','/TN',task_name,'/XML']).returncode != 0
        assert (folder/'unrelated.txt').is_file()
        install()
        assert config.read_text(encoding='utf-8').find('synthetic-test-key') > 0
        diagnose('reinstall.json')
        with closing(Store(data/'history.sqlite3')) as store:
            assert len(store.list_draws(get_rule('mega'))) == 3
        uninstall('/PURGEDATA=1', '/LOG='+str(work/'purge.log'))
        assert not exe.exists() and not data.exists() and not (folder/'_internal').exists()
        assert (folder/'unrelated.txt').is_file()
    finally:
        if scheduling._run(['schtasks','/Query','/TN',task_name,'/XML']).returncode == 0:
            scheduling._write_task(task_name, None)
    report = {'setup':str(setup), 'install_path':str(folder), 'diagnostic':diagnostic,
              'verified':['no shipped data','Unicode/spaced path','all pages/themes/languages/tutorial images offline',
                          'frozen scheduled task command','disabled headless no-op','keep data byte-for-byte',
                          'remove profile task','reinstall reuses config and history','purge data','preserve unrelated files']}
    (work/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Real installer checks passed: '+str(work/'result.json'))


if __name__ == '__main__':
    main()
