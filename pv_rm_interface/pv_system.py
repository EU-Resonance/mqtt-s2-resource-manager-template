import json
import threading
import uuid
from datetime import timedelta
from typing import List

from s2python.common import (
    Commodity,
    CommodityQuantity,
    ControlType,
    Currency,
    ResourceManagerDetails,
    Role,
    RoleType,
)

from common.device import Device
from common.model_interface import PowerForecastInterface
from common.power_data_connector import PowerDataConnector
from pv_rm_interface.pv_model_caller import PvForecastModel
from pv_rm_interface.pv_power_adapter import PvDataConnector


class PvSystem(Device):
    def __init__(self):
        super().__init__()

        # S2 specific configurations
        self.availableControlTypes = [
            ControlType.NOT_CONTROLABLE,
        ]
        self.measurements = [
            CommodityQuantity.ELECTRIC_POWER_3_PHASE_SYMMETRIC,
        ]
        self.roles = [
            Role(role=RoleType.ENERGY_PRODUCER, commodity=Commodity.ELECTRICITY),
        ]

        # read MQTT connection details from environment
        self.mqttCEM = self.getConfig()
        self.timezone = self.mqttCEM.get("timezone", "Europe/Berlin")
        self.pvDetails = self._load_pv_config()
        self.rmd = self._set_rm_details()
        self.model_config = self._load_model_config()
        self.model = self._set_model()
        self.datasource = self._set_power_data_connector()

        self.stop_transmission = (
            threading.Event()
        )  # Shared flag for stopping the thread

    def stop(self):
        self.stop_transmission.set()  # Signal the thread to stop

    def _set_rm_details(self):
        return ResourceManagerDetails(
            message_type="ResourceManagerDetails",
            message_id=uuid.uuid4(),
            resource_id=self.rmUUID,
            name="PV system",
            roles=[
                Role(
                    role=RoleType.ENERGY_PRODUCER,
                    commodity=Commodity.ELECTRICITY,
                ),
            ],
            manufacturer="N/A",
            model="N/A",
            serial_number="N/A",
            firmware_version="N/A",
            instruction_processing_delay=100,
            available_control_types=self.availableControlTypes,
            currency=Currency.EUR,
            provides_forecast=True,
            provides_power_measurement_types=self.measurements,
        )

    def _set_model(self):
        # Set forecast horizon to 6 hours
        horizon_hours = int(self.model_config.get("horizon"))
        self.set_horizon(timedelta(hours=horizon_hours))

        # Model-Type: choose btw lstm , gru, rfr, h1 or h2 - set in config.json
        return PvForecastModel(
            pv_details=self.pvDetails, model_params=self.model_config
        )

    def _set_power_data_connector(self):

        return PvDataConnector(
            pv_details=self.pvDetails,
            measurements=self.measurements,
            timezone=self.timezone,
            model=self.get_model(),
        )

    """ Load device specific config data """

    def _load_pv_config(self):
        with open("./pv_rm_interface/resources/config.json", "r") as f:
            config = json.load(f)
        return config.get("pv_details", {})

    def _load_model_config(self):
        with open("./pv_rm_interface/resources/config.json", "r") as f:
            config = json.load(f)
        return config.get("pv_model", {})

    """ ================= Device Interface Methods ================= """

    def get_roles(self) -> List[Role]:
        return self.roles

    def getAvailableControlTypes(self) -> List[ControlType]:
        return self.availableControlTypes

    def get_model(self) -> PowerForecastInterface:
        """Return the forecasting model."""
        return self.model

    def get_power_data_connector(self) -> PowerDataConnector:
        """Return the data source for power measurements."""
        return self.datasource

    def get_rm_details(self) -> ResourceManagerDetails:
        """Return the ResourceManagerDetails."""
        return self.rmd

    def get_power_data(self):
        """Fetch power predictions from the data connector."""
        power_data_connector = self.get_power_data_connector()
        return power_data_connector.get_power_values_per_commodity()

    def getcurrentControlType(self):
        return self.activeControlType

    def setControlType(self, controlType: ControlType):
        self.activeControlType = controlType

    def set_horizon(self, horizon: timedelta):
        self.horizon = horizon

    def get_horizon(self) -> timedelta:
        return self.horizon
