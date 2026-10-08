import uuid
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hashing_argon2id():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_generation_and_decoding():
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    roles = ["Tenant Admin"]
    permissions = ["document.read", "user.manage"]

    access_token = create_access_token(
        subject=user_id,
        tenant_id=tenant_id,
        roles=roles,
        permissions=permissions
    )

    decoded = decode_token(access_token)
    assert decoded is not None
    assert decoded["sub"] == user_id
    assert decoded["tenant_id"] == tenant_id
    assert decoded["type"] == "access"
    assert "Tenant Admin" in decoded["roles"]
    assert "user.manage" in decoded["permissions"]


def test_refresh_token_decoding():
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())

    refresh_token = create_refresh_token(subject=user_id, tenant_id=tenant_id)
    decoded = decode_token(refresh_token)

    assert decoded is not None
    assert decoded["sub"] == user_id
    assert decoded["tenant_id"] == tenant_id
    assert decoded["type"] == "refresh"
