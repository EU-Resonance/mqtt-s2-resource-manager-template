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
{% if cookiecutter.with_model == "yes" %}
from common.model_interface import PowerForecastInterface{% endif %}

from s2python.pebc import PEBCPowerConstraints, PEBCEnergyConstraint, PEBCPowerEnvelopeLimitType, PEBCPowerEnvelopeConsequenceType, PEBCAllowedLimitRange
from s2python.ombc import OMBCSystemDescription, OMBCOperationMode
from s2python.frbc import FRBCSystemDescription, FRBCActuatorDescription, FRBCStorageDescription
from s2python.ppbc import PPBCPowerProfileDefinition, PPBCPowerSequenceContainer
from s2python.ddbc import DDBCSystemDescription, DDBCActuatorDescription
from s2python.common import (
    PowerValue,
    PowerForecastValue,
    CommodityQuantity,
    PowerForecastElement,
    NumberRange, 
    Transition, 
    Timer
)
{% set raw_ct = cookiecutter.available_control_types
    .split(',')
    | map('trim')
    | map('lower')
    | list
%}

class {{ cookiecutter.class_prefix }}DataConnector(PowerDataConnector):
        
    # This init method is used to process the power data from any source
    def __init__(self, 
                {{ cookiecutter.prefix }}_details,
                measurements, 
                timezone: str,
                {% if cookiecutter.with_model == "yes" %}model : PowerForecastInterface{% endif %}):
        
        self.measurements = measurements
        self.timezone = timezone
        {% if cookiecutter.with_model == "yes" %}self.model = model{% endif %}   

    # Read details to access current power from a database or api
    '''
        self.mqtt_connection = {{ cookiecutter.prefix }}_details.get('mqtt_connection')
        self.db_connection = {{ cookiecutter.prefix }}_details.get('db_connection')
        self.api_connection = {{ cookiecutter.prefix }}_details.get('api_connection')
    '''



    def read_current_power(self) -> float:
        ''' Get the current power from any source '''
        return 50.0

    


    # REQUIRED METHOD:
    # returns the current power data for each commodity quantity
    def get_power_values_per_commodity(self)-> List[PowerValue]:

        power_values_per_commody = []

        for measurement in self.measurements:
            # get the power value for each Commodity Quantitty in measurements
            power_value = self.convert_power_values(measurement, power_value = self.read_current_power())
            power_values_per_commody.append(power_value) 

        return power_values_per_commody

    

    # REQUIRED METHOD:
    # returns the power forecast values for a given horizon
    def get_power_forecast_elements(self) -> List[PowerForecastElement]:
        {% if cookiecutter.with_model == "no" %}
        pass
        {% else %}
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
        {% endif %}



    ###############################################
    #   FLEXEBILITY / CONTROL TYPE DEFINITION     #
    ###############################################

    def provide_flexibility_information(self, {{ cookiecutter.prefix }}_device):
        """
        Here the flexibility has to be defined for the activated control type.
        Dummy values are only provided for PEBC
        """
        {% if not (raw_ct | length == 1 and raw_ct[0] == 'none') %}
        starttime = datetime.now(ZoneInfo(self.timezone))
        {% endif %}
        
        {% if 'pebc' in raw_ct %}
        logging.info(" >> [RM] Calculating PEBC Flexibility ")
        try:
            ll = PEBCAllowedLimitRange(
                commodity_quantity = self.measurements[0],
                limit_type = PEBCPowerEnvelopeLimitType.LOWER_LIMIT,
                range_boundary = NumberRange(
                    start_of_range = 0.0,
                    end_of_range = 0.5
                ),
                abnormal_condition_only=True
            )

            ul = PEBCAllowedLimitRange(
                commodity_quantity=self.measurements[0],
                limit_type=PEBCPowerEnvelopeLimitType.UPPER_LIMIT,
                range_boundary=NumberRange(
                    start_of_range = 4.0,
                    end_of_range = 10.0
                ),
                abnormal_condition_only=False
            )

            {{ cookiecutter.prefix }}_device.pebc_pc = PEBCPowerConstraints(
                message_type = 'PEBC.PowerConstraints',
                message_id = uuid.uuid4(),
                id = uuid.uuid4(),
                valid_from = starttime,
                valid_until = starttime + timedelta(minutes=60),
                consequence_type = PEBCPowerEnvelopeConsequenceType.DEFER,
                allowed_limit_ranges = [ll,ul]
                )

            {{ cookiecutter.prefix }}_device.pebc_ec = PEBCEnergyConstraint(
                    message_type = 'PEBC.EnergyConstraint',
                    message_id = uuid.uuid4(),
                    id=uuid.uuid4(),
                    valid_from = starttime,
                    valid_until = starttime + timedelta(minutes=60),
                    upper_average_power = 20,
                    lower_average_power = 20,
                    commodity_quantity = {{ cookiecutter.prefix }}_device.measurements[0]
                )  

        except Exception as e:
            logging.error(" !! Error defining PEBC: %s", str(e)) {% endif %}

        {% if 'ombc' in raw_ct %}
        logging.info(" >> [RM] Calculating OMBC Flexibility ")
        try:
            {{ cookiecutter.prefix }}_device.ombc = OMBCSystemDescription(
                    message_type = 'OMBC.SystemDescription',
                    message_id = uuid.uuid4(),
                    valid_from = starttime,
                    operation_modes= [OMBCOperationMode()],
                    transitions=[Transition()],
                    timers=[Timer()],
                )
        except Exception as e:
            logging.error(" !! Error defining OMBC: %s", str(e)) {% endif %}

        {% if 'ppbc' in raw_ct %}
        logging.info(" >> [RM] Calculating PPBC Flexibility ")
        try:
            {{ cookiecutter.prefix }}_device.ppbc = PPBCPowerProfileDefinition(
                    message_id = uuid.uuid4(),
                    message_type = 'PPBC.PowerProfileDefinition',
                    id = uuid.uuid4(),
                    start_time = starttime,
                    end_time = starttime + timedelta(minutes=60),
                    power_sequences_containers = [PPBCPowerSequenceContainer()]
                    )
        except Exception as e:
            logging.error(" !! Error defining PPBC: %s", str(e)) {% endif %}

        {% if 'frbc' in raw_ct %}
        logging.info(" >> [RM] Calculating FRBC Flexibility ")
        try:
            {{ cookiecutter.prefix }}_device.frbc = FRBCSystemDescription(
                    message_type = 'FRBC.SystemDescription',
                    message_id = uuid.uuid4(),
                    valid_from = starttime,
                    actuators = [FRBCActuatorDescription()],
                    storage = FRBCStorageDescription(),
                )
        except Exception as e:
            logging.error(" !! Error defining FRBC: %s", str(e)) {% endif %}

        {% if 'ddbc' in raw_ct %}
        logging.info(" >> [RM] Calculating DDBC Flexibility ") 
        try:
            {{ cookiecutter.prefix }}_device.ddbc = DDBCSystemDescription(
                    message_type = 'DDBC.SystemDescription',
                    message_id = uuid.uuid4(),
                    valid_from = starttime,
                    actuators = [DDBCActuatorDescription()],
                    present_demand_rate = NumberRange(
                                start_of_range=0,
                                end_of_range=1
                            ),
                    provides_average_demand_rate_forecast = True
                )
        except Exception as e:
            logging.error(" !! Error defining DDBC: %s", str(e)) {% endif %}



