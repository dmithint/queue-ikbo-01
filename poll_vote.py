import os
import asyncio
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_NAME = os.getenv("SESSION_NAME", "poll_session")
CHECK_CHAT_ID = int(os.getenv("CHECK_CHAT_ID"))

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)


@client.on(events.NewMessage(chats=[CHECK_CHAT_ID]))
async def handler(event):
    if not event.poll:
        return

    try:
        poll = event.poll
        logger.info(f"Найден опрос: {poll.question}")

        await asyncio.sleep(60)

        option = poll.answers[0].option
        await client.vote(event.message, [option])

        logger.info(f"Проголосовали в опросе: {poll.question}")

    except Exception as e:
        logger.error(f"Ошибка при голосовании: {e}")


async def main():
    logger.info("Запуск клиента...")
    async with client:
        await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
