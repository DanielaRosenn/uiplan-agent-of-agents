from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SaveResult:
    path: Path
    backup_path: Path
    bytes_written: int


def save_document(target_path: Path, content: str) -> SaveResult:
    target = target_path.resolve()
    backup = target.with_name(f"{target.name}.bak")
    original = target.read_text(encoding="utf-8") if target.exists() else ""
    backup.write_text(original, encoding="utf-8")
    target.write_text(content, encoding="utf-8")
    return SaveResult(
        path=target,
        backup_path=backup,
        bytes_written=len(content.encode("utf-8")),
    )
