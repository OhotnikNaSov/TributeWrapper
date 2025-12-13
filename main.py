"""
Tribute Webhook Server
Обрабатывает webhook'и от Tribute и начисляет валюту в Minecraft
"""

import hmac
import hashlib
import json
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
import uvicorn

from config_loader import load_config
from database import DatabaseManager
from rcon_manager import RconManager
from logger import Logger

# Загружаем конфигурацию
config = load_config()
logger = Logger(config['server']['debug'])

# Инициализируем FastAPI приложение
app = FastAPI(title="Tribute Webhook Server", version="1.0.0")

# Инициализируем менеджер баз данных (для логирования Tribute)
db_manager = DatabaseManager(config, logger)

# Инициализируем RCON менеджер (для начисления валюты)
rcon_manager = RconManager(config, logger)


def verify_signature(request_body: bytes, signature: str, api_key: str) -> bool:
    """
    Проверяет HMAC-SHA256 подпись webhook запроса
    
    Args:
        request_body: Тело запроса в байтах
        signature: Подпись из заголовка trbt-signature
        api_key: API ключ от Tribute
    
    Returns:
        True если подпись валидна, иначе False
    """
    logger.debug("🔐 Проверка подписи webhook")
    
    # Вычисляем HMAC-SHA256
    expected_signature = hmac.new(
        api_key.encode('utf-8'),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    is_valid = hmac.compare_digest(signature, expected_signature)
    
    if is_valid:
        logger.debug("✅ Подпись валидна")
    else:
        logger.error(f"❌ Подпись невалидна! Получена: {signature[:16]}..., Ожидалась: {expected_signature[:16]}...")
    
    return is_valid


def convert_to_game_currency(amount: int, currency: str) -> int:
    """
    Конвертирует реальную валюту в игровую (Рины)
    
    Args:
        amount: Сумма в копейках (для rub) или центах (для usd/eur)
        currency: Код валюты (RUB, EUR, USD и т.д.)
    
    Returns:
        Количество игровой валюты (Рин)
    """
    logger.debug(f"💱 Конвертация валюты: {amount} {currency}")
    
    # Tribute передает amount в минимальных единицах (копейки, центы)
    # НЕ делим на 100, работаем напрямую с копейками/центами
    
    currency_upper = currency.upper()
    rate = config['currency_rates'].get(currency_upper, 0)
    
    if rate == 0:
        logger.error(f"❌ Неизвестная валюта: {currency}. Используется rate=0")
        return 0
    
    # Прямое умножение: копейки/центы * rate
    game_currency = int(amount * rate)
    
    # Для красивого лога показываем в основной валюте
    real_amount = amount / 100
    logger.debug(f"💰 {amount} копеек/центов ({real_amount} {currency_upper}) × {rate} = {game_currency} Рин")
    
    return game_currency


def extract_player_name(message: str) -> str:
    """
    Извлекает имя игрока из сообщения доната
    
    Args:
        message: Сообщение от донатера
    
    Returns:
        Имя игрока или пустая строка
    """
    logger.debug(f"🔍 Извлечение имени игрока из сообщения: '{message}'")
    
    # Убираем пробелы и берем первое слово
    # Можно настроить под свой формат
    player_name = message.strip().split()[0] if message else ""
    
    logger.debug(f"👤 Найдено имя игрока: '{player_name}'")
    return player_name


def process_new_donation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обрабатывает новый донат (new_donation)
    
    Args:
        payload: Данные webhook'а
    
    Returns:
        Результат обработки
    """
    logger.info("=" * 60)
    logger.info("💳 ОБРАБОТКА НОВОГО ДОНАТА")
    logger.info("=" * 60)
    
    # Извлекаем данные
    donation_id = payload.get('donation_request_id')
    message = payload.get('message', '')
    amount = payload.get('amount', 0)
    currency = payload.get('currency', '')
    user_id = payload.get('user_id')
    telegram_user_id = payload.get('telegram_user_id')
    
    logger.debug(f"📋 ID доната: {donation_id}")
    logger.debug(f"📋 User ID: {user_id}")
    logger.debug(f"📋 Telegram ID: {telegram_user_id}")
    logger.debug(f"📋 Сумма: {amount} {currency}")
    logger.debug(f"📋 Сообщение: '{message}'")
    
    # Извлекаем имя игрока
    player_name = extract_player_name(message)
    
    if not player_name:
        logger.error("❌ Не удалось извлечь имя игрока из сообщения")
        result = {
            'status': 'error',
            'reason': 'Не указано имя игрока в сообщении',
            'player_name': None,
            'game_currency': 0
        }
    else:
        # Конвертируем валюту
        game_currency = convert_to_game_currency(amount, currency)
        
        logger.info(f"🎮 Начисление {game_currency} Рин игроку {player_name}")

        # Пробуем начислить валюту через RCON
        try:
            success = rcon_manager.add_currency_to_player(player_name, game_currency)

            if success:
                logger.info(f"✅ Успешно начислено {game_currency} Рин игроку {player_name}")
                result = {
                    'status': 'success',
                    'reason': 'Валюта успешно начислена через RCON',
                    'player_name': player_name,
                    'game_currency': game_currency
                }
            else:
                logger.error(f"❌ Ошибка начисления валюты игроку {player_name}")
                result = {
                    'status': 'error',
                    'reason': 'Ошибка выполнения RCON команды',
                    'player_name': player_name,
                    'game_currency': game_currency
                }
        except Exception as e:
            logger.error(f"❌ Исключение при начислении валюты: {e}")
            result = {
                'status': 'error',
                'reason': f'Исключение: {str(e)}',
                'player_name': player_name,
                'game_currency': game_currency
            }
    
    # Сохраняем информацию о донате в БД Tribute
    try:
        db_manager.save_tribute_webhook(
            webhook_type='new_donation',
            payload=payload,
            status=result['status'],
            player_name=result.get('player_name'),
            game_currency=result.get('game_currency', 0),
            error_message=result.get('reason') if result['status'] == 'error' else None
        )
        logger.debug("💾 Webhook сохранен в БД Tribute")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения в БД Tribute: {e}")
    
    return result


def process_other_webhook(webhook_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обрабатывает остальные типы webhook'ов (не донаты)
    
    Args:
        webhook_type: Тип webhook'а
        payload: Данные webhook'а
    
    Returns:
        Результат обработки
    """
    logger.info("=" * 60)
    logger.info(f"📬 ПОЛУЧЕН WEBHOOK: {webhook_type}")
    logger.info("=" * 60)
    logger.debug(f"📦 Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    
    # Сохраняем в БД Tribute
    try:
        db_manager.save_tribute_webhook(
            webhook_type=webhook_type,
            payload=payload,
            status='received',
            player_name=None,
            game_currency=0,
            error_message=None
        )
        logger.debug("💾 Webhook сохранен в БД Tribute")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения в БД Tribute: {e}")
    
    return {
        'status': 'received',
        'reason': f'Webhook {webhook_type} получен и сохранен'
    }


@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Основной endpoint для приема webhook'ов от Tribute
    """
    logger.info("\n" + "🌟" * 15)
    logger.info("📨 ПОЛУЧЕН НОВЫЙ WEBHOOK ЗАПРОС")
    
    # Читаем тело запроса
    body = await request.body()
    logger.debug(f"📦 Размер тела запроса: {len(body)} байт")
    
    # Получаем подпись из заголовка
    signature = request.headers.get('trbt-signature', '')
    logger.debug(f"🔑 Получена подпись: {signature[:32]}..." if signature else "⚠️ Подпись отсутствует!")
    
    # Проверяем подпись
    if not verify_signature(body, signature, config['tribute']['api_key']):
        logger.error("🚫 WEBHOOK ОТКЛОНЕН: Неверная подпись")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Парсим JSON
    try:
        data = json.loads(body)
        logger.debug(f"📋 Распарсен JSON: {json.dumps(data, ensure_ascii=False, indent=2)}")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Ошибка парсинга JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON"
        )
    
    # Получаем тип webhook'а
    webhook_type = data.get('name', '')
    payload = data.get('payload', {})
    
    logger.info(f"📌 Тип webhook: {webhook_type}")
    
    # Обрабатываем в зависимости от типа
    if webhook_type == 'new_donation':
        result = process_new_donation(payload)
    else:
        result = process_other_webhook(webhook_type, payload)
    
    logger.info("=" * 60)
    logger.info(f"✅ ОБРАБОТКА ЗАВЕРШЕНА: {result['status']}")
    logger.info("=" * 60 + "\n")
    
    return JSONResponse(content=result, status_code=200)


@app.get("/")
async def root():
    """Корневой endpoint для проверки работы сервера"""
    return {
        "status": "running",
        "service": "Tribute Webhook Server",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    logger.info("🚀 Запуск Tribute Webhook Server")
    logger.info(f"🌐 Host: {config['server']['host']}")
    logger.info(f"🔌 Port: {config['server']['port']}")
    logger.info(f"🐛 Debug: {config['server']['debug']}")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host=config['server']['host'],
        port=config['server']['port'],
        log_level="debug" if config['server']['debug'] else "info"
    )
