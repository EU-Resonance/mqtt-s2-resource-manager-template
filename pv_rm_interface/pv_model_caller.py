import logging
import pandas as pd
from datetime import datetime, timedelta

from common.model_interface import PowerForecastInterface


class PvForecastModel(PowerForecastInterface):
    def __init__(
        self, pv_details, model_params, horizon: timedelta = timedelta(hours=1)
    ):
        self.param = pv_details.get("param")
        self.model_param = model_params.get("model_param")
        self.horizon = timedelta(hours=int(model_params.get("horizon")))

    def get_forecast(self):
        """Return PV forecast series from now for the configured horizon."""

        start_time = pd.Timestamp(start.replace(second=0, microsecond=0)).tz_localize(None).replace(year=2020)
        end_time = start_time + self.horizon

        filtered_df = self.df.loc[start_time:end_time]

        if filtered_df.empty:
            return pd.Series(dtype=float)

        resampled_df = (
            filtered_df[["Normalized Production [0..1]"]]
            .resample(self.fc_res)
            .mean()
            .interpolate(method="time")
            .bfill()
            .ffill()
        )

        forecast_series = self.peak_power * resampled_df["Normalized Production [0..1]"]
        forecast_series.name = "forecast_power"

        return forecast_series

    def get_forecast_for_event(self, event, commodity):
        """Generate a forecast specific to the provided event."""
        # This method is not implemented in this example.
        pass

    def get_forecast_for_sequence(self, events, commodity):
        """Generate forecasts for a sequence of events (e.g. current schedule)."""
        # This method is not implemented in this example.
        pass

    def get_model_input(self):
        """Fetch external model input data"""
        pass

    def prediction(self, model_input, model_param):
        """Calculate predicted power consumption / generation"""
        pass
