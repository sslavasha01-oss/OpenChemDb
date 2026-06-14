from fastapi import FastAPI, Request, APIRouter, HTTPException, status
import hmac
import hashlib

from app.core.settings import settings

router = APIRouter(tags=["webhooks"])

@router.post("/bmac/webhook")
async def receive_webhook(request: Request):
    # 1. Забираем заголовок с сигнатурой
    signature = request.headers.get("x-signature-sha256")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature"
        )

    # 2. Читаем тело запроса как СЫРЫЕ БАЙТЫ (это критично для правильного хэша)
    raw_body = await request.body()

    # 3. Вычисляем наш собственный хэш на основе сырого тела и нашего секрета
    computed_signature = hmac.new(
        key=settings.BMAC_SIGNING_SECRET.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()

    # 4. Безопасно сравниваем подписи (защита от атак по времени / timing attacks)
    if not hmac.compare_digest(computed_signature, signature):
        print("КРИТИЧЕСКАЯ ОШИБКА: Подписи не совпали! Запрос фейковый.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature"
        )

    try:
        # 1. Читаем JSON, который прислал вебхук
        payload = await request.json()

        print("\n" + "=" * 50)
        print(" СЕРВЕР ПОЛУЧИЛ НОВЫЙ ВЕБХУК!")
        print("=" * 50)

        # 2. Выводим данные в консоль
        import pprint
        pprint.pprint(payload)

        print("=" * 50 + "\n")
        print("ЗАГОЛОВКИ ЗАПРОСА:")
        print(dict(request.headers))

    except Exception as e:
        # На случай, если пришел не JSON, а что-то другое (например, обычный текст)
        raw_body = await request.body()
        print(f"\n Ошибка чтения JSON: {e}")
        print(f"Сырые данные (raw body): {raw_body.decode('utf-8', errors='ignore')}\n")

    # 3. Обязательно возвращаем успешный статус платежке
    return {"status": "success", "message": "Webhook received"}