"""Tests for the reproducibility fingerprint (pure, deterministic)."""
from talktrace_ai.utils.fingerprint import compute_fingerprint


def _fp(**kw):
    base = dict(codebook="cb", system_prompt="sys", user_prompt="usr",
                model="m", transcript="S01: hi")
    base.update(kw)
    return compute_fingerprint(**base)


def test_length_and_hex():
    fp = _fp()
    assert len(fp) == 12
    assert all(c in "0123456789abcdef" for c in fp)


def test_deterministic():
    assert _fp() == _fp()


def test_each_ingredient_changes_the_hash():
    base = _fp()
    for field in ("codebook", "system_prompt", "user_prompt", "model", "transcript"):
        assert _fp(**{field: "different"}) != base, field


def test_newline_normalization():
    # CRLF / CR / LF on the same logical content collapse to one fingerprint.
    assert _fp(transcript="a\r\nb") == _fp(transcript="a\nb") == _fp(transcript="a\rb")


def test_none_is_treated_as_empty_string():
    assert _fp(codebook=None) == _fp(codebook="")


def test_separator_prevents_field_collision():
    # Moving a character across a field boundary must change the hash, i.e.
    # ("ab","c") and ("a","bc") are distinct thanks to the unit separator.
    assert compute_fingerprint("ab", "c", "u", "m", "t") != \
        compute_fingerprint("a", "bc", "u", "m", "t")
