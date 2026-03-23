import json
from json import JSONDecodeError
from typing import Any, Dict

from s2python.common import (
    PowerForecast,
    PowerMeasurement,
    ReceptionStatus,
    ResourceManagerDetails,
    SelectControlType,
)
from s2python.ddbc import DDBCInstruction, DDBCSystemDescription
from s2python.frbc import FRBCInstruction, FRBCSystemDescription
from s2python.ombc import OMBCInstruction, OMBCSystemDescription
from s2python.pebc import (
    PEBCEnergyConstraint,
    PEBCInstruction,
    PEBCPowerConstraints,
)
from s2python.ppbc import (
    PPBCPowerProfileDefinition,
    PPBCScheduleInstruction,
)

MAX_JSON_SIZE_BYTES = 1_048_576  # 1 MiB


class Payload:
    @staticmethod
    def from_json(json_str: str):
        """Deserialize a JSON payload into the appropriate S2 message type.
        Basic validation is applied to guard against malformed or oversized input.
        """
        if not isinstance(json_str, str):
            raise TypeError("json_str must be a string")

        if len(json_str.encode("utf-8")) > MAX_JSON_SIZE_BYTES:
            raise ValueError(
                f"JSON payload exceeds maximum size of {MAX_JSON_SIZE_BYTES} bytes"
            )

        try:
            data: Dict[str, Any] = json.loads(json_str)
        except JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON payload: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("JSON payload must decode to an object")

        message_type = data.get("message_type") or data.get("messageType")
        if not isinstance(message_type, str) or not message_type:
            raise ValueError("No message_type present in json string")

        # Resource Manager message
        if message_type == "ResourceManagerDetails":
            return ResourceManagerDetails(**data)
        if message_type == "ResourceManagerUpdate":
            return ResourceManagerDetails(**data)

        # Reception messages
        if message_type == "ReceptionStatus":
            return ReceptionStatus(**data)

        # Power related messages
        if message_type == "PowerForecast":
            return PowerForecast(**data)
        if message_type == "PowerMeasurement":
            return PowerMeasurement(**data)

        # Activation messages
        if message_type == "SelectControlType":
            return SelectControlType(**data)

        # ControlType related messages
        if message_type == "PPBC.PowerProfileDefinition":
            return PPBCPowerProfileDefinition(**data)
        if message_type == "OMBC.SystemDescription":
            return OMBCSystemDescription(**data)
        if message_type == "FRBC.SystemDescription":
            return FRBCSystemDescription(**data)
        if message_type == "PEBC.EnergyConstraint":
            return PEBCEnergyConstraint(**data)
        if message_type == "PEBC.PowerConstraints":
            return PEBCPowerConstraints(**data)
        if message_type == "DDBC.SystemDescription":
            return DDBCSystemDescription(**data)

        # Instruction related Messages
        if message_type == "PPBC.ScheduleInstruction":
            return PPBCScheduleInstruction(**data)
        if message_type == "OMBC.Instruction":
            return OMBCInstruction(**data)
        if message_type == "DDBC.Instruction":
            return DDBCInstruction(**data)
        if message_type == "PEBC.Instruction":
            return PEBCInstruction(**data)
        if message_type == "FRBC.Instruction":
            return FRBCInstruction(**data)

        # Fallback
        raise ValueError(f"Unknown message type: {message_type}")
