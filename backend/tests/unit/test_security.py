import uuid

import pytest

from app.services.security import (
    InvalidTokenError,
    create_access_token,
    create_invite_token,
    create_refresh_token,
    decode_invite_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correcthorsebatterystaple")
    assert verify_password("correcthorsebatterystaple", hashed)
    assert not verify_password("wrong password", hashed)


def test_password_hashes_are_salted():
    # same password, hashed twice, must not produce identical hashes
    assert hash_password("same password") != hash_password("same password")


def test_access_and_refresh_tokens_roundtrip():
    user_id = uuid.uuid4()
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)

    assert decode_token(access, expected_type="access") == user_id
    assert decode_token(refresh, expected_type="refresh") == user_id


def test_token_type_confusion_is_rejected():
    user_id = uuid.uuid4()
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)

    with pytest.raises(InvalidTokenError):
        decode_token(access, expected_type="refresh")
    with pytest.raises(InvalidTokenError):
        decode_token(refresh, expected_type="access")


def test_garbage_token_is_rejected():
    with pytest.raises(InvalidTokenError):
        decode_token("not.a.jwt", expected_type="access")


def test_invite_token_roundtrip():
    org_id = uuid.uuid4()
    token = create_invite_token(org_id, "new.hire@example.com", "member")
    claims = decode_invite_token(token)

    assert claims["org_id"] == org_id
    assert claims["email"] == "new.hire@example.com"
    assert claims["role"] == "member"


def test_invite_token_rejected_as_access_token():
    token = create_invite_token(uuid.uuid4(), "x@example.com", "member")
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type="access")
