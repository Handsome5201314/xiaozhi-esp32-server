"""保全既有工作，并准备无生产配置的隔离测试目录。"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root = next(parent for parent in Path(__file__).resolve().parents if (parent / '.git').is_dir())
source = root.with_name('xiaozhi-esp32-server-v0.9.6')
backup = root / '.git' / 'merge-backups' / '20260909-v096'
backup.mkdir(parents=True, exist_ok=False)

def git_files(*args):
    return subprocess.check_output(['git', *args, '-z'], cwd=root).decode().rstrip('\0').split('\0')

dirty = set(git_files('diff', '--name-only')) | set(git_files('diff', '--cached', '--name-only'))
dirty |= set(git_files('ls-files', '--others', '--exclude-standard'))
hashes = {}
for relative in sorted(dirty):
    path = root / relative
    if relative and path.is_file() and not relative.startswith('.trellis/tasks/09-09-merge-v096-worktree/'):
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
(backup / 'preexisting-hashes.json').write_text(json.dumps(hashes, ensure_ascii=False, indent=2), encoding='utf-8')
patch = subprocess.check_output(['git', '-C', str(source), 'diff', '--binary'], cwd=root)
(backup / 'source.patch').write_bytes(patch)
changed = subprocess.check_output(['git', '-C', str(source), 'diff', '--name-only', '-z']).decode().rstrip('\0').split('\0')
for relative in changed:
    target = backup / 'original' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / relative, target)
for relative in ['main/xiaozhi-server/tests/test_medical_gateway.py', 'main/xiaozhi-server/tests/test_connection_bind_wait.py', 'main/xiaozhi-server/tests/test_medical_session_store.py']:
    shutil.copy2(source / relative, root / relative)

test_root = backup / 'test-root'
prefix = 'main/xiaozhi-server/'
for relative in git_files('ls-files', 'main/xiaozhi-server'):
    path = root / relative
    if path.is_file():
        target = test_root / relative.removeprefix(prefix)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
for path in (root / prefix / 'tests').glob('test_*.py'):
    shutil.copy2(path, test_root / 'tests' / path.name)
(test_root / 'data').mkdir(exist_ok=True)
(test_root / 'data' / '.config.yaml').write_text('read_config_from_api: false\nmanager-api:\n  url: ""\n', encoding='utf-8')
print(f'Protected {len(hashes)} preexisting files; copied source tests; prepared {test_root}')
