import asyncio
import logging
from datetime import datetime
from sqlalchemy import update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.settings import settings
from app.models.user import User

# Импортируй свои настройки и модели
# from config import settings
# from models import User, TariffPlan

# Настройка логирования, чтобы видеть результаты в консоли/логах сервера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("subscription_cron")

# Инициализируем движок БД (замени settings.DATABASE_URL на твою строку подключения)
# Например: "postgresql+asyncpg://user:pass@localhost/dbname"
engine = create_async_engine(settings.USERS_DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def check_expired_subscriptions():
    now_utc = datetime.utcnow()
    logger.info("Запуск проверки истекших подписок...")

    async with async_session() as session:
        try:
            # Массовый апдейт (Bulk Update):
            # Ищем всех пользователей, у которых тариф PAID_1, но дата окончания подписки МЕНЬШЕ текущей
            stmt = (
                update(User)
                .where(
                    User.tariff_plan == "PAID_1",  # Переводим только тех, у кого сейчас платная
                    User.subscription_period_end < now_utc
                )
                .values(
                    tariff_plan="FREE",
                    # Опционально: можно очищать дату, а можно оставить для истории.
                    # Оставим для истории, чтобы понимать, когда она закончилась.
                )
                .execution_options(synchronize_session="fetch")
            )

            result = await session.execute(stmt)
            await session.commit()

            # result.rowcount покажет, сколько строк было обновлено
            if result.rowcount > 0:
                logger.info(f"Успешно переведено на тариф FREE пользователей: {result.rowcount}")
            else:
                logger.info("Истекших подписок не найдено. Все пользователи активны.")

        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при выполнении джобы: {e}", exc_info=True)
        finally:
            await session.close()

async def main():
    await check_expired_subscriptions()
    # Закрываем пулы соединений с БД
    await engine.dispose()

if __name__ == "__main__":
    # Запуск асинхронного event loop
    asyncio.run(main())