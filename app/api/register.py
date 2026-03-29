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
from app.models.user import User  # Импорт вашей модели
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

    # 2. Создаем НЕАКТИВНОГО пользователя
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role="USER",
        is_active=False
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # 3. Генерируем токен и отправляем письмо в фоне (не тормозим ответ API)
    token = create_verification_token(user_data.email)
    background_tasks.add_task(send_verification_email, user_data.email, token)

    return new_user


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email_page(token: str, db: AsyncSession = Depends(get_users_db)):
    try:
        # Декодируем токен
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")

        if email is None:
            return render_error_page("Неверный токен активации.")

        # Ищем пользователя
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return render_error_page("Пользователь не найден.")

        if user.is_active:
            return render_success_page("Ваш аккаунт уже был активирован ранее!")

        # Активируем
        user.is_active = True
        await db.commit()

        return render_success_page("Аккаунт успешно активирован! Теперь вы можете войти в систему.")

    except JWTError:
        return render_error_page("Ссылка для активации устарела или недействительна.")


# Вспомогательные функции для красоты
def render_success_page(message: str):
    return f"""
    <html>
        <head>
            <title>OpenChemDB - Успех</title>
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
                <h2>Готово!</h2>
                <p>{message}</p>
                <br>
                <p style="font-size: 0.9em; color: #888;">Можете закрыть это окно.</p>
            </div>
        </body>
    </html>
    """


def render_error_page(error_message: str):
    return f"""
    <html>
        <head>
            <title>OpenChemDB - Ошибка</title>
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
                <h2>Ошибка активации</h2>
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
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # В целях безопасности не говорим, есть такой email или нет
    if user:
        # Генерируем токен (используем тот же метод, но уменьшаем exp)
        token = create_verification_token(user.email, expires_delta=timedelta(hours=1))
        background_tasks.add_task(send_reset_password_email, user.email, token)

    return {"message": "Если такой email зарегистрирован, письмо со ссылкой отправлено."}


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
        raise HTTPException(status_code=400, detail="Токен недействителен или истек")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Хешируем новый пароль и сохраняем
    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()

    return {"message": "Пароль успешно изменен. Теперь вы можете войти."}


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
            return "<h3>Ошибка: Пользователь не найден.</h3>"

        # Хешируем и сохраняем
        user.hashed_password = get_password_hash(new_password)
        await db.commit()

        return """
        <div style="text-align:center; padding-top:50px; font-family:sans-serif;">
            <h2 style="color: green;">Пароль успешно изменен!</h2>
            <p>Теперь вы можете войти в систему под своим новым паролем.</p>
        </div>
        """
    except JWTError:
        return "<h3>Ошибка: Ссылка устарела или неверна.</h3>"


@router.get("/reset-password-page", response_class=HTMLResponse)
async def reset_password_page(token: str):
    return f"""
    <html>
        <head>
            <title>OpenChemDB - Сброс пароля</title>
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
                <h2>Новый пароль</h2>
                <div id="message"></div>
                <form id="resetForm" action="/reset-password-confirm-html" method="post">
                    <input type="hidden" name="token" value="{token}">

                    <input type="password" id="pass" name="new_password" 
                           placeholder="Новый пароль (мин. 6 симв.)" required minlength="6">

                    <input type="password" id="confirm_pass" 
                           placeholder="Повторите пароль" required>

                    <button type="submit" id="submitBtn" disabled>Обновить пароль</button>
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
                            msg.innerText = "Пароли не совпадают";
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
