"""认证：注册 / 登录 / 当前用户（JWT，SQLite users 表）"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import settings
from database.db import get_db
from models.user_model import User

router = APIRouter()
security = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"


class RegisterBody(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=72)


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=72)


class UserPublic(BaseModel):
    id: int
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class MeResponse(BaseModel):
    id: int
    username: str


class ChangePasswordBody(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=6, max_length=72)


def _hash_password(raw: str) -> str:
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(raw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(raw.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def _create_token(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
    payload = {"sub": username, "uid": user_id, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    if creds is None or not creds.credentials:
        return None
    try:
        payload = _decode_token(creds.credentials)
    except jwt.PyJWTError:
        return None
    uid = payload.get("uid")
    if uid is None:
        return None
    return db.query(User).filter(User.id == int(uid)).first()


def require_user(
    user: User | None = Depends(get_optional_user),
) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="未登录或令牌无效")
    return user


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterBody, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == body.username).first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    row = User(username=body.username, password_hash=_hash_password(body.password))
    db.add(row)
    db.commit()
    db.refresh(row)
    token = _create_token(row.id, row.username)
    return TokenResponse(
        access_token=token,
        user=UserPublic(id=row.id, username=row.username),
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginBody, db: Session = Depends(get_db)):
    row = db.query(User).filter(User.username == body.username.strip()).first()
    if row is None or not _verify_password(body.password, row.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = _create_token(row.id, row.username)
    return TokenResponse(
        access_token=token,
        user=UserPublic(id=row.id, username=row.username),
    )


@router.get("/me", response_model=MeResponse)
def me(user: User = Depends(require_user)):
    return MeResponse(id=user.id, username=user.username)


@router.post("/change-password")
def change_password(
    body: ChangePasswordBody,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    print(f"[auth.password] user_id={user.id}", flush=True)
    if not _verify_password(body.current_password, user.password_hash):
        print("[auth.password] result=error reason=current_password_incorrect", flush=True)
        raise HTTPException(status_code=400, detail="当前密码不正确，请重新输入")
    if body.new_password == body.current_password:
        print("[auth.password] result=error reason=new_same_as_current", flush=True)
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    row = db.query(User).filter(User.id == user.id).first()
    if row is None:
        print("[auth.password] result=error reason=user_not_found", flush=True)
        raise HTTPException(status_code=404, detail="用户不存在")
    row.password_hash = _hash_password(body.new_password)
    db.commit()
    print("[auth.password] result=success", flush=True)
    return {"ok": True, "message": "密码已更新"}


@router.post("/logout")
def logout():
    """无状态 JWT：客户端丢弃 token 即可；此处仅占位便于前端统一调用。"""
    return {"ok": True}
