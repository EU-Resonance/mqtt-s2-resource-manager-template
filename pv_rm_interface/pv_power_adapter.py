# This in a devices specific class, to specify where the power data is coming from
# and to bring it in the correct format

import logging
from collections.abc import Iterable
from datetime import timedelta
from typing import List

import pandas as pd
from s2python.common import (
    PowerForecastElement,
    PowerValue,
)

from common.model_interface import PowerForecastInterface
from common.power_data_connector import PowerDataConnector


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

    def read_current_power(self) -> float:
        """Get the current power from any source"""
        return 50.0

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
