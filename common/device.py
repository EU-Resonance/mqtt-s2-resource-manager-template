import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from zoneinfo import ZoneInfo

from s2python.common import (
    ControlType,
    PowerForecast,
    PowerMeasurement,
    ResourceManagerDetails,
)

from .model_interface import PowerForecastInterface
from .power_data_connector import PowerDataConnector
from .rmClient import RMClient


class Device(RMClient, ABC):
    """================= Setup Device ================="""

    def get_model(self) -> PowerForecastInterface:
        """Return an instance of a PowerForecastModel."""
        pass

    @abstractmethod
    def get_power_data_connector(self) -> PowerDataConnector:
        """Return an instance of a DataSource for power measurements."""
        pass

    @abstractmethod
    def get_rm_details(self) -> ResourceManagerDetails:
        """Return an instance of ResourceManagerDetails."""
        pass

    """ ================= Power Data ================= """

    def get_power_measurement(self, timestamp: datetime) -> PowerMeasurement:
        return self.get_power_data_connector().create_power_measurement(timestamp)

    def get_power_forecast(self, starttime: datetime) -> PowerForecast:
        return self.get_power_data_connector().create_power_forecast(starttime)

    """ ================= Data Transmission Loop ================= """

    def startDataTransmission(self, local_timezone, repeat=15):

        if self.rmd.provides_forecast:
            logging.info(" >> Starting data transmission with forecast...")
        else:
            logging.info(" >> Starting data transmission without forecast...")

        try:
            while self.connection.on:
                timestamp = datetime.now(ZoneInfo(local_timezone))

                # Send power measurement
                try:
                    measurement = self.get_power_measurement(timestamp)
                    self.sendPowerMeasurement(measurement, self.rmMessenger.client)
                except Exception as e:
                    logging.error(
                        f" !! Error during power measurement transmission: {e}",
                        exc_info=True,
                    )

                # Send power forecast
                if self.rmd.provides_forecast:
                    try:
                        forecast = self.get_power_forecast(timestamp)
                        self.sendPowerForecast(forecast, self.rmMessenger.client)
                    except Exception as e:
                        logging.error(
                            f" !! Error during power forecast transmission: {e}",
                            exc_info=True,
                        )

                time.sleep(repeat)

        except KeyboardInterrupt:
            logging.info(
                "\n XX Keyboard Interrupt detected! Exiting the loop safely..."
            )
            self.rmMessenger.loop_stop()

    """ ================= Trigger Flexibility Transmission ================= """

    def sendSystemDescription(self):

        # PEBC
        if self.activeControlType == ControlType.POWER_ENVELOPE_BASED_CONTROL:
            if self.pebc_ec is not None:
                self.sendPEBCEnergyConstraints(self.rmMessenger.client)
                time.sleep(0.5)

            self.sendPEBCPowerConstraints(self.rmMessenger.client)

        # PPBC
        if self.activeControlType == ControlType.POWER_PROFILE_BASED_CONTROL:
            self.sendPPBCPowerProfileDefinition(self.rmMessenger.client)

        # OMBC
        if self.activeControlType == ControlType.OPERATION_MODE_BASED_CONTROL:
            self.sendOMBCSystemDescription(self.rmMessenger.client)

        # FRBC
        if self.activeControlType == ControlType.FILL_RATE_BASED_CONTROL:
            self.sendFRBCSystemDescription(self.rmMessenger.client)

        # DDBC
        if self.activeControlType == ControlType.DEMAND_DRIVEN_BASED_CONTROL:
            self.sendDDBCSystemDescription(self.rmMessenger.client)
