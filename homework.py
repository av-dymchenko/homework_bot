import time
import requests
from telegram import Bot
from dotenv import load_dotenv
import os
import logging
from telegram import TelegramError

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("my_logger")

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Валидация токенов."""
    missing_tokens = []

    for token_name, token_value in [
        ('TELEGRAM_TOKEN', TELEGRAM_TOKEN),
        ('TELEGRAM_CHAT_ID', TELEGRAM_CHAT_ID),
        ('PRACTICUM_TOKEN', PRACTICUM_TOKEN)
    ]:
        if not token_value:
            missing_tokens.append(token_name)

    if missing_tokens:
        logger.critical(
            f'Токены {", ".join(missing_tokens)} отсутствуют. '
            f'Программа завершает работу.'
        )
        exit()

    return True


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug("Сообщение успешно отправлено в Telegram")
    except TelegramError as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")


def get_api_answer(timestamp):
    """Получение ответа."""
    payload = {
        'from_date': timestamp
    }
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f'ошибка во время выполнения запроса {e}')
        raise ConnectionError(
            f'ошибка во время выполнения запроса {e}'
        )

    if response.status_code != 200:
        logger.error('HTTP ошибка')
        raise requests.exceptions.HTTPError('HTTP ошибка')
    return response.json()


def check_response(response):
    """Валидация ответа."""
    if not isinstance(response, dict):
        logger.error("Ответ не является словарём")
        raise TypeError("Ответ не является словарём")
    if 'homeworks' not in response or 'current_date' not in response:
        logger.error("Нужных ключей нет в ответе")
        raise KeyError("Нужных ключей нет в ответе")
    if not isinstance(response['homeworks'], list):
        logger.error("Данные домашки не представлены в виде списка")
        raise TypeError("Данные домашки не представлены в виде списка")
    return True


def parse_status(homework):
    """Парсинг домашки."""
    if 'homework_name' not in homework:
        logger.error(
            "Отсутствует ключ 'homework_name' в данных о домашней работе"
        )
        raise KeyError(
            "Отсутствует ключ 'homework_name' в данных о домашней работе"
        )
    if 'status' not in homework:
        logger.error("Отсутствует ключ 'status' в данных о домашней работе")
        raise KeyError("Отсутствует ключ 'status' в данных о домашней работе")
    homework_name = homework['homework_name']
    status = homework['status']
    verdict = HOMEWORK_VERDICTS.get(homework['status'])
    if status not in HOMEWORK_VERDICTS:
        logger.error("Статус отсутствует в списке ожидаемых статусов")
        raise ValueError('Статус отсутствует')
    if verdict is None:
        logger.error("Нет информации о вердикте")
        raise ValueError('Нет информации')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = 1690008665
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            homework = response['homeworks'][0]
            message = parse_status(homework)
            send_message(bot, message)
        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
        finally:
            logger.debug("Ожидание перед следующей попыткой...")
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
