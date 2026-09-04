"""
Envio de las notificaciones de las acciones de alarma. La configuracion de cada
canal se lee aqui, junto al unico codigo que la usa, y sin credenciales no se
intenta el envio.
"""

import ipaddress
import os
import smtplib
import socket
import ssl
from email.message import EmailMessage
from typing import List
from urllib.parse import urlparse

import requests
from config.config import settings

TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false") == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = os.getenv("TELEGRAM_API_URL", "https://api.telegram.org")

SMS_ENABLED = os.getenv("SMS_ENABLED", "false") == "true"

WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "false") == "true"
WHATSAPP_PROVIDER = os.getenv("WHATSAPP_PROVIDER", "meta")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_API_URL = os.getenv("WHATSAPP_API_URL", "https://graph.facebook.com/v19.0")


class ChannelNotConfigured(Exception):
    """
    El canal no esta habilitado o le faltan credenciales.
    """


class DestinationNotAllowed(Exception):
    """
    El destino no esta en la lista blanca o resuelve a una direccion interna.
    """


def send_telegram(destination: str, message: str) -> None:
    if not TELEGRAM_ENABLED or not TELEGRAM_BOT_TOKEN:
        raise ChannelNotConfigured("Telegram no esta configurado en este entorno")

    response = requests.post(
        f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": destination, "text": message, "parse_mode": "HTML"},
        timeout=settings.DEFAULT_EXTERNAL_REQUEST_TIMEOUT,
    )
    response.raise_for_status()


def send_sms(destination: str, message: str) -> None:
    if not SMS_ENABLED:
        raise ChannelNotConfigured("El envio de SMS no esta habilitado")

    if settings.SMS_PROVIDER != "aws_sns":
        raise ChannelNotConfigured(
            f"Proveedor de SMS no soportado: '{settings.SMS_PROVIDER}'. Solo aws_sns"
        )

    import boto3

    client = boto3.client(
        "sns",
        region_name=settings.SMS_AWS_REGION,
        aws_access_key_id=settings.SMS_API_KEY,
        aws_secret_access_key=settings.SMS_API_SECRET,
    )

    message_attributes = {
        "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}
    }

    if settings.SMS_FROM:
        message_attributes["AWS.SNS.SMS.SenderID"] = {
            "DataType": "String",
            "StringValue": settings.SMS_FROM,
        }

    client.publish(
        PhoneNumber=destination,
        Message=message,
        MessageAttributes=message_attributes,
    )


def send_whatsapp(destination: str, message: str) -> None:
    if not WHATSAPP_ENABLED:
        raise ChannelNotConfigured("El envio de WhatsApp no esta habilitado")

    if WHATSAPP_PROVIDER != "meta":
        raise ChannelNotConfigured(
            f"Proveedor de WhatsApp no soportado: '{WHATSAPP_PROVIDER}'. Solo meta"
        )

    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise ChannelNotConfigured("Faltan las credenciales de WhatsApp")

    response = requests.post(
        f"{WHATSAPP_API_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages",
        json={
            "messaging_product": "whatsapp",
            "to": destination,
            "type": "text",
            "text": {"body": message},
        },
        headers={
            "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        timeout=settings.DEFAULT_EXTERNAL_REQUEST_TIMEOUT,
    )
    response.raise_for_status()


def send_email(destinations: List[str], subject: str, body: str) -> None:
    if not settings.MAIL_ENABLED or not settings.MAIL_HOST:
        raise ChannelNotConfigured("El envio de correo no esta configurado")

    if not destinations:
        raise ChannelNotConfigured("La accion de correo no tiene destinatarios")

    message = EmailMessage()
    message["From"] = settings.MAIL_FROM or settings.MAIL_USERNAME
    message["To"] = ", ".join(destinations)
    message["Subject"] = subject
    message.set_content(body)

    with _smtp_connection() as smtp:
        if settings.MAIL_USERNAME:
            smtp.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)

        smtp.send_message(message)


