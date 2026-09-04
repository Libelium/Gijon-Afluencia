"""Pruebas de los canales de accion del motor de alarmas."""

from unittest.mock import MagicMock

import pytest

from jobs.alarms.action import senders
from jobs.alarms.action.email_action import EmailAction
from jobs.alarms.action.entity_command_action import EntityCommandAction
from jobs.alarms.action.http_push_action import HttpPushAction


@pytest.fixture
def db():
    return MagicMock()


def mail_settings(mocker, **overrides):
    values = {
        "MAIL_ENABLED": True,
        "MAIL_HOST": "smtp.example.org",
        "MAIL_PORT": 587,
        "MAIL_USERNAME": "avisos@example.org",
        "MAIL_PASSWORD": "secreto",
        "MAIL_FROM": "avisos@example.org",
        "MAIL_ENCRYPTION": "starttls",
        "MAIL_TIMEOUT": 10,
    }
    values.update(overrides)

    for name, value in values.items():
        mocker.patch.object(senders.settings, name, value)


# ---------------------------------------------------------------------------
# Correo
# ---------------------------------------------------------------------------


class TestEmailAction:
    def test_sends_the_message_with_the_summary(self, mocker, db):
        mail_settings(mocker)
        smtp = mocker.patch.object(senders.smtplib, "SMTP")
        # smtplib.SMTP se usa como gestor de contexto y devuelve la propia conexion.
        smtp.return_value.__enter__.return_value = smtp.return_value

        EmailAction(
            name="aviso",
            destination=["a@example.org", "b@example.org"],
            subject="Alarma disparada",
            content="Revisa el sensor",
            alarm_id=7,
            summary="filling > 0.8",
            db=db,
        ).run()

        connection = smtp.return_value
        connection.starttls.assert_called_once()
        connection.login.assert_called_once_with("avisos@example.org", "secreto")

        message = connection.send_message.call_args.args[0]
        assert message["To"] == "a@example.org, b@example.org"
        assert message["Subject"] == "Alarma disparada"
        assert message["From"] == "avisos@example.org"
        assert "Revisa el sensor" in message.get_content()
        assert "filling > 0.8" in message.get_content()

    def test_uses_an_ssl_connection_when_configured(self, mocker, db):
        mail_settings(mocker, MAIL_ENCRYPTION="ssl", MAIL_PORT=465)
        smtp_ssl = mocker.patch.object(senders.smtplib, "SMTP_SSL")
        plain_smtp = mocker.patch.object(senders.smtplib, "SMTP")

        EmailAction("aviso", ["a@example.org"], "asunto", "cuerpo", 7, "", db).run()

        smtp_ssl.assert_called_once()
        plain_smtp.assert_not_called()

    def test_without_a_server_it_skips_the_channel_and_does_not_raise(
        self, mocker, db
    ):
        mail_settings(mocker, MAIL_ENABLED=False)
        smtp = mocker.patch.object(senders.smtplib, "SMTP")
        warning_log = mocker.patch(
            "jobs.alarms.action.logged_action.create_warning_log"
        )

        EmailAction("aviso", ["a@example.org"], "asunto", "cuerpo", 7, "", db).run()

        smtp.assert_not_called()
        warning_log.assert_called_once()

    def test_a_broken_server_is_logged_as_an_error(self, mocker, db):
        mail_settings(mocker)
        mocker.patch.object(
            senders.smtplib, "SMTP", side_effect=OSError("conexion rechazada")
        )
        error_log = mocker.patch("jobs.alarms.action.logged_action.create_error_log")

        EmailAction("aviso", ["a@example.org"], "asunto", "cuerpo", 7, "", db).run()

        error_log.assert_called_once()


# ---------------------------------------------------------------------------
# Aviso HTTP
# ---------------------------------------------------------------------------


