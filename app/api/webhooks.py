import hashlib
import hmac
import traceback
from datetime import datetime

from fastapi import Request, APIRouter, HTTPException, status, Depends
from pydantic import EmailStr, BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_users_db
from app.core.settings import settings
from app.models.user import User, Webhook, TariffPlan

router = APIRouter(tags=["webhooks"])

@router.post("/bmac/webhook")
async def receive_webhook(request: Request,
                          db: AsyncSession = Depends(get_users_db)):
    # 1. Проверка сигнатуры безопасности (это единственное, что жестко отсекаем)
    signature = request.headers.get("x-signature-sha256")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature"
        )

    raw_body = await request.body()
    computed_signature = hmac.new(
        key=settings.BMAC_SIGNING_SECRET.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_signature, signature):
        print("CRITICAL ERROR: Webhook signature mismatch!")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature"
        )

    # Инициализируем дефолтные значения на случай, если JSON окажется битым или нетипичным
    payload = {}
    event_type = "unknown"
    supporter_email = "not_provided"
    supporter_name = None
    amount = 0.0
    currency = "USD"
    current_period_start = None
    current_period_end = None
    user_id = None

    # 2. Пытаемся распарсить JSON, но в случае ошибки — не падаем, а сохраняем сырые байты
    try:
        payload = await request.json()
    except Exception as e:
        print(f"JSON parsing error: {e}")
        # Сохраняем структуру, чтобы в базу записалось хоть что-то
        payload = {"_error": "Invalid JSON", "_raw_body_fallback": raw_body.decode('utf-8', errors='ignore')}
        event_type = "invalid_json"

    # 3. Безопасно вытаскиваем данные через .get(), чтобы не поймать KeyError
    if event_type != "invalid_json":
        data = payload.get("data", payload)
        event_type = payload.get("type", "unknown")

        # Проверяем возможные варианты ключей почты
        supporter_email = data.get("supporter_email") or data.get("payer_email") or "not_provided"
        supporter_name = data.get("supporter_name")

        try:
            amount = float(data.get("amount", 0))
        except (ValueError, TypeError):
            amount = 0.0

        currency = data.get("currency", "USD")

        # Безопасный парсинг дат
        start_ts = data.get("current_period_start")
        end_ts = data.get("current_period_end")
        try:
            current_period_start = datetime.utcfromtimestamp(int(start_ts)) if start_ts else None
            current_period_end = datetime.utcfromtimestamp(int(end_ts)) if end_ts else None
        except Exception as e:
            print(f"Timestamp parsing error: {e}")

    # 4. Пробуем найти пользователя, ТОЛЬКО если у нас есть вменяемый email
    if supporter_email and supporter_email != "not_provided":
        try:
            query = select(User).where(
                or_(
                    User.email == supporter_email,
                    User.billing_email == supporter_email
                )
            )
            result = await db.execute(query)
            user = result.scalars().first()
            if user:
                user_id = user.id
        except Exception as e:
            print(f"Database user lookup error: {e}")
            user = None
    else:
        user = None

    # 5. Железно сохраняем вебхук в БД
    try:
        webhook_record = Webhook(
            event_type=event_type,
            supporter_email=supporter_email,
            supporter_name=supporter_name,
            amount=amount,
            currency=currency,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            raw_payload=payload,
            user_id=user_id  # Будет корректный ID или NULL
        )
        db.add(webhook_record)

        # Делаем flush, чтобы изменения вебхука попали в транзакцию, но не фиксируем окончательно
        await db.flush()
    except Exception as e:
        # Супер-фолбек: если даже создание модели упало (например, структуры БД не совпали),
        # пишем критический лог. Но платежке отдаем 200, чтобы она не спамила вебхуками.
        print(f"CRITICAL FAULT saving webhook to DB: {e}")
        traceback.print_exc()
        return {"status": "error_logged", "message": "Failed to save webhook but request accepted"}

    # 6. Если сматчили и событие верное — обновляем тариф пользователя
    if user:
        try:
            # Сценарий А: Подписка стартовала (первая оплата)
            if event_type == "membership.started":
                user.tariff_plan = TariffPlan.PAID_1.value
                if current_period_end:
                    user.subscription_period_end = current_period_end
                print(f"User {user.username} successfully upgraded to PAID_1 plan")

            # Сценарий Б: Подписка обновилась (продление, отмена автопродления и т.д.)
            elif event_type == "membership.updated":
                cancel_at_period_end = data.get("cancel_at_period_end") == "true" or data.get(
                    "cancel_at_period_end") is True

                if cancel_at_period_end:
                    # Пользователь отменил автопродление.
                    # Мы НЕ снимаем тариф, просто обновляем финальную дату, до которой он допущен
                    if current_period_end:
                        user.subscription_period_end = current_period_end
                    print(f"User {user.username} cancelled auto-renewal. Access until: {current_period_end}")
                else:
                    # Это обычное обновление (например, успешное автопродление на следующий месяц)
                    # На всякий случай продлеваем ему дату окончания
                    user.tariff_plan = TariffPlan.PAID_1.value
                    if current_period_end:
                        user.subscription_period_end = current_period_end
                    print(f"Membership for user {user.username} renewed/updated until {current_period_end}")
        except Exception as e:
            print(f"Failed to update subscription for user {user.id}: {e}")

    # Финальный коммит изменений (и вебхук, и апдейт юзера сохранятся одной транзакцией)
    await db.commit()

    return {"status": "success", "message": "Webhook processed"}


