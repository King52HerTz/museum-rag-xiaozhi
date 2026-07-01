import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
import json
import logging

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.infra.database import SessionLocal
from backend.db.models import User

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
ADMIN_INVITE_CODE = os.getenv("ADMIN_INVITE_CODE", "")
PBKDF2_ROUNDS = int(os.getenv("PASSWORD_PBKDF2_ROUNDS", "310000"))
BRIDGE_SSO_SECRET = os.getenv("BRIDGE_SSO_SECRET", "museum-rag-bridge-dev-secret")
BRIDGE_API_KEY = os.getenv("BRIDGE_API_KEY", "").strip()
logger = logging.getLogger("museum.bridge")
DEFAULT_BRIDGE_SSO_SECRET = "museum-rag-bridge-dev-secret"
DEFAULT_JWT_SECRET = "change-this-secret"
DEFAULT_DEV_BRIDGE_API_KEY = "museum-rag-bridge-api-dev-key"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def warn_insecure_runtime_secrets() -> None:
    insecure_items: list[str] = []
    if not SECRET_KEY or SECRET_KEY == DEFAULT_JWT_SECRET:
        insecure_items.append("JWT_SECRET_KEY")
    if not BRIDGE_SSO_SECRET or BRIDGE_SSO_SECRET == DEFAULT_BRIDGE_SSO_SECRET:
        insecure_items.append("BRIDGE_SSO_SECRET")
    if not BRIDGE_API_KEY:
        insecure_items.append("BRIDGE_API_KEY(empty)")
    elif BRIDGE_API_KEY == DEFAULT_DEV_BRIDGE_API_KEY:
        insecure_items.append("BRIDGE_API_KEY(dev-default)")

    if insecure_items:
        logger.warning(
            "museum bridge runtime is using insecure development secrets: %s | production deployment must override them",
            ", ".join(insecure_items),
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not plain_password or not password_hash:
        return False

    # New format: pbkdf2_sha256$<rounds>$<salt_b64>$<digest_b64>
    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, rounds, salt_b64, digest_b64 = password_hash.split("$", 3)
            salt = base64.b64decode(salt_b64.encode("ascii"))
            expected = base64.b64decode(digest_b64.encode("ascii"))
            calculated = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt,
                int(rounds),
            )
            return hmac.compare_digest(calculated, expected)
        except Exception:
            return False

    # Backward compatibility for legacy passlib/bcrypt hashes.
    if password_hash.startswith("$2") or password_hash.startswith("$bcrypt"):
        try:
            from passlib.context import CryptContext

            legacy_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")
            return legacy_context.verify(plain_password, password_hash)
        except Exception:
            return False

    return False


def get_password_hash(password: str) -> str:
    if not password:
        raise ValueError("password is required")

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ROUNDS,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${PBKDF2_ROUNDS}${salt_b64}${digest_b64}"


def create_access_token(username: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或过期的认证令牌",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise credentials_exception
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="管理员权限不足")
    return current_user


def verify_bridge_api_key(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    trace_id = str(getattr(request.state, "bridge_trace_id", "") or request.headers.get("X-Bridge-Trace-Id") or "").strip()
    configured_key = (BRIDGE_API_KEY or "").strip()
    if not configured_key:
        logger.error(
            "museum bridge auth config missing | trace_id=%s | path=%s",
            trace_id or "-",
            request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": 50301,
                "message": "服务端未配置博物馆桥接鉴权密钥",
                "query": "",
                "contexts": [],
                "trace": {},
                "error_code": "BRIDGE_API_KEY_NOT_CONFIGURED",
                "details": [],
            },
        )

    auth_header = (authorization or "").strip()
    prefix = "Bearer "
    if not auth_header.startswith(prefix):
        logger.warning(
            "museum bridge auth missing | trace_id=%s | path=%s",
            trace_id or "-",
            request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": 40101,
                "message": "缺少桥接服务认证信息",
                "query": "",
                "contexts": [],
                "trace": {},
                "error_code": "BRIDGE_AUTH_MISSING",
                "details": [],
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    provided_key = auth_header[len(prefix) :].strip()
    if not provided_key or not hmac.compare_digest(provided_key, configured_key):
        logger.warning(
            "museum bridge auth invalid | trace_id=%s | path=%s",
            trace_id or "-",
            request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": 40102,
                "message": "桥接服务认证失败",
                "query": "",
                "contexts": [],
                "trace": {},
                "error_code": "BRIDGE_AUTH_INVALID",
                "details": [],
            },
            headers={"WWW-Authenticate": "Bearer"},
        )


def resolve_role(requested_role: str | None, admin_code: str | None) -> str:
    role = (requested_role or "user").strip().lower()
    if role != "admin":
        return "user"
    expected = (ADMIN_INVITE_CODE or "").strip()
    provided = (admin_code or "").strip()
    if not expected:
        raise HTTPException(status_code=403, detail="服务端未配置管理员邀请码")
    if provided == expected:
        return "admin"
    raise HTTPException(status_code=403, detail="管理员邀请码错误")


def _decode_b64url(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def verify_bridge_ticket(ticket: str) -> dict:
    if not ticket or "." not in ticket:
        raise HTTPException(status_code=401, detail="知识库免登录票据无效")

    payload_b64, signature = ticket.split(".", 1)
    expected_signature = hmac.new(
        BRIDGE_SSO_SECRET.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="知识库免登录票据签名校验失败")

    try:
        payload_raw = _decode_b64url(payload_b64)
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="知识库免登录票据格式错误") from exc

    username = str(payload.get("username") or "").strip()
    role = str(payload.get("role") or "user").strip().lower()
    exp = payload.get("exp")

    if not username:
        raise HTTPException(status_code=401, detail="知识库免登录票据缺少用户名")

    if role not in {"admin", "user"}:
        role = "user"

    try:
        exp_value = int(exp)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="知识库免登录票据过期时间无效") from exc

    now = int(datetime.now(timezone.utc).timestamp())
    if exp_value < now:
        raise HTTPException(status_code=401, detail="知识库免登录票据已过期")

    return {
        "username": username,
        "role": role,
        "source": str(payload.get("source") or ""),
        "sub": str(payload.get("sub") or ""),
    }
