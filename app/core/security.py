from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

from app.core.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict):
    to_encode = data.copy()

    # Наша фича: вечный токен или на 12 часов
    if settings.AUTHORIZATION_NEVER_EXPIRES:
        expire = datetime.utcnow() + timedelta(days=36500)
    else:
        expire = datetime.utcnow() + timedelta(minutes=1440)  # 24 часа

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

