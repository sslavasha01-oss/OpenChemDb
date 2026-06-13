from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Form
from fastapi import Request
from fastapi.responses import HTMLResponse
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_users_db
from app.core.email import create_verification_token, send_verification_email, send_reset_password_email
from app.core.limiter import rate_limit
from app.core.security import get_password_hash
from app.core.settings import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, ResetPasswordUpdate, ForgotPasswordRequest  # Ваши схемы

router = APIRouter()


@router.post("/register-prod", response_model=UserOut)
@rate_limit(requests=5, window_seconds=3600)
async def register_prod(
        request: Request,
        user_data: UserCreate,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_users_db)
):
    # 1. Проверка на дубликаты (как в вашем коде)
    result = await db.execute(select(User).where(
        (User.username == user_data.username) | (User.email == user_data.email)
    ))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email or username already exists")

    if settings.LOCAL_MODE:
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            role="USER" ,
            is_active=True
        )
    else:
        # 2. Создаем НЕАКТИВНОГО пользователя
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            role="USER",
            is_active=False
        )

    db.add(new_user)
    # 3. Генерируем токен и отправляем письмо в фоне (не тормозим ответ API)
    if not settings.LOCAL_MODE:
        token = create_verification_token(user_data.email)
        background_tasks.add_task(send_verification_email, user_data.email, token)
    if not settings.LOCAL_MODE:
        user_tariff = getattr(new_user, "tariff_plan", "FREE")
        new_user.max_allowed_size = settings.TARIFF_LIMITS.get(user_tariff, settings.TARIFF_LIMITS["FREE"])
    else:
        new_user.max_allowed_size = 0

    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email_page(token: str, db: AsyncSession = Depends(get_users_db)):
    try:
        # Декодируем токен
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")

        if email is None:
            return render_error_page("Invalid activation token.")

        # Ищем пользователя
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return render_error_page("User not found.")

        if user.is_active:
            return render_success_page("Account already activated!")

        # Активируем
        user.is_active = True
        await db.commit()

        return render_success_page("Account successfully activated!")

    except JWTError:
        return render_error_page("Activation link expired or invalid.")


# Вспомогательные функции для красоты
def render_success_page(message: str):
    return f"""
    <html>
        <head>
            <title>OpenChemDB - Success</title>
            <style>
                body {{ font-family: sans-serif; display: flex; justify-content: center; padding-top: 100px; background-color: #f4f4f9; }}
                .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; width: 400px; }}
                h2 {{ color: #27ae60; margin-bottom: 20px; }}
                p {{ color: #555; line-height: 1.6; }}
                .icon {{ font-size: 50px; color: #27ae60; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon">✔</div>
                <h2>Done!</h2>
                <p>{message}</p>
                <br>
                <p style="font-size: 0.9em; color: #888;">You may close this window.</p>
            </div>
        </body>8
    </html>
    """


def render_error_page(error_message: str):
    return f"""
    <html>
        <head>
            <title>OpenChemDB - Error</title>
            <style>
                body {{ font-family: sans-serif; display: flex; justify-content: center; padding-top: 100px; background-color: #f4f4f9; }}
                .card {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; width: 400px; }}
                h2 {{ color: #e74c3c; margin-bottom: 20px; }}
                p {{ color: #555; line-height: 1.6; }}
                .icon {{ font-size: 50px; color: #e74c3c; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon">✘</div>
                <h2>Activation Error</h2>
                <p>{error_message}</p>
                <br>
                <p><a href="/" style="color: #3498db; text-decoration: none;">На главную</a></p>
            </div>
        </body>
    </html>
    """


# 1. Запрос на сброс пароля
@router.post("/forgot-password")
@rate_limit(requests=5, window_seconds=3600)
async def forgot_password(
        request: Request,
        data: ForgotPasswordRequest,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_users_db)
):
    if settings.LOCAL_MODE:
        raise HTTPException(status_code=400, detail="Endpoint is disabled in local mode")

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # В целях безопасности не говорим, есть такой email или нет
    if user:
        # Генерируем токен (используем тот же метод, но уменьшаем exp)
        token = create_verification_token(user.email, expires_delta=timedelta(hours=1))
        background_tasks.add_task(send_reset_password_email, user.email, token)

    return {"message": "If this email is registered, a reset link has been sent."}


# 2. Установка нового пароля
@router.post("/reset-password-confirm")
async def reset_password_confirm(
        data: ResetPasswordUpdate,
        db: AsyncSession = Depends(get_users_db)
):
    try:
        payload = jwt.decode(data.token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=400, detail="Token is invalid or expired")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Хешируем новый пароль и сохраняем
    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()

    return {"message": "Password changed successfully. You can now log in."}


@router.post("/reset-password-confirm-html", response_class=HTMLResponse)
async def reset_password_confirm_html(
        token: str = Form(...),
        new_password: str = Form(...),
        db: AsyncSession = Depends(get_users_db)
):
    try:
        # Проверяем токен (та же логика, что была раньше)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return "<h3>Error: User not found.</h3>"

        # Хешируем и сохраняем
        user.hashed_password = get_password_hash(new_password)
        await db.commit()

        return """
        <div style="text-align:center; padding-top:50px; font-family:sans-serif;">
            <h2 style="color: green;">Password changed successfully!</h2>
            <p>You can now log in to the system with your new password.</p>
        </div>
        """
    except JWTError:
        return "<h3>Error: Link expired or invalid.</h3>"


@router.get("/reset-password-page", response_class=HTMLResponse)
async def reset_password_page(token: str):
    return f"""
    <html>
        <head>
            <title>OpenChemDB - Reset Password</title>
            <style>
                body {{ font-family: sans-serif; display: flex; justify-content: center; padding-top: 50px; background-color: #f4f4f9; }}
                .card {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 350px; }}
                h2 {{ color: #333; font-size: 20px; margin-bottom: 20px; }}
                input {{ width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
                button {{ width: 100%; padding: 12px; background-color: #2c3e50; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; margin-top: 10px; }}
                button:disabled {{ background-color: #bdc3c7; cursor: not-allowed; }}
                #message {{ color: red; font-size: 0.85em; margin-bottom: 10px; min-height: 1.2em; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>New Password</h2>
                <div id="message"></div>
                <form id="resetForm" action="/reset-password-confirm-html" method="post">
                    <input type="hidden" name="token" value="{token}">

                    <input type="password" id="pass" name="new_password" 
                           placeholder="New password (min. 6 chars)" required minlength="6">

                    <input type="password" id="confirm_pass" 
                           placeholder="Confirm password" required>

                    <button type="submit" id="submitBtn" disabled>Update Password</button>
                </form>
            </div>

            <script>
                const pass = document.getElementById('pass');
                const confirm = document.getElementById('confirm_pass');
                const btn = document.getElementById('submitBtn');
                const msg = document.getElementById('message');

                function validate() {{
                    if (pass.value.length >= 6 && pass.value === confirm.value) {{
                        btn.disabled = false;
                        msg.innerText = "";
                    }} else {{
                        btn.disabled = true;
                        if (confirm.value.length > 0 && pass.value !== confirm.value) {{
                            msg.innerText = "Passwords do not match";
                        }} else {{
                            msg.innerText = "";
                        }}
                    }}
                }}

                pass.oninput = validate;
                confirm.oninput = validate;
            </script>
        </body>
    </html>
    """
