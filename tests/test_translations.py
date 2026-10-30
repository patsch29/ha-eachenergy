"""All languages must offer the same translation keys."""
import json
import pathlib

BASE = pathlib.Path(__file__).parents[1] / "custom_components" / "eachenergy" / "translations"


def _keys(obj, prefix=""):
    if isinstance(obj, dict):
        out = set()
        for k, v in obj.items():
            out |= _keys(v, f"{prefix}.{k}" if prefix else k)
        return out
    return {prefix}


def test_languages_have_identical_keys():
    langs = {p.stem: _keys(json.loads(p.read_text(encoding="utf-8"))) for p in BASE.glob("*.json")}
    reference = langs["en"]
    for lang, keys in langs.items():
        assert keys == reference, f"{lang}: missing {reference - keys}, extra {keys - reference}"