def _smtp_connection() -> smtplib.SMTP:
    if settings.MAIL_ENCRYPTION == "ssl":
        return smtplib.SMTP_SSL(
            settings.MAIL_HOST,
            settings.MAIL_PORT,
            timeout=settings.MAIL_TIMEOUT,
            context=ssl.create_default_context(),
        )

    smtp = smtplib.SMTP(
        settings.MAIL_HOST,
        settings.MAIL_PORT,
        timeout=settings.MAIL_TIMEOUT,
    )

    if settings.MAIL_ENCRYPTION == "starttls":
        smtp.starttls(context=ssl.create_default_context())

    return smtp


def allowed_http_push_destinations() -> List[str]:
    return [
        destination.strip()
        for destination in settings.HTTP_PUSH_ALLOWED_DESTINATIONS.split(",")
        if destination.strip()
    ]


def send_http_push(url: str, method: str, authorization: str, payload: dict) -> None:
    allowed = allowed_http_push_destinations()

    if not allowed:
        raise ChannelNotConfigured(
            "No hay destinos permitidos para el aviso HTTP: no se envia nada"
        )

    check_http_push_destination(url, allowed)

    verb = (method or "POST").upper()
    request_config = (
        {"json": payload} if verb in ("POST", "PUT", "PATCH") else {"params": payload}
    )
    headers = {"Authorization": f"Bearer {authorization}"} if authorization else None

    response = requests.request(
        verb,
        url,
        headers=headers,
        # Un 30x no debe reenviar la peticion (ni la cabecera Authorization) a
        # un destino que no esta en la lista blanca.
        allow_redirects=False,
        timeout=settings.HTTP_PUSH_REQUEST_TIMEOUT,
        **request_config,
    )
    response.raise_for_status()


def check_http_push_destination(url: str, allowed: List[str]) -> None:
    """
    El destino lo escribe quien configura la alarma, asi que se comprueba antes
    de llamarlo: esquema HTTP, presente en la lista blanca y sin resolver a una
    direccion interna o de bucle local.
    """
    try:
        parsed = urlparse(url)
        _port(parsed)

    except ValueError as e:
        raise DestinationNotAllowed(
            f"Destino no valido para un aviso HTTP: '{url}'"
        ) from e

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise DestinationNotAllowed(f"Destino no valido para un aviso HTTP: '{url}'")

    # "https://permitido@atacante.tld/" tiene por host a atacante.tld: el
    # userinfo solo sirve aqui para disfrazar el destino.
    if parsed.username or parsed.password:
        raise DestinationNotAllowed(
            f"El destino '{url}' lleva credenciales en la URL"
        )

    if not any(_matches_destination(parsed, entry) for entry in allowed):
        raise DestinationNotAllowed(
            f"El destino '{url}' no esta en la lista de destinos permitidos"
        )

    _reject_internal_host(parsed.hostname)


def _matches_destination(parsed, entry: str) -> bool:
    """
    Las entradas sin esquema son hosts (el destino ha de ser ese host o un
    subdominio suyo); las que lo llevan son prefijos de URL y se comparan por
    partes, nunca como cadenas: 'https://avisos.example.org' no puede dar por
    bueno a 'avisos.example.org.atacante.tld'.
    """
    hostname = (parsed.hostname or "").lower()

    if "://" not in entry:
        entry = entry.lower().rstrip("/")

        return hostname == entry or hostname.endswith(f".{entry}")

    allowed = urlparse(entry)

    if (
        parsed.scheme != allowed.scheme
        or hostname != (allowed.hostname or "").lower()
        or _port(parsed) != _port(allowed)
    ):
        return False

    prefix = allowed.path or "/"

    return parsed.path == prefix.rstrip("/") or parsed.path.startswith(
        prefix.rstrip("/") + "/"
    )


def _port(parsed) -> int:
    return parsed.port or (443 if parsed.scheme == "https" else 80)


def _reject_internal_host(hostname: str) -> None:
    try:
        addresses = socket.getaddrinfo(hostname, None)

    except socket.gaierror as e:
        raise DestinationNotAllowed(f"No se resuelve el destino '{hostname}'") from e

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise DestinationNotAllowed(
                f"El destino '{hostname}' resuelve a la direccion interna {ip}"
            )