class LinkBillingEmailRequest(BaseModel):
    email: EmailStr


@router.post("/billing/link-manual", status_code=status.HTTP_200_OK)
async def link_manual_webhook(
        request_data: LinkBillingEmailRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    target_email = request_data.email.strip().lower()

    try:
        # 1. Ищем все вебхуки с этим email, у которых user_id еще НЕ выставлен (NULL)
        # Сортируем по ID или по дате по возрастанию, чтобы самый свежий вебхук обрабатывался последним
        query = (
            select(Webhook)
            .where(
                Webhook.supporter_email == target_email,
                Webhook.user_id.is_(None)
            )
            .order_by(Webhook.id.asc())
        )
        result = await db.execute(query)
        webhooks = result.scalars().all()

        # 2. Если вебхуков не нашлось, возвращаем ошибку 404 (или 400 на ваше усмотрение)
        if not webhooks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment info for this email was not found. The payment might still be processing or has already been linked."
            )

        # Переменные для отслеживания финального состояния подписки
        latest_period_end = None
        has_active_membership = False
        is_cancelled = False

        # 3. Проходим по найденным вебхукам и симулируем логику из вебхук-эндпоинта
        for wh in webhooks:
            # Привязываем вебхук к текущему авторизованному пользователю
            wh.user_id = current_user.id

            # Сохраняем самую последнюю дату окончания периода
            if wh.current_period_end:
                latest_period_end = wh.current_period_end

            # Если было хотя бы одно событие старта или апдейта —
            # значит, факт оплаты/наличия подписки в этой цепочке точно зафиксирован
            if wh.event_type in ("membership.started", "membership.updated"):
                has_active_membership = True

            # 4. Обновляем данные пользователя
        current_user.billing_email = target_email

        # Если в истории есть валидные вебхуки подписки, ВСЕГДА включаем PAID_1.
        # (Даже если автопродление отменено, доступ должен быть активен до наступления latest_period_end)
        if has_active_membership:
            current_user.tariff_plan = TariffPlan.PAID_1.value
            print(f"User {current_user.username} manually upgraded to PAID_1 plan")

        if latest_period_end:
            current_user.subscription_period_end = latest_period_end

        # 5. Сохраняем все изменения одной транзакцией
        await db.commit()

        print(f"Successfully linked {len(webhooks)} events manually for user {current_user.username}")

        return {
            "status": "success",
            "message": f"Subscription successfully updated. Linked events: {len(webhooks)}. Billing email set.",
            "subscription_period_end": latest_period_end.isoformat() if latest_period_end else None
        }

    except HTTPException:
        # Пробрасываем HTTP исключения (например, 404), чтобы они вернулись клиенту напрямую
        raise
    except Exception as e:
        # В случае непредвиденной ошибки откатываем изменения
        await db.rollback()
        print(f"Error during manual email linking ({target_email}) for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing your request."
        )