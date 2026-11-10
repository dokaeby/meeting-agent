import pytest

from meeting_agent.security import decrypt, digest, encrypt, password_hash, verify_password


def test_password_and_tokens():
    encoded = password_hash("Very-long-test-password1!")
    assert verify_password("Very-long-test-password1!", encoded)
    assert not verify_password("wrong", encoded)
    assert digest("token") != "token"


def test_encryption_is_authenticated():
    value = encrypt({"access_token": "private"}, "test-secret")
    assert "private" not in value
    assert decrypt(value, "test-secret")["access_token"] == "private"
    with pytest.raises(ValueError):
        decrypt(value, "wrong-secret")
