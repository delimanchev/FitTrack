from hmac import compare_digest
from urllib.parse import quote

import httpx
import jwt
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer


bearer = HTTPBearer(auto_error=False)
service_token = APIKeyHeader(name="X-Service-Token", auto_error=False)


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    error = HTTPException(
        status_code=401,
        detail="A valid access token is required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise error

    settings = request.app.state.settings
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings["JWT_SECRET"],
            algorithms=["HS256"],
            issuer=settings["JWT_ISSUER"],
            audience=settings["JWT_AUDIENCE"],
            options={"require": ["sub", "exp", "iss", "aud"]},
        )
    except jwt.InvalidTokenError:
        raise error from None

    user_id = payload["sub"]
    if not isinstance(user_id, str) or not user_id.strip() or len(user_id) > 200:
        raise error
    return user_id


def verify_user(request: Request, user_id: str):
    try:
        response = request.app.state.user_api.get(f"/users/{quote(user_id, safe='')}")
    except httpx.RequestError:
        raise HTTPException(503, "User Service is unavailable") from None

    if response.status_code == 404:
        raise HTTPException(404, "User does not exist")
    if response.status_code != 200:
        raise HTTPException(503, "User Service is unavailable")


def internal_user(
    request: Request,
    token: str | None = Depends(service_token),
    x_user_id: str | None = Header(default=None, max_length=200),
) -> str:
    expected = request.app.state.settings["USER_TO_NUTRITION_TOKEN"]
    if token is None or not compare_digest(token.encode(), expected.encode()):
        raise HTTPException(403, "Invalid service token")
    if x_user_id is None or not x_user_id.strip():
        raise HTTPException(400, "X-User-Id is required")
    return x_user_id
