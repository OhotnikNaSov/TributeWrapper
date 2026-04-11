"""
Модуль для отправки уведомлений об ошибках в Discord
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any, Optional


class DiscordNotifier:
    """Отправляет уведомления об ошибках донатов в Discord"""

    def __init__(self, webhook_url: str, logger):
        """
        Инициализация Discord уведомлений

        Args:
            webhook_url: URL Discord webhook
            logger: Объект логгера
        """
        self.webhook_url = webhook_url
        self.logger = logger
        self.enabled = bool(webhook_url and webhook_url.strip())

        if self.enabled:
            self.logger.info(f"✅ Discord уведомления включены")
        else:
            self.logger.info(f"⚠️  Discord уведомления отключены (webhook_url не указан)")

    def send_error_notification(
        self,
        player_name: Optional[str],
        amount: int,
        currency: str,
        game_currency: int,
        error_reason: str,
        rcon_response: Optional[str] = None,
        trb_user_id: Optional[str] = None,
        telegram_user_id: Optional[str] = None,
        donation_id: Optional[str] = None
    ):
        """
        Отправляет уведомление об ошибке в Discord

        Args:
            player_name: Имя игрока (если удалось извлечь)
            amount: Сумма в копейках/центах
            currency: Валюта (RUB, USD, EUR, UAH)
            game_currency: Конвертированная игровая валюта (Рины)
            error_reason: Причина ошибки
            rcon_response: Ответ от RCON сервера (если был)
            trb_user_id: Единый идентификатор пользователя Tribute (trb_user_id)
            telegram_user_id: Telegram ID донатера
            donation_id: ID доната
        """
        if not self.enabled:
            self.logger.debug("Discord уведомления отключены, пропускаем")
            return

        try:
            # Форматируем сумму в нормальный вид
            real_amount = amount / 100

            # Формируем embed
            embed = {
                "title": "❌ Ошибка обработки доната",
                "color": 15158332,  # Красный цвет
                "timestamp": datetime.utcnow().isoformat(),
                "fields": []
            }

            # Основная информация
            embed["fields"].append({
                "name": "💰 Сумма доната",
                "value": f"{real_amount} {currency.upper()} ||({amount} копеек/центов)||",
                "inline": True
            })

            embed["fields"].append({
                "name": "🎮 Игровая валюта",
                "value": f"{game_currency} Рин",
                "inline": True
            })

            # Пустое поле для переноса строки
            embed["fields"].append({
                "name": "\u200b",
                "value": "\u200b",
                "inline": False
            })

            # Игрок
            if player_name:
                embed["fields"].append({
                    "name": "👤 Игрок",
                    "value": player_name,
                    "inline": True
                })
            else:
                embed["fields"].append({
                    "name": "👤 Игрок",
                    "value": "❌ Не указан в сообщении",
                    "inline": True
                })

            # TRB User ID и Telegram ID
            user_info = []
            if trb_user_id:
                user_info.append(f"TRB User ID: `{trb_user_id}`")
            if telegram_user_id:
                user_info.append(f"Telegram: `{telegram_user_id}`")
            if donation_id:
                user_info.append(f"Donation: `{donation_id}`")

            if user_info:
                embed["fields"].append({
                    "name": "🆔 Идентификаторы",
                    "value": "\n".join(user_info),
                    "inline": True
                })

            # Пустое поле для переноса строки
            embed["fields"].append({
                "name": "\u200b",
                "value": "\u200b",
                "inline": False
            })

            # Причина ошибки
            embed["fields"].append({
                "name": "⚠️ Причина ошибки",
                "value": f"```{error_reason}```",
                "inline": False
            })

            # RCON ответ
            if rcon_response is None:
                # None = реальный сбой подключения (exception)
                embed["fields"].append({
                    "name": "🎮 Ответ RCON сервера",
                    "value": "❌ Сбой подключения к RCON серверу",
                    "inline": False
                })
            elif rcon_response == "":
                # Пустой ответ = команда выполнилась, но сервер ничего не вернул
                embed["fields"].append({
                    "name": "🎮 Ответ RCON сервера",
                    "value": "⚠️ Пустой ответ (команда выполнена, но сервер ничего не вернул)\n```\n(пусто)\n```",
                    "inline": False
                })
            else:
                # Есть ответ от сервера (но паттерн успеха не найден)
                # Обрезаем если слишком длинный
                if len(rcon_response) > 500:
                    rcon_response = rcon_response[:500] + "..."

                embed["fields"].append({
                    "name": "🎮 Ответ RCON сервера",
                    "value": f"```{rcon_response}```",
                    "inline": False
                })

            # Footer
            embed["footer"] = {
                "text": "Tribute Webhook Server | Требуется ручная проверка"
            }

            # Формируем payload для Discord
            payload = {
                "embeds": [embed]
            }

            # Отправляем в Discord
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )

            if response.status_code in [200, 204]:
                self.logger.debug("✅ Уведомление отправлено в Discord")
            else:
                self.logger.error(f"❌ Ошибка отправки в Discord: {response.status_code} - {response.text}")

        except Exception as e:
            self.logger.error(f"❌ Исключение при отправке в Discord: {e}")
