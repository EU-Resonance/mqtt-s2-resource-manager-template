import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List

from s2python.common import (
    CommodityQuantity,
    Duration,
    PowerForecast,
    PowerForecastElement,
    PowerForecastValue,
    PowerMeasurement,
    PowerValue,
)
from s2python.ddbc import DDBCSystemDescription
from s2python.frbc import FRBCSystemDescription
from s2python.ombc import OMBCSystemDescription
from s2python.pebc import PEBCEnergyConstraint, PEBCPowerConstraints
from s2python.ppbc import PPBCPowerProfileDefinition

from .model_interface import PowerEvent


class PowerDataConnector(ABC):
    """Abstract base class for handling power data."""

    @abstractmethod
    def get_power_values_per_commodity(self) -> List[PowerValue]:
        """Retrieve current power values. One for each commodity."""
        pass

    @abstractmethod
    def get_power_forecast_elements(self) -> List[PowerForecastElement]:
        """Retrieve power forecast values from a model_interface or a database interface."""
        pass

    """ ================= S2 conversions ================= """

    def create_power_measurement(self, timestamp: datetime) -> PowerMeasurement:
        power_values = self.get_power_values_per_commodity()
        return PowerMeasurement(
            message_type="PowerMeasurement",
            message_id=uuid.uuid4(),
            measurement_timestamp=timestamp,
            values=power_values,
        )

    def create_power_forecast(self, starttime: datetime) -> PowerForecast:
        power_forecast_elements = self.get_power_forecast_elements()
        return PowerForecast(
            message_type="PowerForecast",
            message_id=uuid.uuid4(),
            start_time=starttime,
            elements=power_forecast_elements,
        )

    def convert_power_values(
        self, measurement: CommodityQuantity, power_value: float
    ) -> PowerValue:
        return PowerValue(commodity_quantity=measurement, value=power_value)

    def convert_power_forecast_value(
        self, events: List[PowerEvent]
    ) -> PowerForecastElement:
        if not events:
            raise ValueError("Events must not be empty")

        events = sorted(events, key=lambda e: e.start)

        power_values = []

        for event in events:
            powerValue = PowerForecastValue(
                value_upper_limit=event.power.max(),
                value_upper_95PPR=event.power.quantile(0.95),
                value_upper_68PPR=event.power.quantile(0.68),
                value_expected=event.power.mean(),
                value_lower_68PPR=event.power.quantile(0.32),
                value_lower_95PPR=event.power.quantile(0.05),
                value_lower_limit=event.power.min(),
                commodity_quantity=event.commodity_quantity,
            )
            power_values.append(powerValue)

        start_time = events[0].start
        end_time = events[-1].end
        total_ms = int((end_time - start_time).total_seconds() * 1000)

        # Create an instance of Elements
        return PowerForecastElement(
            duration=Duration(root=total_ms), power_values=power_values
        )

    def convert_float_to_forecast_element(
        self, measurement: CommodityQuantity, stepsize: timedelta, power: float
    ) -> PowerForecastElement:
        """Convert a float to a PowerForecastElement"""
        millisconds_step = stepsize.total_seconds() * 1000
        return PowerForecastElement(
            duration=Duration(root=int(millisconds_step)),
            power_values=[
                PowerForecastValue(
                    value_expected=float(power), commodity_quantity=measurement
                )
            ],
        )

    def convert_measurement_array_to_forecast_element(
        self,
        measurements: List[CommodityQuantity],
        stepsize: timedelta,
        power_values_per_timestep: List[float],
    ) -> PowerForecastElement:
        """Convert an array of multiple measurements to a PowerForecastElement"""
        power_values = []
        millisconds_step = stepsize.total_seconds() * 1000

        for i, measurement in enumerate(measurements):
            powerValue = PowerForecastValue(
                value_expected=power_values_per_timestep[i],
                commodity_quantity=measurement,
            )
            power_values.append(powerValue)

        return PowerForecastElement(
            duration=Duration(root=int(millisconds_step)),
            power_values=power_values,
        )

    def convert_power_events(
        self, events: List[PowerEvent]
    ) -> List[PowerForecastElement]:

        elements = []

        for event in events:
            elements.append(
                PowerForecastElement(
                    duration=Duration(
                        root=int((event.end - event.start).total_seconds() * 1000)
                    ),
                    power_values=[
                        PowerForecastValue(
                            value_upper_limit=event.power.max(),
                            value_upper_95PPR=event.power.quantile(0.95),
                            value_upper_68PPR=event.power.quantile(0.68),
                            value_expected=event.power.mean(),
                            value_lower_68PPR=event.power.quantile(0.32),
                            value_lower_95PPR=event.power.quantile(0.05),
                            value_lower_limit=event.power.min(),
                            commodity_quantity=event.commodity_quantity,
                        )
                    ],
                )
            )

        return elements

    """ ================= Control Type Details ================= """

    def provide_flexibility_information(self):
        """
        Here the flexibility has to be defined for the activated control type.
        """
        pass

    def create_PPBC(self, starttime: datetime) -> PPBCPowerProfileDefinition:
        pass

    def create_PEBC_power(self, starttime: datetime) -> PEBCPowerConstraints:
        pass

    def create_PEBC_energy(self, starttime: datetime) -> PEBCEnergyConstraint:
        pass

    def create_OMBC(self, starttime: datetime) -> OMBCSystemDescription:
        pass

    def create_FRBC(self, starttime: datetime) -> FRBCSystemDescription:
        pass

    def create_DDPC(self, starttime: datetime) -> DDBCSystemDescription:
        pass
