import asyncio
import os
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from pytz import timezone

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Константы
MOSCOW_TZ = timezone('Europe/Moscow')

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
NOTIFY_MINUTES_BEFORE = int(os.getenv('NOTIFY_MINUTES_BEFORE', 30))

# Проверка обязательных переменных
if not TOKEN or not CHAT_ID:
    logger.error("Не заданы TOKEN или CHAT_ID в .env!")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализация планировщика
scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)

# Соответствие русских дней недели cron-формату
DAY_MAP = {
    'пн': 'mon',
    'вт': 'tue',
    'ср': 'wed',
    'чт': 'thu',
    'пт': 'fri',
    'сб': 'sat',
    'вс': 'sun'
}

async def send_queue_message(subject: str):
    """Отправка сообщения в указанный чат"""
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f'🔔 Открыта очередь на {subject}'
        )
        logger.info(f'Сообщение отправлено: "{subject}"')
    except Exception as e:
        logger.error(f'Ошибка при отправке сообщения: {e}')

def setup_scheduler():
    """Настройка расписания из файла"""
    try:
        with open('data.txt', 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                logger.debug(f"Обработка строки {line_number}: {line}")

                parts = line.split(',')
                if len(parts) != 3:
                    logger.error(f"Строка {line_number}: Некорректный формат. Ожидается: день,время,предмет")
                    continue

                day_str, time_str, subject = map(str.strip, parts)
                day_str = day_str.lower()

                if day_str not in DAY_MAP:
                    logger.error(f"Строка {line_number}: Неизвестный день недели '{day_str}'")
                    continue

                try:
                    hour, minute = map(int, time_str.split(':'))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        raise ValueError
                except (ValueError, IndexError):
                    logger.error(f"Строка {line_number}: Некорректное время '{time_str}'")
                    continue

                # Рассчет времени уведомления
                target_time = datetime.now(MOSCOW_TZ).replace(
                    hour=hour,
                    minute=minute,
                    second=5,
                    microsecond=0
                )
                notify_time = target_time - timedelta(minutes=NOTIFY_MINUTES_BEFORE)

                scheduler.add_job(
                    send_queue_message,
                    'cron',
                    day_of_week=DAY_MAP[day_str],
                    hour=notify_time.hour,
                    minute=notify_time.minute,
                    args=[subject]
                )
                logger.info(f"Добавлено: {subject} - {DAY_MAP[day_str]} {notify_time.strftime('%H:%M')} MSK")

    except FileNotFoundError:
        logger.error("Файл data.txt не найден")
        exit(1)

async def on_startup():
    """Действия при запуске бота"""
    logger.info("Бот запущен")

    # Тестовое уведомление через 10 секунд
    scheduler.add_job(
        send_queue_message,
        'date',
        run_date=datetime.now(MOSCOW_TZ) + timedelta(seconds=10),
        args=["🚀 Тестовое уведомление"]
    )

    setup_scheduler()
    scheduler.start()
    logger.info(f"Планировщик запущен. Всего задач: {len(scheduler.get_jobs())}")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"Необработанная ошибка: {e}")