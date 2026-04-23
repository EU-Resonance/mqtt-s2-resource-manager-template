# This in a devices specific class, to specify where the power data is coming from
# and to bring it in the correct format

import logging
import uuid

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List
from collections.abc import Iterable
import pandas as pd

from common.power_data_connector import PowerDataConnector

from common.model_interface import PowerForecastInterface

from s2python.pebc import (
    PEBCPowerConstraints,
    PEBCEnergyConstraint,
    PEBCPowerEnvelopeLimitType,
    PEBCPowerEnvelopeConsequenceType,
    PEBCAllowedLimitRange,
)
from s2python.ombc import OMBCSystemDescription, OMBCOperationMode
from s2python.frbc import (
    FRBCSystemDescription,
    FRBCActuatorDescription,
    FRBCStorageDescription,
)
from s2python.ppbc import PPBCPowerProfileDefinition, PPBCPowerSequenceContainer
from s2python.ddbc import DDBCSystemDescription, DDBCActuatorDescription
from s2python.common import (
    PowerValue,
    PowerForecastValue,
    CommodityQuantity,
    PowerForecastElement,
    NumberRange,
    Transition,
    Timer,
)


class PvDataConnector(PowerDataConnector):
    # This init method is used to process the power data from any source
    def __init__(
        self, pv_details, measurements, timezone: str, model: PowerForecastInterface
    ):

        self.measurements = measurements
        self.timezone = timezone
        self.model = model

        # Read details to access current power from a database or api
        """
        self.mqtt_connection = pv_details.get('mqtt_connection')
        self.db_connection = pv_details.get('db_connection')
        self.api_connection = pv_details.get('api_connection')
        """

        self.pv_details = pv_details
        
        df = pd.read_csv(self.pv_details.get('path_to_data'), sep=";", decimal=",")
        df["DateTime"] = pd.to_datetime(df["Date"] + " " + df["Time"])
        df["time_key"] = df["DateTime"].dt.strftime("%m-%d %H:%M")
        self.datasource = df

    def read_current_power(self) -> float:
        """Get historic power data from CSV"""
        
        now = datetime.now(ZoneInfo(self.timezone)).replace(
            minute=0, second=0, microsecond=0
        )
        time_key = now.strftime("%m-%d %H:00")

        row = self.datasource[self.datasource["time_key"] == time_key]

        if row.empty:
            raise ValueError(f"No PV data found for {time_key}")

        normalized = float(row.iloc[0]["Normalized Production [0..1]"])
        peak_power = float(self.pv_details.get("peak_power"))

        current_power = peak_power * normalized
        return current_power

    # REQUIRED METHOD:
    # returns the current power data for each commodity quantity
    def get_power_values_per_commodity(self) -> List[PowerValue]:

        power_values_per_commody = []

        for measurement in self.measurements:
            # get the power value for each Commodity Quantitty in measurements
            power_value = self.convert_power_values(
                measurement, power_value=self.read_current_power()
            )
            power_values_per_commody.append(power_value)

        return power_values_per_commody

    # REQUIRED METHOD:
    # returns the power forecast values for a given horizon
    def get_power_forecast_elements(self) -> List[PowerForecastElement]:

        power_forecast = self.model.get_forecast()
        elements: List[PowerForecastElement] = []

        if power_forecast is None or not isinstance(power_forecast, Iterable):
            logging.warning("Forecast is not iterable.")
            return []

        # Calculate duration per element:
        # Divide total horizon by number of forecast values.
        # If horizon is 6 hours and forecast has 6 hourly values,
        # each element gets 1 hour duration
        num_forecast_values = len(power_forecast)
        if num_forecast_values == 0:
            logging.warning("Forecast list is empty.")
            return []

        # Ensure horizon is a timedelta
        if isinstance(self.model.horizon, timedelta):
            total_horizon = self.model.horizon
        else:
            # Fallback: assume milliseconds if not timedelta
            try:
                total_horizon = timedelta(milliseconds=int(self.model.horizon))
            except Exception:
                total_horizon = timedelta(hours=1)  # Default to 1 hour

        # Calculate duration per timestep
        stepsize = total_horizon / num_forecast_values

        # Build elements using the common helper to ensure schema correctness
        for forecast_value in power_forecast:
            fv = 0.0 if pd.isna(forecast_value) else float(forecast_value)
            power_values_per_timestep = [fv for _ in self.measurements]
            element = self.convert_measurement_array_to_forecast_element(
                measurements=self.measurements,
                stepsize=stepsize,
                power_values_per_timestep=power_values_per_timestep,
            )
            elements.append(element)

        return elements

    ###############################################
    #   FLEXEBILITY / CONTROL TYPE DEFINITION     #
    ###############################################

    def provide_flexibility_information(self, pv_device):
        """
        Here the flexibility has to be defined for the activated control type.
        Dummy values are only provided for PEBC
        """

        starttime = datetime.now(ZoneInfo(self.timezone))

        logging.info(" >> [RM] Calculating PEBC Flexibility ")
        try:
            ll = PEBCAllowedLimitRange(
                commodity_quantity=self.measurements[0],
                limit_type=PEBCPowerEnvelopeLimitType.LOWER_LIMIT,
                range_boundary=NumberRange(start_of_range=0.0, end_of_range=0.5),
                abnormal_condition_only=True,
            )

            ul = PEBCAllowedLimitRange(
                commodity_quantity=self.measurements[0],
                limit_type=PEBCPowerEnvelopeLimitType.UPPER_LIMIT,
                range_boundary=NumberRange(start_of_range=4.0, end_of_range=10.0),
                abnormal_condition_only=False,
            )

            pv_device.pebc_pc = PEBCPowerConstraints(
                message_type="PEBC.PowerConstraints",
                message_id=uuid.uuid4(),
                id=uuid.uuid4(),
                valid_from=starttime,
                valid_until=starttime + timedelta(minutes=60),
                consequence_type=PEBCPowerEnvelopeConsequenceType.DEFER,
                allowed_limit_ranges=[ll, ul],
            )

            pv_device.pebc_ec = PEBCEnergyConstraint(
                message_type="PEBC.EnergyConstraint",
                message_id=uuid.uuid4(),
                id=uuid.uuid4(),
                valid_from=starttime,
                valid_until=starttime + timedelta(minutes=60),
                upper_average_power=20,
                lower_average_power=20,
                commodity_quantity=pv_device.measurements[0],
            )

        except Exception as e:
            logging.error(" !! Error defining PEBC: %s", str(e))
