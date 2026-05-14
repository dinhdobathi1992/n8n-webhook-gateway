from app.crypto import decrypt, encrypt


def test_roundtrip():
    secret = "xoxb-my-slack-signing-secret-123"
    assert decrypt(encrypt(secret)) == secret


def test_none_passthrough():
    assert encrypt(None) is None
    assert decrypt(None) is None


def test_different_inputs_different_ciphertexts():
    a = encrypt("secret-a")
    b = encrypt("secret-b")
    assert a != b
