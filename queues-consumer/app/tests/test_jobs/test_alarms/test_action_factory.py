"""La fabrica de acciones tiene que dar de alta los seis canales de la API."""

from unittest.mock import MagicMock

import pytest

from jobs.alarms.action.action_factory import ActionFactory
from jobs.alarms.action.email_action import EmailAction
from jobs.alarms.action.entity_command_action import EntityCommandAction
from jobs.alarms.action.http_push_action import HttpPushAction
from jobs.alarms.action.notification_action import NotificationAction
from jobs.alarms.queries import ACTION_MODELS


def action_model(name: str) -> MagicMock:
    model = MagicMock()
    model.name = name
    return model


CHANNEL_ROWS = {
    "action_telegram": MagicMock(chat_id=1234, message="salta"),
    "action_sms": MagicMock(phone="+34600000000", message="salta"),
    "action_whatsapp": MagicMock(phone="+34600000000", message="salta"),
    "action_email": MagicMock(
        destination="a@example.org#b@example.org",
        subject="asunto",
        content="cuerpo",
    ),
    "action_http_push": MagicMock(
        url_template="https://avisos.example.org/x",
        method="POST",
        authorization=None,
    ),
    "action_entity_command": MagicMock(commands={"12": {"close": "1"}}),
}


@pytest.fixture
def alarm_actions(mocker):
    mocker.patch(
        "jobs.alarms.action.action_factory.queries.get_alarm_action_ids",
        return_value=list(range(1, len(CHANNEL_ROWS) + 1)),
    )
    mocker.patch(
        "jobs.alarms.action.action_factory.queries.get_actions_of_type",
        side_effect=lambda action_ids, actionable_type, db: [
            (action_model(actionable_type), CHANNEL_ROWS[actionable_type])
        ],
    )


class TestActionFactory:
    def test_every_channel_of_the_api_has_a_model(self):
        assert set(ACTION_MODELS) == set(CHANNEL_ROWS)

    def test_builds_one_action_per_channel(self, alarm_actions):
        actions = ActionFactory().get_alarm_actions(7, True, "resumen", MagicMock())

        assert len(actions) == len(CHANNEL_ROWS)
        assert sum(isinstance(a, NotificationAction) for a in actions) == 3
        assert sum(isinstance(a, EmailAction) for a in actions) == 1
        assert sum(isinstance(a, HttpPushAction) for a in actions) == 1
        assert sum(isinstance(a, EntityCommandAction) for a in actions) == 1

    def test_no_channel_is_reported_as_unsupported(self, alarm_actions, mocker):
        warning = mocker.patch(
            "jobs.alarms.action.action_factory.logging.warning"
        )

        ActionFactory().get_alarm_actions(7, True, "resumen", MagicMock())

        warning.assert_not_called()

    def test_email_destinations_are_split(self, alarm_actions):
        actions = ActionFactory().get_alarm_actions(7, True, "resumen", MagicMock())
        email = next(a for a in actions if isinstance(a, EmailAction))

        assert email.destination == ["a@example.org", "b@example.org"]
