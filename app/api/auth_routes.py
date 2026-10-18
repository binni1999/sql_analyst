from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

try:
    from services.auth_service import (
        _new_session, authenticate_user, clear_session_cookie, current_user,
        register_user, revoke_session, set_session_cookie, _validate_origin,
        enforce_login_rate_limit, record_failed_login, clear_login_attempts,
    )
except ImportError:
    from app.services.auth_service import (
        _new_session, authenticate_user, clear_session_cookie, current_user,
        register_user, revoke_session, set_session_cookie, _validate_origin,
        enforce_login_rate_limit, record_failed_login, clear_login_attempts,
    )

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class SignupBody(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)

class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)

@router.post("/signup", status_code=201)
def signup(body: SignupBody, request: Request, response: Response):
    _validate_origin(request)
    user = register_user(body.name, body.email, body.password)
    try:
        token = _new_session(user["id"])
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Could not create a session") from exc
    set_session_cookie(response, token)
    return {"user": user}

@router.post("/login")
def login(body: LoginBody, request: Request, response: Response):
    _validate_origin(request)
    client_ip = request.client.host if request.client else "unknown"
    enforce_login_rate_limit(client_ip)
    try:
        user = authenticate_user(body.email, body.password)
    except HTTPException as exc:
        if exc.status_code == 401:
            record_failed_login(client_ip)
        raise
    clear_login_attempts(client_ip)
    token = _new_session(user["id"])
    set_session_cookie(response, token)
    return {"user": user}

@router.get("/me")
def me(user: dict = Depends(current_user)):
    return {"user": user}

@router.post("/logout")
def logout(request: Request, response: Response, _user: dict = Depends(current_user)):
    _validate_origin(request)
    revoke_session(request)
    clear_session_cookie(response)
    return {"success": True}
