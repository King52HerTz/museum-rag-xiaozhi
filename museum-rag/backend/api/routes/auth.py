from secrets import token_urlsafe
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.db.models import User
from backend.infra.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_db,
    get_password_hash,
    resolve_role,
    verify_bridge_ticket,
)
from backend.schemas import AuthResponse, CurrentUserResponse, LoginRequest, RegisterRequest

router = APIRouter(tags=["auth"])


@router.post("/auth/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    username = (request.username or "").strip()
    password = (request.password or "").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(status_code=409, detail="用户名已存在")

    role = resolve_role(request.role, request.admin_code)
    user = User(username=username, password_hash=get_password_hash(password), role=role)
    db.add(user)
    db.commit()

    token = create_access_token(username=username, role=role)
    return AuthResponse(access_token=token, username=username, role=role)


@router.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(username=user.username, role=user.role)
    return AuthResponse(access_token=token, username=user.username, role=user.role)


@router.get("/auth/me", response_model=CurrentUserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return CurrentUserResponse(username=current_user.username, role=current_user.role)


@router.get("/auth/bridge-login")
async def bridge_login(ticket: str, db: Session = Depends(get_db)):
    claims = verify_bridge_ticket(ticket)
    username = claims["username"]
    role = claims["role"]

    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            username=username,
            password_hash=get_password_hash(token_urlsafe(24)),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if user.role != role:
            user.role = role
            db.commit()

    token = create_access_token(username=user.username, role=user.role)
    redirect_url = f"/?access_token={quote(token)}&bridge=1"
    return RedirectResponse(url=redirect_url, status_code=302)
