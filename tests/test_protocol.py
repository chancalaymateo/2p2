"""Pruebas del (de)serializador del protocolo."""

import pytest

from remote_desk.common.protocol import Signal, make, parse


def test_make_and_parse_roundtrip():
    raw = make(Signal.CONNECT_REQUEST, agent_id="123456789", password="abc")
    msg = parse(raw)
    assert msg["type"] == Signal.CONNECT_REQUEST
    assert msg["agent_id"] == "123456789"
    assert msg["password"] == "abc"


def test_parse_rejects_non_json():
    with pytest.raises(ValueError):
        parse("no soy json {")


def test_parse_rejects_missing_type():
    with pytest.raises(ValueError):
        parse('{"foo": 1}')
