import asyncio
import os
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from pytz import timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

MOSCOW_TZ = timezone('Europe/Moscow')

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
QUEUE_CHAT_ID = os.getenv('QUEUE_CHAT_ID')
CHECK_CHAT_ID = os.getenv('CHECK_CHAT_ID')
import asyncio
import os
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from pytz import timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

MOSCOW_TZ = timezone('Europe/Moscow')

load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
QUEUE_CHAT_ID = os.getenv('QUEUE_CHAT_ID')
CHECK_CHAT_ID = os.getenv('CHECK_CHAT_ID')
QUEUE_THREAD_ID = os.getenv('QUEUE_THREAD_ID')
CHECK_THREAD_ID = os.getenv('CHECK_THREAD_ID')
NOTIFY_MINUTES_BEFORE = int(os.getenv('NOTIFY_MINUTES_BEFORE', 30))

if not TOKEN or not QUEUE_CHAT_ID or not CHECK_CHAT_ID:
    logger.error("Не заданы обязательные переменные окружения!")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)

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
    """Отправка сообщения о начале очереди"""
    try:
        await bot.send_message(
            chat_id=QUEUE_CHAT_ID,
            message_thread_id=int(QUEUE_THREAD_ID) if QUEUE_THREAD_ID else None,
            text=f'🔔 Открыта очередь на {subject}'
        )
        logger.info(f'Очередь отправлена: {subject}')
    except Exception as e:
        logger.error(f'Ошибка при отправке очереди: {e}')


async def send_poll_message(subject: str):
    """Отправка опроса о посещении"""
    try:
        await bot.send_poll(
            chat_id=CHECK_CHAT_ID,
            message_thread_id=int(CHECK_THREAD_ID) if CHECK_THREAD_ID else None,
            question=f'Лекция: {subject}',
            options=['На месте', 'На месте'],
            is_anonymous=False,
            allows_multiple_answers=False
        )
        logger.info(f'Опрос отправлен: {subject}')
    except Exception as e:
        logger.error(f'Ошибка при отправке опроса: {e}')


def add_jobs_from_file(file_name: str, func, func_type: str, chat_id: str, minutes_before: int, odd: bool):
    """
    Загрузка задач из файла.
    odd=True  -> задачи ставятся на ЧЁТНЫЕ недели (2-52/2)
    odd=False -> задачи ставятся на НЕЧЁТНЫЕ недели (1-53/2)
    """
    if odd:
        week_expr = "2-52/2"
        week_label = "четная"
    else:
        week_expr = "1-53/2"
        week_label = "нечетная"

    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split(',')
                if len(parts) != 3:
                    logger.error(f"{file_name} строка {line_number}: неверный формат (день,время,предмет)")
                    continue

                day_str, time_str, subject = map(str.strip, parts)
                day_str = day_str.lower()

                if day_str not in DAY_MAP:
                    logger.error(f"{file_name} строка {line_number}: неизвестный день '{day_str}'")
                    continue

                try:
                    hour, minute = map(int, time_str.split(':'))
                except Exception:
                    logger.error(f"{file_name} строка {line_number}: некорректное время '{time_str}'")
                    continue

                # время уведомления
                notify_hour = hour
                notify_minute = minute
                if minutes_before > 0:
                    dt = datetime(2000, 1, 1, hour, minute) - timedelta(minutes=minutes_before)
                    notify_hour, notify_minute = dt.hour, dt.minute

                scheduler.add_job(
                    func,
                    'cron',
                    week=week_expr,
                    day_of_week=DAY_MAP[day_str],
                    hour=notify_hour,
                    minute=notify_minute,
                    args=[subject + f" ({time_str})"]
                )

                logger.info(
                    f"Добавлен {func_type} ({week_label}): {subject} - {DAY_MAP[day_str]} "
                    f"в {notify_hour:02d}:{notify_minute:02d} -> {chat_id}"
                )

    except FileNotFoundError:
        logger.warning(f"Файл {file_name} не найден, пропускаем {func_type}")


def setup_scheduler():
    """Настройка задач из всех файлов"""
    configs = [
        {
            'files': {
                'odd': 'queue_lessons_odd.txt',
                'even': 'queue_lessons_even.txt'
            },
            'function': send_queue_message,
            'type': 'очередь',
            'chat_id': QUEUE_CHAT_ID,
            'minutes_before': 30
        },
        {
            'files': {
                'odd': 'check_lessons_odd.txt',
                'even': 'check_lessons_even.txt'
            },
            'function': send_poll_message,
            'type': 'опрос',
            'chat_id': CHECK_CHAT_ID,
            'minutes_before': 0
        }
    ]

    for config in configs:
        add_jobs_from_file(
            config['files']['odd'],
            config['function'],
            config['type'],
            config['chat_id'],
            config['minutes_before'],
            odd=True
        )
        add_jobs_from_file(
            config['files']['even'],
            config['function'],
            config['type'],
            config['chat_id'],
            config['minutes_before'],
            odd=False
        )


