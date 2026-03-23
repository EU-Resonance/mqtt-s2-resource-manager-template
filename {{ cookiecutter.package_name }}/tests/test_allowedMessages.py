import json
import uuid

import pytest
from common.allowedMessages import Payload
from s2python.common import ReceptionStatus, ReceptionStatusValues


def test_from_json_valid_reception_status():
    payload = {
        "message_type": "ReceptionStatus",
        "subject_message_id": str(uuid.uuid4()),
        "status": ReceptionStatusValues.OK,
        "diagnostic_label": "ok",
    }
    json_str = json.dumps(payload)

    result = Payload.from_json(json_str)

    assert isinstance(result, ReceptionStatus)
    assert result.message_type == "ReceptionStatus"
    assert result.subject_message_id == uuid.UUID(payload["subject_message_id"])
    assert result.status == ReceptionStatusValues.OK
    assert result.diagnostic_label == "ok"


def test_from_json_missing_message_type_raises():
    json_str = json.dumps({"foo": "bar"})

    with pytest.raises(ValueError):
        Payload.from_json(json_str)
