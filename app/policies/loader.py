"""Load ``data/company/company.yaml`` without requiring a healthy PyYAML install."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

COMPANY_YAML = Path("data/company/company.yaml")


def load_company_config(path: Path | None = None) -> dict[str, Any]:
    """Load the NexaCommerce world model.

    Prefers PyYAML when ``safe_load`` is available; otherwise parses the
    restricted YAML subset used by this repository.
    """
    target = path or COMPANY_YAML
    text = target.read_text(encoding="utf-8")
    try:
        import yaml

        if hasattr(yaml, "safe_load"):
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    data = parse_simple_yaml(text)
    if not isinstance(data, dict):
        raise ValueError("company.yaml must be a mapping")
    return data


@lru_cache(maxsize=1)
def load_cached_company_config() -> dict[str, Any]:
    """Cached loader for the policy engine and generator."""
    return load_company_config()


def parse_simple_yaml(text: str) -> Any:
    """Parse indented mappings and lists used in ``company.yaml``."""
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = raw.split("#", 1)[0].rstrip()
        if not stripped:
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, stripped.lstrip()))
    value, _ = _parse_block(lines, 0, 0)
    return value


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index
    _, content = lines[index]
    if content.startswith("- "):
        return _parse_list(lines, index, indent)
    return _parse_mapping(lines, index, indent)


def _parse_mapping(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ValueError(f"Unexpected indent at {content!r}")
        if content.startswith("- "):
            break
        key, _, remainder = content.partition(":")
        key = key.strip()
        remainder = remainder.strip()
        index += 1
        if remainder:
            result[key] = _parse_scalar(remainder)
            continue
        if index < len(lines) and lines[index][0] > current_indent:
            value, index = _parse_block(lines, index, lines[index][0])
            result[key] = value
        else:
            result[key] = None
    return result, index


def _parse_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent or not content.startswith("- "):
            break
        item = content[2:].strip()
        index += 1
        if item:
            result.append(_parse_scalar(item))
            continue
        if index < len(lines) and lines[index][0] > current_indent:
            value, index = _parse_block(lines, index, lines[index][0])
            result.append(value)
        else:
            result.append(None)
    return result, index


def _parse_scalar(value: str) -> Any:
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    lowered = value.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
