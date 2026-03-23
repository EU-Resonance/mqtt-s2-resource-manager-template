import logging
from datetime import timedelta

import pandas as pd

from common.model_interface import PowerForecastInterface


class PvForecastModel(PowerForecastInterface):
    def __init__(
        self, pv_details, model_params, horizon: timedelta = timedelta(hours=1)
    ):
        self.param = pv_details.get("param")
        self.model_param = model_params.get("model_param")
        self.horizon = timedelta(hours=int(model_params.get("horizon")))

    def get_forecast(self):
        try:
            # model_path = './pv_rm_interface/resources/models/'
            # LSTM = joblib.load(model_path + 'LSTM_Model.pkl')

            # model_input = self.get_model_input()
            # p = self.prediction(model_input, model_param)

            # if isinstance(p, (list, tuple)):
            #     result_list = [float(x) for x in p]

            return pd.Series([50.0, 55.0, 60.0, 65.0, 70.0, 75.0])

        except Exception as e:
            logging.error(f"Error in prediction: {e}")
            return -1

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
