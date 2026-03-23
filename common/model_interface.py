from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

import pandas as pd
from s2python.common import CommodityQuantity


class Event:
    """Abstract base class, that has an start_time, ent_time and any list of arguments."""

    def __init__(self, start_time: datetime, end_time: datetime, **kwargs):
        self.start = start_time
        self.end = end_time
        self.args = kwargs


class PowerEvent(Event):
    """Extends Event class with power and commodityQuantity to be used for EN 50941-12-2 messages."""

    def __init__(
        self,
        start_time: datetime,
        end_time: datetime,
        power: pd.Series,
        commodity: CommodityQuantity = CommodityQuantity.ELECTRIC_POWER_3_PHASE_SYMMETRIC,
        **kwargs,
    ):
        super().__init__(start_time, end_time, **kwargs)
        self.power = power
        self.commodity_quantity = commodity


class PowerForecastInterface(ABC):
    """Abstract base class for forecasting models."""

    @abstractmethod
    def get_forecast(self) -> pd.DataFrame:
        """Generate a forecast (not linked to Events) to be used e.g. for flexibility calculation."""
        pass

    @abstractmethod
    def get_forecast_for_event(
        self,
        event: Event,
        commodity: CommodityQuantity = CommodityQuantity.ELECTRIC_POWER_3_PHASE_SYMMETRIC,
    ) -> PowerEvent:
        """Generate a forecast specific to the provided event."""
        pass

    @abstractmethod
    def get_forecast_for_sequence(
        self,
        events: List[Event],
        commodity: CommodityQuantity = CommodityQuantity.ELECTRIC_POWER_3_PHASE_SYMMETRIC,
    ) -> List[PowerEvent]:
        """
        Generate forecasts for a sequence of events (e.g. current schedule).

        :param events: List of Event objects.
        :return: A pandas Series containing power forecast data for the events.
        """
        pass
