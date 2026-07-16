"""
Canales de aviso. `get_notifiers()` solo instancia los que tienen
credenciales configuradas — así el sistema funciona con Telegram solo,
Gmail solo, ambos, o ninguno (el digest se genera igual, simplemente no
se envía por ningún canal si no hay credenciales).

Gmail queda con código completo pero SIN activar hasta que se agreguen
GMAIL_USER/GMAIL_APP_PASSWORD/ALERT_EMAIL_TO (decisión del usuario,
15/07/26: enfocar primero en Telegram).
"""
import smtplib
from email.mime.text import MIMEText
from typing import Protocol

import httpx
from loguru import logger

from ..core.config import settings


class Notifier(Protocol):
    def send(self, text: str) -> None: ...


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        resp = httpx.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=15)
        resp.raise_for_status()


class GmailNotifier:
    def __init__(self, user: str, app_password: str, to_email: str,
                 subject: str = "GovTracker — hallazgos nuevos"):
        self.user = user
        self.app_password = app_password
        self.to_email = to_email
        self.subject = subject

    def send(self, text: str) -> None:
        msg = MIMEText(text, "plain", "utf-8")
        msg["Subject"] = self.subject
        msg["From"] = self.user
        msg["To"] = self.to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(self.user, self.app_password)
            server.sendmail(self.user, [self.to_email], msg.as_string())


def get_notifiers() -> list:
    notifiers = []
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        notifiers.append(TelegramNotifier(settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID))
    else:
        logger.info("Telegram no configurado (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes)")
    if settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD and settings.ALERT_EMAIL_TO:
        notifiers.append(GmailNotifier(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD, settings.ALERT_EMAIL_TO))
    return notifiers