class TestHttpPushAction:
    @pytest.fixture(autouse=True)
    def public_dns(self, mocker):
        """Evita la resolucion real: el destino permitido es una IP publica."""
        mocker.patch.object(
            senders.socket,
            "getaddrinfo",
            return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
        )

    def test_sends_the_alarm_state_to_an_allowed_destination(self, mocker, db):
        mocker.patch.object(
            senders.settings,
            "HTTP_PUSH_ALLOWED_DESTINATIONS",
            "avisos.example.org",
        )
        request = mocker.patch.object(senders.requests, "request")

        HttpPushAction(
            name="aviso",
            url_template=[
                {"type": "text", "value": "https://avisos.example.org/alarmas/"},
                {"type": "variable", "value": "alarm_id"},
            ],
            method="post",
            authorization="un-token",
            alarm_id=7,
            alarm_up=True,
            summary="filling > 0.8",
            db=db,
        ).run()

        assert request.call_args.args == (
            "POST",
            "https://avisos.example.org/alarmas/7",
        )
        assert request.call_args.kwargs["allow_redirects"] is False
        assert request.call_args.kwargs["timeout"] > 0
        assert request.call_args.kwargs["headers"] == {
            "Authorization": "Bearer un-token"
        }
        assert request.call_args.kwargs["json"] == {
            "alarm_id": 7,
            "alarm_status_up": True,
            "alarm_activation_conditions": "filling > 0.8",
        }

    def test_a_destination_outside_the_allow_list_is_not_called(self, mocker, db):
        mocker.patch.object(
            senders.settings,
            "HTTP_PUSH_ALLOWED_DESTINATIONS",
            "avisos.example.org",
        )
        request = mocker.patch.object(senders.requests, "request")
        error_log = mocker.patch("jobs.alarms.action.logged_action.create_error_log")

        HttpPushAction(
            name="aviso",
            url_template="https://otro-sitio.example.net/webhook",
            method="POST",
            authorization=None,
            alarm_id=7,
            alarm_up=True,
            summary="",
            db=db,
        ).run()

        request.assert_not_called()
        error_log.assert_called_once()

    @pytest.mark.parametrize(
        "url",
        [
            "https://avisos.example.org.atacante.tld/x",
            "https://avisos.example.org@atacante.tld/x",
            "https://avisos.example.org.atacante.tld:8080/",
            "https://avisos.example.org:8443/x",
        ],
    )
    def test_a_destination_that_only_looks_like_the_allowed_prefix_is_rejected(
        self, mocker, db, url
    ):
        """Una entrada con esquema es un prefijo de URL, no un prefijo de cadena."""
        mocker.patch.object(
            senders.settings,
            "HTTP_PUSH_ALLOWED_DESTINATIONS",
            "https://avisos.example.org",
        )
        request = mocker.patch.object(senders.requests, "request")
        error_log = mocker.patch("jobs.alarms.action.logged_action.create_error_log")

        HttpPushAction("aviso", url, "POST", "un-token", 7, True, "", db).run()

        request.assert_not_called()
        error_log.assert_called_once()

    def test_a_url_prefix_allows_only_that_path(self, mocker, db):
        mocker.patch.object(
            senders.settings,
            "HTTP_PUSH_ALLOWED_DESTINATIONS",
            "https://avisos.example.org/alarmas",
        )
        request = mocker.patch.object(senders.requests, "request")

        HttpPushAction(
            "aviso", "https://avisos.example.org/alarmas/7", "POST", None, 7, True, "", db
        ).run()
        assert request.call_count == 1

        HttpPushAction(
            "aviso", "https://avisos.example.org/alarmasX", "POST", None, 7, True, "", db
        ).run()
        assert request.call_count == 1

    def test_an_unusable_url_template_is_logged_and_does_not_raise(self, mocker, db):
        mocker.patch.object(
            senders.settings, "HTTP_PUSH_ALLOWED_DESTINATIONS", "avisos.example.org"
        )
        request = mocker.patch.object(senders.requests, "request")
        error_log = mocker.patch("jobs.alarms.action.logged_action.create_error_log")

        HttpPushAction("aviso", {"a": "b"}, "POST", None, 7, True, "", db).run()

        request.assert_not_called()
        error_log.assert_called_once()

    def test_an_empty_allow_list_sends_nothing(self, mocker, db):
        mocker.patch.object(senders.settings, "HTTP_PUSH_ALLOWED_DESTINATIONS", "")
        request = mocker.patch.object(senders.requests, "request")
        warning_log = mocker.patch(
            "jobs.alarms.action.logged_action.create_warning_log"
        )

        HttpPushAction(
            "aviso", "https://avisos.example.org/x", "POST", None, 7, True, "", db
        ).run()

        request.assert_not_called()
        warning_log.assert_called_once()

    def test_an_internal_address_is_rejected(self, mocker, db):
        mocker.patch.object(
            senders.settings, "HTTP_PUSH_ALLOWED_DESTINATIONS", "interno.example.org"
        )
        mocker.patch.object(
            senders.socket,
            "getaddrinfo",
            return_value=[(2, 1, 6, "", ("127.0.0.1", 80))],
        )
        request = mocker.patch.object(senders.requests, "request")

        HttpPushAction(
            "aviso", "http://interno.example.org/webhook", "POST", None, 7, True, "", db
        ).run()

        request.assert_not_called()

    def test_a_network_failure_is_logged_and_does_not_raise(self, mocker, db):
        mocker.patch.object(
            senders.settings, "HTTP_PUSH_ALLOWED_DESTINATIONS", "avisos.example.org"
        )
        mocker.patch.object(
            senders.requests, "request", side_effect=Exception("sin ruta al destino")
        )
        error_log = mocker.patch("jobs.alarms.action.logged_action.create_error_log")

        HttpPushAction(
            "aviso", "https://avisos.example.org/x", "POST", None, 7, True, "", db
        ).run()

        error_log.assert_called_once()

    def test_a_scheme_that_is_not_http_is_rejected(self, mocker, db):
        mocker.patch.object(
            senders.settings, "HTTP_PUSH_ALLOWED_DESTINATIONS", "file://"
        )
        request = mocker.patch.object(senders.requests, "request")

        HttpPushAction(
            "aviso", "file:///etc/passwd", "POST", None, 7, True, "", db
        ).run()

        request.assert_not_called()


