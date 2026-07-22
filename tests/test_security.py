"""Pruebas del control anti fuerza-bruta del servidor."""

from remote_desk.server.security import LoginThrottle


def test_locks_after_max_attempts():
    throttle = LoginThrottle(max_attempts=3, lockout_seconds=60)
    key = "1.2.3.4:123456789"

    assert not throttle.is_locked(key)
    for _ in range(3):
        throttle.record_failure(key)
    assert throttle.is_locked(key)


def test_success_resets_counter():
    throttle = LoginThrottle(max_attempts=3, lockout_seconds=60)
    key = "1.2.3.4:123456789"

    throttle.record_failure(key)
    throttle.record_failure(key)
    throttle.record_success(key)
    throttle.record_failure(key)
    assert not throttle.is_locked(key)
