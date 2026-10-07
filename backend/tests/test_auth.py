import pytest
from httpx import AsyncClient

from backend.app.db.models.user import User


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    payload = {
        "email": "newstudent@example.com",
        "username": "newstudent",
        "password": "SecurePassword123!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newstudent@example.com"
    assert data["username"] == "newstudent"
    assert data["role"] == "student"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, student_user: User):
    payload = {
        "email": student_user.email,
        "username": "different_username",
        "password": "Password123!",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "email already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success_and_cookie(client: AsyncClient, student_user: User):
    payload = {
        "email": student_user.email,
        "password": "StudentPass123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # Check httpOnly cookie
    assert "refresh_token" in response.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, student_user: User):
    payload = {
        "email": student_user.email,
        "password": "WrongPassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_lifecycle(client: AsyncClient, student_user: User):
    # 1. Login to get cookie
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": student_user.email, "password": "StudentPass123!"},
    )
    assert login_resp.status_code == 200
    refresh_token = login_resp.cookies.get("refresh_token")
    assert refresh_token is not None

    # 2. Call refresh
    client.cookies.set("refresh_token", refresh_token)
    refresh_resp = await client.post("/api/v1/auth/refresh")
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    assert "access_token" in new_data


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, student_user: User):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": student_user.email, "password": "StudentPass123!"},
    )
    assert "refresh_token" in login_resp.cookies

    logout_resp = await client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200


@pytest.mark.asyncio
async def test_get_me_authenticated(
    client: AsyncClient, student_user: User, student_auth_headers: dict
):
    response = await client.get("/api/v1/auth/me", headers=student_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == student_user.id
    assert data["email"] == student_user.email


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
