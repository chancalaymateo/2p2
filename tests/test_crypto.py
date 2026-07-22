"""Pruebas de las utilidades criptograficas."""

from remote_desk.common import crypto


def test_agent_id_format():
    agent_id = crypto.generate_agent_id()
    assert len(agent_id) == 11  # '123 456 789'
    assert crypto.normalize_id(agent_id).isdigit()
    assert len(crypto.normalize_id(agent_id)) == 9


def test_password_is_random():
    assert crypto.generate_password() != crypto.generate_password()


def test_password_hash_roundtrip():
    password = crypto.generate_password()
    salt, digest = crypto.hash_password(password)
    assert crypto.verify_password(password, salt, digest)
    assert not crypto.verify_password("otra-clave", salt, digest)


def test_verify_rejects_bad_salt():
    assert not crypto.verify_password("x", "no-hex", "deadbeef")
