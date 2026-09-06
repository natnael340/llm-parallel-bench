"""Staging helpers: copy a selected implementation variant into a fixed
staging directory and generate the adapter file that maps the canonical
entry symbol onto whatever the implementation exposes.

Research artifacts (llm_written/, baselines/) are never modified — only
their copies in the staging directory are rewritten.
"""

import re
import shutil
from pathlib import Path


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def copy_files(root: Path, files: list, dest: Path) -> list:
    """Copy `files` (paths relative to `root`) into `dest` (flat). Returns dest paths."""
    out = []
    for f in files:
        src = root / f
        if not src.is_file():
            raise FileNotFoundError(f"variant file not found: {src}")
        dst = dest / Path(f).name
        shutil.copy2(src, dst)
        out.append(dst)
    return out


_GO_PACKAGE_RE = re.compile(r"^package\s+\w+", re.MULTILINE)


def rewrite_go_package(path: Path, package: str = "staging") -> None:
    """Rewrite the package declaration of a staged Go file copy."""
    text = path.read_text()
    new, n = _GO_PACKAGE_RE.subn(f"package {package}", text, count=1)
    if n == 0:
        raise ValueError(f"no package declaration found in {path}")
    path.write_text(new)


_JAVA_PACKAGE_RE = re.compile(r"^\s*package\s+[\w.]+\s*;\s*$", re.MULTILINE)


def strip_java_package(path: Path) -> None:
    """Drop the package declaration from a staged Java file copy so all
    staged classes live in the default package alongside the harness."""
    text = path.read_text()
    path.write_text(_JAVA_PACKAGE_RE.sub("", text, count=1))


def adapter_text(variant: dict) -> str:
    """The adapter source from a manifest variant; accepts string or list of lines."""
    adapter = variant.get("adapter", "")
    if isinstance(adapter, list):
        adapter = "\n".join(adapter)
    return adapter.rstrip() + "\n"


def write_adapter(path: Path, header: str, variant: dict) -> None:
    path.write_text(header + adapter_text(variant))
