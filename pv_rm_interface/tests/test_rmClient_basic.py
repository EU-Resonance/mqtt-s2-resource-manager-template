import json
import uuid
from typing import Any, Dict

from common.rmClient import RMClient
from s2python.common import (
    ControlType,
    ResourceManagerDetails,
    Role,
    SelectControlType,
)


class DummyRM(RMClient):
    """Minimal RMClient subclass with a static ResourceManagerDetails."""

    def __init__(self) -> None:
        super().__init__()
        self.rmd = ResourceManagerDetails(
            message_type="ResourceManagerDetails",
            message_id=uuid.uuid4(),
            resource_id=self.rmUUID,
            name="test_dummy",
            roles=[Role(role="ENERGY_PRODUCER", commodity="ELECTRICITY")],
            instruction_processing_delay=0,
            available_control_types=[ControlType.NO_SELECTION],
            provides_forecast=False,
            provides_power_measurement_types=["ELECTRIC.POWER.L1"],
        )


class DummyClient:
    """Very small stand-in for paho-mqtt client, capturing publishes."""

    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    def publish(self, topic: str, payload: str, *args: Any, **kwargs: Any) -> None:
        self.published.append((topic, payload))


def test_send_resource_manager_details_registers_message():
    rm = DummyRM()
    client = DummyClient()

    rm.sendResourceManagerDetails(client)  # type: ignore[arg-type]

    assert rm.messageRegister  # not empty
    # There should be a single entry keyed by the message_id
    assert str(rm.rmd.message_id) in rm.messageRegister
    entry: Dict[str, Any] = rm.messageRegister[str(rm.rmd.message_id)]
    assert entry["direction"] == "sent"
    assert entry["message_type"] == "ResourceManagerDetails"


def test_handle_rm_topic_messages_activates_control_type():
    rm = DummyRM()
    rm.rmd.available_control_types = [ControlType.POWER_PROFILE_BASED_CONTROL]

    payload = SelectControlType(
        message_type="SelectControlType",
        message_id=uuid.uuid4(),
        control_type=ControlType.POWER_PROFILE_BASED_CONTROL,
    )
    json_str = json.dumps(json.loads(payload.model_dump_json()))

    class DummyMQTTMessage:
        def __init__(self, payload: str) -> None:
            self.payload = payload.encode("utf-8")

    def _rm_callback(value: ControlType) -> None:
        rm.activeControlType = value

    rm.rmCallback = _rm_callback

    rm.handle_rm_topic_messages(
        client=DummyClient(),
        userdata=None,
        msg=DummyMQTTMessage(json_str),  # type: ignore[arg-type]
    )

    assert rm.activeControlType == ControlType.POWER_PROFILE_BASED_CONTROL
