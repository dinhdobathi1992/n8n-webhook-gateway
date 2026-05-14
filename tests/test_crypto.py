from app.crypto import decrypt, encrypt


def test_roundtrip():
    original = "my-secret-value"
    encrypted = encrypt(original)
    assert encrypted != original
    assert decrypt(encrypted) == original


def test_none_passthrough():
    assert encrypt(None) is None
    assert decrypt(None) is None


def test_different_inputs_different_ciphertexts():
    a = encrypt("secret-a")
    b = encrypt("secret-b")
    assert a != b


def test_plaintext_fallback():
    assert decrypt("not-encrypted-plaintext") == "not-encrypted-plaintext"
