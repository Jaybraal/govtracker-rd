import smtplib

from app.services import notifier as notifier_module
from app.services.notifier import TelegramNotifier, GmailNotifier, get_notifiers


def test_telegram_notifier_envia_al_endpoint_correcto(monkeypatch):
    llamadas = []

    def fake_post(url, json, timeout):
        llamadas.append((url, json))
        class FakeResp:
            def raise_for_status(self): pass
        return FakeResp()

    monkeypatch.setattr(notifier_module.httpx, "post", fake_post)

    TelegramNotifier("TOKEN123", "999").send("hola mundo")

    url, payload = llamadas[0]
    assert url == "https://api.telegram.org/botTOKEN123/sendMessage"
    assert payload == {"chat_id": "999", "text": "hola mundo"}


def test_gmail_notifier_usa_smtp_ssl_465(monkeypatch):
    envios = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            envios["host"] = host
            envios["port"] = port
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, user, password):
            envios["login"] = (user, password)
        def sendmail(self, from_addr, to_addrs, msg):
            envios["sendmail"] = (from_addr, to_addrs)

    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)

    GmailNotifier("bot@gmail.com", "app-pass", "destino@gmail.com").send("cuerpo")

    assert envios["host"] == "smtp.gmail.com"
    assert envios["port"] == 465
    assert envios["login"] == ("bot@gmail.com", "app-pass")
    assert envios["sendmail"] == ("bot@gmail.com", ["destino@gmail.com"])


def test_get_notifiers_solo_instancia_lo_configurado(monkeypatch):
    monkeypatch.setattr(notifier_module.settings, "TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setattr(notifier_module.settings, "TELEGRAM_CHAT_ID", "c")
    monkeypatch.setattr(notifier_module.settings, "GMAIL_USER", None)
    monkeypatch.setattr(notifier_module.settings, "GMAIL_APP_PASSWORD", None)
    monkeypatch.setattr(notifier_module.settings, "ALERT_EMAIL_TO", None)

    notifiers = get_notifiers()

    assert len(notifiers) == 1
    assert isinstance(notifiers[0], TelegramNotifier)


def test_get_notifiers_vacio_sin_ninguna_credencial(monkeypatch):
    for campo in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "GMAIL_USER", "GMAIL_APP_PASSWORD", "ALERT_EMAIL_TO"]:
        monkeypatch.setattr(notifier_module.settings, campo, None)

    assert get_notifiers() == []
