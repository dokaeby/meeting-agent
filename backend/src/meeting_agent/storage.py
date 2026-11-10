from pathlib import Path
from uuid import uuid4


def path_for(settings, key: str) -> Path:
    root = settings.storage_path.resolve()
    path = (root / key).resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("invalid storage key")
    return path


def store(settings, org: str, meeting: str, content: bytes, suffix: str):
    key = f"{org}/{meeting}/{uuid4().hex}{suffix}"
    path = path_for(settings, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return key
