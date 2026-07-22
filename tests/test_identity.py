"""Pruebas de la identidad: permanencia (determinismo) y verificador Luhn."""

from remote_desk.common.identity import _derive_id, _luhn_check_digit


def test_id_is_deterministic_per_device():
    # Mismo device + nonce => mismo ID (permanente).
    assert _derive_id("dev-1", "n1") == _derive_id("dev-1", "n1")


def test_id_differs_by_device_and_nonce():
    assert _derive_id("dev-1", "n1") != _derive_id("dev-2", "n1")
    assert _derive_id("dev-1", "n1") != _derive_id("dev-1", "n2")  # reset cambia nonce


def test_id_format_is_nine_digits_grouped():
    value = _derive_id("dev-1", "n1")
    assert len(value) == 11  # '123 456 789'
    digits = value.replace(" ", "")
    assert digits.isdigit() and len(digits) == 9


def test_last_digit_is_valid_luhn_check():
    digits = _derive_id("dev-xyz", "abc").replace(" ", "")
    assert _luhn_check_digit(digits[:-1]) == int(digits[-1])
