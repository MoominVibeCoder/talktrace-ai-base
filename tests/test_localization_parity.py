"""DE/EN localization parity.

Every section and every key must exist in both languages, and no string value
may be empty. This is the automated guard the project previously lacked — it
caught the historical `system_prompts` indentation drift and protects every
section added afterwards (e.g. the Start tab).
"""

from talktrace_ai.localization.de import STRINGS as DE
from talktrace_ai.localization.en import STRINGS as EN


def test_same_top_level_sections():
    de_only = sorted(set(DE) - set(EN))
    en_only = sorted(set(EN) - set(DE))
    assert set(DE) == set(EN), f"section mismatch: DE-only={de_only} EN-only={en_only}"


def test_same_keys_per_section():
    for section in sorted(set(DE) & set(EN)):
        de_keys, en_keys = set(DE[section]), set(EN[section])
        de_only = sorted(de_keys - en_keys)
        en_only = sorted(en_keys - de_keys)
        assert de_keys == en_keys, (
            f"[{section}] DE-only={de_only} EN-only={en_only}"
        )


def test_no_empty_string_values():
    for strings, lang in ((DE, "DE"), (EN, "EN")):
        for section, entries in strings.items():
            for key, val in entries.items():
                if isinstance(val, str):
                    assert val.strip(), f"{lang} empty value: {section}.{key}"