# ---------------------------------------------------------------------------
# Comando a la entidad
# ---------------------------------------------------------------------------


class TestEntityCommandAction:
    @pytest.fixture(autouse=True)
    def realtime_db(self, mocker):
        """La base de tiempo real se abre al marcar el pendiente: no se toca aqui."""
        session = MagicMock()
        realtime = mocker.patch(
            "jobs.alarms.action.entity_command_action.realtime_session"
        )
        realtime.return_value.__enter__.return_value = session
        return session

    def test_sends_each_command_through_the_context_broker(self, mocker, db):
        mocker.patch(
            "jobs.alarms.action.entity_command_action.crud_entity.get_entity_urns_for_ids",
            return_value={12: ("urn:ngsi-ld:Device:001", "pid", "/")},
        )
        update = mocker.patch(
            "jobs.alarms.action.entity_command_action.update_on_context_broker",
            return_value={"updated": True},
        )

        EntityCommandAction(
            name="cierra la valvula",
            commands={"12": {"close": "1", "led": "off"}},
            alarm_id=7,
            db=db,
        ).run()

        assert update.call_count == 2
        assert update.call_args_list[0].args == (
            "urn:ngsi-ld:Device:001",
            "pid",
            "/",
            {"close": {"type": "Command", "value": "1"}},
        )

    def test_marks_the_sent_command_as_pending_in_the_realtime_db(
        self, mocker, db, realtime_db
    ):
        mocker.patch(
            "jobs.alarms.action.entity_command_action.crud_entity.get_entity_urns_for_ids",
            return_value={12: ("urn:ngsi-ld:Device:001", "pid", "/")},
        )
        mocker.patch(
            "jobs.alarms.action.entity_command_action.update_on_context_broker",
            return_value={"updated": True},
        )
        update_command = mocker.patch(
            "jobs.alarms.action.entity_command_action.crud_entity_commands.update_entity_command"
        )

        EntityCommandAction("cierra", {"12": {"close": "1"}}, 7, db).run()

        payload = update_command.call_args.args[0]
        assert payload["urn"] == "urn:ngsi-ld:Device:001"
        assert payload["entity_id"] == 12
        assert payload["name"] == "close"
        assert payload["pending"] is True
        assert payload["pending_value"] == "1"
        assert update_command.call_args.args[1] is realtime_db

    def test_a_failure_marking_the_pending_command_does_not_raise(self, mocker, db):
        mocker.patch(
            "jobs.alarms.action.entity_command_action.crud_entity.get_entity_urns_for_ids",
            return_value={12: ("urn:ngsi-ld:Device:001", "pid", "/")},
        )
        mocker.patch(
            "jobs.alarms.action.entity_command_action.update_on_context_broker",
            return_value={"updated": True},
        )
        mocker.patch(
            "jobs.alarms.action.entity_command_action.crud_entity_commands.update_entity_command",
            side_effect=Exception("la base de tiempo real no responde"),
        )
        info_log = mocker.patch("jobs.alarms.action.logged_action.create_info_log")

        EntityCommandAction("cierra", {"12": {"close": "1"}}, 7, db).run()

        info_log.assert_called_once()

    def test_a_rejected_command_is_not_marked_as_pending(self, mocker, db):
        mocker.patch(
            "jobs.alarms.action.entity_command_action.crud_entity.get_entity_urns_for_ids",
            return_value={12: ("urn:ngsi-ld:Device:001", "pid", "/")},
        )
        mocker.patch(
            "jobs.alarms.action.entity_command_action.update_on_context_broker",
            return_value={"updated": False, "response": "404 Not Found"},
        )
        update_command = mocker.patch(
            "jobs.alarms.action.entity_command_action.crud_entity_commands.update_entity_command"
        )
        mocker.patch("jobs.alarms.action.logged_action.create_error_log")

        EntityCommandAction("cierra", {"12": {"close": "1"}}, 7, db).run()

        update_command.assert_not_called()

    def test_an_unknown_entity_is_logged_and_skipped(self, mocker, db):
        mocker.patch(
            "jobs.alarms.action.entity_command_action.crud_entity.get_entity_urns_for_ids",
            return_value={},
        )
        update = mocker.patch(
            "jobs.alarms.action.entity_command_action.update_on_context_broker"
        )
        error_log = mocker.patch("jobs.alarms.action.logged_action.create_error_log")

        EntityCommandAction("cierra", {"99": {"close": "1"}}, 7, db).run()

        update.assert_not_called()
        error_log.assert_called_once()

    def test_a_rejected_command_is_logged_as_an_error(self, mocker, db):
        mocker.patch(
            "jobs.alarms.action.entity_command_action.crud_entity.get_entity_urns_for_ids",
            return_value={12: ("urn:ngsi-ld:Device:001", "pid", "/")},
        )
        mocker.patch(
            "jobs.alarms.action.entity_command_action.update_on_context_broker",
            return_value={"updated": False, "response": "404 Not Found"},
        )
        error_log = mocker.patch("jobs.alarms.action.logged_action.create_error_log")

        EntityCommandAction("cierra", {"12": {"close": "1"}}, 7, db).run()

        error_log.assert_called_once()

    def test_an_action_without_commands_does_nothing(self, mocker, db):
        update = mocker.patch(
            "jobs.alarms.action.entity_command_action.update_on_context_broker"
        )
        warning_log = mocker.patch(
            "jobs.alarms.action.logged_action.create_warning_log"
        )

        EntityCommandAction("cierra", {}, 7, db).run()

        update.assert_not_called()
        warning_log.assert_called_once()