async def on_startup():
    logger.info("Бот запускается...")
    setup_scheduler()
    scheduler.start()
    logger.info(f"Планировщик запущен. Задач: {len(scheduler.get_jobs())}")


async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.exception(f"Необработанная ошибка: {e}")
QUEUE_THREAD_ID = os.getenv('QUEUE_THREAD_ID')
CHECK_THREAD_ID = os.getenv('CHECK_THREAD_ID')
NOTIFY_MINUTES_BEFORE = int(os.getenv('NOTIFY_MINUTES_BEFORE', 30))

if not TOKEN or not QUEUE_CHAT_ID or not CHECK_CHAT_ID:
    logger.error("Не заданы обязательные переменные окружения!")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=MOSCOW_TZ)

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
    """Отправка сообщения о начале очереди"""
    try:
        await bot.send_message(
            chat_id=QUEUE_CHAT_ID,
            message_thread_id=int(QUEUE_THREAD_ID) if QUEUE_THREAD_ID else None,
            text=f'🔔 Открыта очередь на {subject}'
        )
        logger.info(f'Очередь отправлена: {subject}')
    except Exception as e:
        logger.error(f'Ошибка при отправке очереди: {e}')


async def send_poll_message(subject: str):
    """Отправка опроса о посещении"""
    try:
        await bot.send_poll(
            chat_id=CHECK_CHAT_ID,
            message_thread_id=int(CHECK_THREAD_ID) if CHECK_THREAD_ID else None,
            question=f'Лекция: {subject}',
            options=['На месте', 'На месте'],
            is_anonymous=False,
            allows_multiple_answers=False
        )
        logger.info(f'Опрос отправлен: {subject}')
    except Exception as e:
        logger.error(f'Ошибка при отправке опроса: {e}')


def add_jobs_from_file(file_name: str, func, func_type: str, chat_id: str, minutes_before: int, odd: bool):
    """
    Загрузка задач из файла.
    odd=True  -> задачи ставятся на ЧЁТНЫЕ недели (2-52/2)
    odd=False -> задачи ставятся на НЕЧЁТНЫЕ недели (1-53/2)
    """
    if odd:
        week_expr = "2-52/2"
        week_label = "четная"
    else:
        week_expr = "1-53/2"
        week_label = "нечетная"

    try:
        with open(file_name, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split(',')
                if len(parts) != 3:
                    logger.error(f"{file_name} строка {line_number}: неверный формат (день,время,предмет)")
                    continue

                day_str, time_str, subject = map(str.strip, parts)
                day_str = day_str.lower()

                if day_str not in DAY_MAP:
                    logger.error(f"{file_name} строка {line_number}: неизвестный день '{day_str}'")
                    continue

                try:
                    hour, minute = map(int, time_str.split(':'))
                except Exception:
                    logger.error(f"{file_name} строка {line_number}: некорректное время '{time_str}'")
                    continue

                # время уведомления
                notify_hour = hour
                notify_minute = minute
                if minutes_before > 0:
                    dt = datetime(2000, 1, 1, hour, minute) - timedelta(minutes=minutes_before)
                    notify_hour, notify_minute = dt.hour, dt.minute

                scheduler.add_job(
                    func,
                    'cron',
                    week=week_expr,
                    day_of_week=DAY_MAP[day_str],
                    hour=notify_hour,
                    minute=notify_minute,
                    args=[subject + f" ({time_str})"]
                )

                logger.info(
                    f"Добавлен {func_type} ({week_label}): {subject} - {DAY_MAP[day_str]} "
                    f"в {notify_hour:02d}:{notify_minute:02d} -> {chat_id}"
                )

    except FileNotFoundError:
        logger.warning(f"Файл {file_name} не найден, пропускаем {func_type}")


def setup_scheduler():
    """Настройка задач из всех файлов"""
    configs = [
        {
            'files': {
                'odd': 'queue_lessons_odd.txt',
                'even': 'queue_lessons_even.txt'
            },
            'function': send_queue_message,
            'type': 'очередь',
            'chat_id': QUEUE_CHAT_ID,
            'minutes_before': 30
        },
        {
            'files': {
                'odd': 'check_lessons_odd.txt',
                'even': 'check_lessons_even.txt'
            },
            'function': send_poll_message,
            'type': 'опрос',
            'chat_id': CHECK_CHAT_ID,
            'minutes_before': 0
        }
    ]

    for config in configs:
        add_jobs_from_file(
            config['files']['odd'],
            config['function'],
            config['type'],
            config['chat_id'],
            config['minutes_before'],
            odd=True
        )
        add_jobs_from_file(
            config['files']['even'],
            config['function'],
            config['type'],
            config['chat_id'],
            config['minutes_before'],
            odd=False
        )


async def on_startup():
    logger.info("Бот запускается...")
    setup_scheduler()
    scheduler.start()
    logger.info(f"Планировщик запущен. Задач: {len(scheduler.get_jobs())}")


async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.exception(f"Необработанная ошибка: {e}")
