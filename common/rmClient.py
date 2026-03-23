import configparser
import json
import logging
import os
import uuid

import paho.mqtt.client as mqtt
from s2python.common import (
    ControlType,
    PowerForecast,
    PowerMeasurement,
    ReceptionStatus,
    ReceptionStatusValues,
    ResourceManagerDetails,
    SelectControlType,
)
from s2python.ddbc import DDBCInstruction, DDBCSystemDescription
from s2python.frbc import FRBCInstruction, FRBCSystemDescription
from s2python.ombc import OMBCInstruction, OMBCSystemDescription
from s2python.pebc import PEBCEnergyConstraint, PEBCInstruction, PEBCPowerConstraints
from s2python.ppbc import PPBCPowerProfileDefinition, PPBCScheduleInstruction

from .allowedMessages import Payload
from .messaging import Messaging as msg


class RMClient:
    def __init__(self):
        self.rmUUID = uuid.uuid4()
        self.rmd = None
        self.activeControlType = ControlType.NO_SELECTION
        self.rmdSent = False

        self.connection = self.CEMConnection()
        self.messageRegister = {}

        self.pebc_pc = None
        self.pebc_ec = None
        self.ppbc = None
        self.ombc = None
        self.frbc = None
        self.ddbc = None

    # environment.env provides the mqtt connection properties.
    def getConfig(self):
        configParser = configparser.ConfigParser(defaults={})

        # Resolve config to environmental variables in docker compose
        env_vars = {
            "host": "MQTT_SERVER",
            "password": "MQTT_PASSWORD",
            "port": "MQTT_PORT",
            "username": "MQTT_USERNAME",
            "timezone": "TZ",
        }
        for key, env_var in env_vars.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                escaped_env_value = env_value.replace("%", "%%")
                configParser["DEFAULT"][key] = escaped_env_value

        return configParser["DEFAULT"]

    def startDiscovery(self, config, onCemDiscovered):
        logging.info(" >> === Looking for a CEM ===")

        def cemDiscovery(client, userdata, msg: mqtt.MQTTMessage):
            jsonString = msg.payload.decode("utf-8")
            payload = json.loads(jsonString)

            if payload["message_type"] == "CEM_ALIVE_MESSAGE" and not self.rmdSent:
                self.connection.cemUUID = payload["message_id"]
                logging.info(
                    f" >> [CEM] discovered with uuid: {self.connection.cemUUID} \n"
                )

                onCemDiscovered(self.connection.cemUUID)

        self.cemMessenger = msg(config, "resonance/cem/#", cemDiscovery)
        self.cemMessenger.loop_start()

    def startRmSubscription(self, config, rmCallback=None):
        logging.info(" >> [RM] Starting RM subscription...")

        self.rmCallback = rmCallback

        self.rmMessenger = msg(
            config,
            f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/#",
            self.handle_rm_topic_messages,
        )
        self.rmMessenger.subscribe(
            f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/ack/cem"
        )
        self.rmMessenger.loop_start()

        # Send ResourceManagerDetails to the CEM and wait for acceptance (rmMessenger-loop)
        self.sendResourceManagerDetails(self.rmMessenger.client)
        self.rmdSent = True

        logging.info(" >> [RM] ResourceManagerDetails sent. \n")

        # After sending ResourceManagerDetails, the details for available ControlTypes,
        # need to be updated. This is then sent after activation message for the respective ControlType
        self.get_power_data_connector().provide_flexibility_information(self)

    """ =================  RM Message Handling  ================= """
    # Handle messages on the RM topic, that come from the CEM

    def handle_rm_topic_messages(
        self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage
    ):
        jsonString = msg.payload.decode("utf-8")
        payload = Payload.from_json(jsonString)

        """ Activation of Control Type """
        if isinstance(payload, SelectControlType):
            logging.info(" >> [CEM] Received ControlType activation request")

            if payload.control_type in self.rmd.available_control_types:
                self.activeControlType = payload.control_type

                if self.rmCallback:
                    self.rmCallback(self.activeControlType)

                self.sendReceptionStatus(
                    recStatus=ReceptionStatusValues.OK,
                    message="ControlType activated",
                    subMessageId=payload.message_id,
                    client=client,
                )

            else:
                logging.info(
                    f" >> [RM] ControlType {payload.control_type} rejected. Sending response to CEM"
                )
                self.sendReceptionStatus(
                    recStatus=ReceptionStatusValues.INVALID_CONTENT,
                    message="ControlType activation rejected",
                    subMessageId=payload.message_id,
                    client=client,
                )

        elif isinstance(payload, ReceptionStatus):
            # Implenet method handleReceptionStatus() as in CEM

            smId = str(payload.subject_message_id)
            if smId in self.messageRegister:
                # get the message_type from the register to assign the response
                message_type = self.messageRegister[smId]["message_type"]

                # ignore messages that are related to other responses
                if message_type == "ReceptionStatus":
                    return

                """ consequences of the response """

                if payload.subject_message_id == self.rmd.message_id:
                    if payload.status == ReceptionStatusValues.OK:
                        self.connection.established(True)
                        self.connectedCem = self.connection.cemUUID
                        logging.info(
                            f" >> [CEM] Received positive response from CEM, connection established. Connection: {self.connection.on} \n"
                        )
                    else:
                        logging.info(
                            f" [CEM] Resource Manager Details rejected: {payload}"
                        )
                        # logging.warning(self.handleReceptionStatus(payload))
                else:
                    logging.info(
                        " !! [CEM] Received Reception Status for unknown message id: \n"
                        + str(payload.subject_message_id)
                    )

        elif isinstance(
            payload,
            (
                PPBCScheduleInstruction,
                FRBCInstruction,
                OMBCInstruction,
                PEBCInstruction,
                DDBCInstruction,
            ),
        ):
            logging.info(
                f" >> [CEM] Received CEM Instruction with message_id {payload.message_id}."
            )

            if self.rmCallback:
                self.rmCallback(payload)

            # For DEMO purposes, accept all instructions
            self.sendReceptionStatus(
                recStatus=ReceptionStatusValues.OK,
                message=" >> [RM] Instruction accepted",
                subMessageId=payload.message_id,
                client=client,
            )

            return

        # Ignore messages that can only be sent by the RM itself
        elif isinstance(
            payload,
            (
                ResourceManagerDetails,
                PowerForecast,
                PowerMeasurement,
                PPBCPowerProfileDefinition,
                OMBCSystemDescription,
                FRBCSystemDescription,
                PEBCEnergyConstraint,
                PEBCPowerConstraints,
                DDBCSystemDescription,
            ),
        ):
            return

        else:
            logging.info(
                f" !! [RM] Unknown message type {payload.message_type}. Message: {msg.payload.decode()}"
            )

    def sendResourceManagerDetails(self, client: mqtt.Client):
        resourceManagerDetails = self.rmd
        payloadJson = resourceManagerDetails.to_json()
        # logging.info(" Resource manager details: " + payloadJson)
        try:
            client.publish(
                f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/event",
                payloadJson,
            )

            self.logMessageInRegsiter(
                True,
                str(resourceManagerDetails.message_id),
                resourceManagerDetails.message_type,
            )

        except Exception as e:
            logging.error(f" !! [RM] Error sending RM details: {e}")

    def sendPowerForecast(self, powerForecast: PowerForecast, client: mqtt.Client):
        payloadJson = powerForecast.to_json()
        logging.info(" Power forecast: " + payloadJson)

        try:
            client.publish(
                f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/telemetry",
                payloadJson,
            )

        except Exception as e:
            logging.error(f" !! [RM] Error sending power forecast: {e}")

    def sendPowerMeasurement(
        self, powerMeasurement: PowerMeasurement, client: mqtt.Client
    ):
        payloadJson = powerMeasurement.to_json()
        logging.info(" Power measurement: " + payloadJson)
        try:
            client.publish(
                f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/telemetry",
                payloadJson,
            )
        except Exception as e:
            logging.error(f" !! [RM] Error sending power measurement: {e}")

    def sendReceptionStatus(
        self,
        recStatus: ReceptionStatusValues,
        message: str,
        subMessageId: uuid.UUID,
        client: mqtt.Client,
    ):
        # 9.2.1 in EN-50491-12-2
        responsePayload = ReceptionStatus(
            message_type="ReceptionStatus",
            subject_message_id=subMessageId,
            status=recStatus,
            diagnostic_label=message,
        )

        responseJson = responsePayload.to_json()

        try:
            logging.info(f" >> [RM] Sending response to CEM: {recStatus.value} \n")
            client.publish(
                f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/ack",
                responseJson,
            )

            self.logMessageInRegsiter(
                True,
                str(responsePayload.subject_message_id),
                responsePayload.message_type,
            )

        except Exception as e:
            logging.error(f" !! [RM] Error sending ReceptionStatus: {e}")

    """ =================  Control Types  ================= """

    def sendPPBCPowerProfileDefinition(self, client: mqtt.Client):
        payloadJson = self.ppbc.to_json()

        logging.info(" PowerProfileBasedControl: " + payloadJson)
        try:
            client.publish(
                f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/event",
                payloadJson,
            )
        except Exception as e:
            logging.error(f" !! Error sending PPBC PowerProfileDefinition: {e}")

    def sendOMBCSystemDescription(self, client: mqtt.Client):
        payloadJson = self.ombc.to_json()

        logging.info(" OperationModeBasedControl: " + payloadJson)
        try:
            client.publish(
                f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/event",
                payloadJson,
            )
        except Exception as e:
            logging.error(f" !! Error sending OMBC SystemDescription: {e}")

    def sendFRBCSystemDescription(self, client: mqtt.Client):
        payloadJson = self.frbc.to_json()

        logging.info(" FillRateBasedControl: " + payloadJson)
        try:
            client.publish(
                f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/event",
                payloadJson,
            )
        except Exception as e:
            logging.error(f" !! Error sending FRBC SystemDescription: {e}")

    def sendPEBCPowerConstraints(self, client: mqtt.Client):
        payloadJson = self.pebc_pc.to_json()

        logging.info(" PowerEnvelopeBasedControl (PC): " + payloadJson)
        try:
            client.publish(
                f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/event",
                payloadJson,
            )
        except Exception as e:
            logging.error(f" !! Error sending PEBC PowerConstraints: {e}")

    def sendPEBCEnergyConstraints(self, client: mqtt.Client):
        payloadJson = self.pebc_ec.to_json()

        logging.info(" PowerEnvelopeBasedControl (EC): " + payloadJson)
        try:
            client.publish(
                f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/event",
                payloadJson,
            )
        except Exception as e:
            logging.error(f" !! Error sending PEBC EnergyConstraints: {e}")

    def sendDDBCSystemDescription(self, client: mqtt.Client):
        payloadJson = self.ddbc.to_json()

        logging.info(" DemandDrivenBasedControl: " + payloadJson)
        try:
            client.publish(
                f"resonance/cem/{self.connection.cemUUID}/rm/{self.rmUUID}/event",
                payloadJson,
            )
        except Exception as e:
            logging.error(f" !! Error sending DDBC SystemDescription: {e}")

    """ =================  Message Register  ================= """

    def logMessageInRegsiter(
        self, sent: bool, subject_message_id: str, message_type: str
    ):
        """Logging messages with detailed information"""
        self.messageRegister[subject_message_id] = {
            "direction": "sent" if sent else "received",
            "message_type": message_type,
        }

    def getMessageRegister(self):
        return self.messageRegister

    def printRegister(self):
        logging.info(
            f" ------------ MESSAGE REGISTER ----------- \n {self.messageRegister} \n "
        )

    """ =================  Helper Functions  ================= """
    # Functions that are used to simplify the code and provide
    # additional functionality.

    def handleReceptionStatus(payload):
        if payload.status == ReceptionStatusValues.OK:
            return "Received positive response from CEM"
        elif payload.status == ReceptionStatusValues.INVALID_CONTENT:
            return "Received invalid content response from CEM"
        elif payload.status == ReceptionStatusValues.INVALID_MESSAGE:
            return "Received invalid message response from CEM"
        elif payload.status == ReceptionStatusValues.INVALID_DATA:
            return "Received invalid data response from CEM"
        elif payload.status == ReceptionStatusValues.PERMANENT_ERROR:
            return "Received permanent error response from CEM"
        elif payload.status == ReceptionStatusValues.TEMPORARY_ERROR:
            return "Received temporary error response from CEM"

    # store all information related
    class CEMConnection:
        def __init__(self):
            self._on = False
            self._cemUUID = None

        @property
        def cemUUID(self):
            return self._cemUUID

        @cemUUID.setter
        def cemUUID(self, value):
            self._cemUUID = value

        @property
        def on(self):
            return self._on

        def established(self, value: bool):
            self._on = value
