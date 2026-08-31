from __future__ import annotations
import json, os, tempfile, time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
import yaml

class LockTimeout(RuntimeError): pass

@contextmanager
def file_lock(path: Path, timeout: float = 10.0) -> Iterator[None]:
    lock = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise LockTimeout(f"Timed out acquiring {lock}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try: lock.unlink()
        except FileNotFoundError: pass

def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def atomic_write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name+".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
            f.flush(); os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)

def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line=json.dumps(record, ensure_ascii=False, sort_keys=True)+"\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line); f.flush(); os.fsync(f.fileno())
