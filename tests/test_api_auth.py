"""Tests for auth utilities and routes."""
import time

import pytest
from jose import jwt

from autoquery.api.auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


# --- Unit tests for auth utilities ---


def test_hash_and_verify_password():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert verify_password("mypassword", hashed)
    assert not verify_password("wrongpassword", hashed)


def test_create_and_decode_access_token():
    token = create_access_token({"sub": "42"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "access"


def test_create_and_decode_refresh_token():
    token = create_refresh_token({"sub": "42"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["type"] == "refresh"


def test_decode_expired_token():
    from datetime import timedelta
    from fastapi import HTTPException

    token = create_access_token({"sub": "1"}, expires_delta=timedelta(seconds=-1))
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token)
    assert exc_info.value.status_code == 401


def test_decode_invalid_token():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        decode_token("not.a.token")
    assert exc_info.value.status_code == 401


# --- Route tests ---


def test_register_success(client, db_session):
    resp = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email(client, db_session):
    client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "securepass123",
    })
    resp = client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 409


def test_register_short_password(client):
    resp = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "short",
    })
    assert resp.status_code == 422


def test_login_success(client, db_session):
    client.post("/api/auth/register", json={
        "email": "login@example.com",
        "password": "securepass123",
    })
    resp = client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client, db_session):
    client.post("/api/auth/register", json={
        "email": "wrong@example.com",
        "password": "securepass123",
    })
    resp = client.post("/api/auth/login", json={
        "email": "wrong@example.com",
        "password": "badpassword1",
    })
    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 401


def test_refresh_token_flow(client, db_session):
    reg = client.post("/api/auth/register", json={
        "email": "refresh@example.com",
        "password": "securepass123",
    })
    refresh_token = reg.json()["refresh_token"]
    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
