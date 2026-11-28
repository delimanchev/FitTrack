import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


bearer = HTTPBearer(auto_error=False)


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> str:
    error = HTTPException(
        401, "A valid access token is required", headers={"WWW-Authenticate": "Bearer"},
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
