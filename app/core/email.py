from typing import Optional

from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from mailtrap import APIError


def create_verification_token(email: str, expires_delta: Optional[timedelta] = None):
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # По умолчанию оставляем 24 часа для регистрации
        expire = datetime.now(timezone.utc) + timedelta(hours=24)

    to_encode = {"exp": expire, "sub": email}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


import mailtrap as mt
from fastapi.concurrency import run_in_threadpool
from app.core.settings import settings


def _send_mail_sync(email_to: str, verify_url: str):
    """Синхронная отправка через SDK v2.x"""
    # Создаем клиент, передавая токен
    client = mt.MailtrapClient(token=settings.MAIL_TOKEN)

    # Создаем объект письма
    mail = mt.Mail(
        sender=mt.Address(email=settings.MAIL_FROM, name=settings.MAIL_FROM_NAME),
        to=[mt.Address(email=email_to)],
        subject="Подтверждение регистрации OpenChemDB",
        html=f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eee; padding: 20px;">
            <h2 style="color: #2c3e50;">Добро пожаловать в OpenChemDB!</h2>
            <p>Вы успешно зарегистрировались в системе химических баз данных.</p>
            <p>Для активации вашего аккаунта, пожалуйста, нажмите на кнопку ниже:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verify_url}" 
                   style="background-color: #4CAF50; color: white; padding: 12px 25px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                   Активировать аккаунт
                </a>
            </div>
            <p style="font-size: 0.8em; color: #7f8c8d;">Ссылка действительна в течение 24 часов.</p>
        </div>
        """,
        category="Registration"
    )

    try:
        client.send(mail)
    except APIError as e:
        # Логируем ошибку, но не даем приложению упасть
        print(f"Ошибка Mailtrap: {e}")


async def send_verification_email(email: str, token: str):
    """Асинхронный вызов из вашего роутера"""
    verify_url = f"{settings.BACKEND_URL}/verify-email?token={token}"
    await run_in_threadpool(_send_mail_sync, email, verify_url)


def _send_reset_password_sync(email_to: str, reset_url: str):
    client = mt.MailtrapClient(token=settings.MAIL_TOKEN)

    mail = mt.Mail(
        sender=mt.Address(email=settings.MAIL_FROM, name=settings.MAIL_FROM_NAME),
        to=[mt.Address(email=email_to)],
        subject="Сброс пароля OpenChemDB",
        html=f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eee; padding: 20px;">
            <h2 style="color: #2c3e50;">Восстановление доступа</h2>
            <p>Мы получили запрос на сброс пароля для вашего аккаунта в OpenChemDB.</p>
            <p>Если вы этого не делали, просто проигнорируйте это письмо.</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background-color: #e74c3c; color: white; padding: 12px 25px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                   Сбросить пароль
                </a>
            </div>
            <p style="font-size: 0.8em; color: #7f8c8d;">Ссылка действительна 1 час.</p>
        </div>
        """,
        category="Password Reset"
    )
    client.send(mail)


async def send_reset_password_email(email: str, token: str):
    # Урл должен вести на страницу фронтенда, где есть форма ввода нового пароля
    reset_url = f"{settings.BACKEND_URL}/reset-password-page?token={token}"
    await run_in_threadpool(_send_reset_password_sync, email, reset_url)