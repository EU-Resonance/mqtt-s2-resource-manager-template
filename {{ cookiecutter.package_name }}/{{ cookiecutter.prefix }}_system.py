from datetime import timedelta
import threading
import uuid
import json
from typing import List

from common.device import Device
from common.power_data_connector import PowerDataConnector
from common.model_interface import PowerForecastInterface
from {{ cookiecutter.package_name }}.{{ cookiecutter.prefix }}_power_adapter import {{ cookiecutter.class_prefix }}DataConnector
{% if cookiecutter.with_model == "yes" %}
from {{ cookiecutter.package_name }}.{{ cookiecutter.prefix }}_model_caller import {{ cookiecutter.class_prefix }}ForecastModel
{% endif %}

from s2python.common import (
    ResourceManagerDetails, 
    Role, 
    RoleType, 
    ControlType, 
    Currency, 
    CommodityQuantity, 
    Commodity
)
{% set raw_ct = cookiecutter.available_control_types.split(',') | map('trim') | map('lower') | list %}
{% if raw_ct | length == 6 and 'none' in raw_ct %}
  {% set control_types = raw_ct | reject('equalto', 'none') | list %}
{% else %}
  {% set control_types = raw_ct %}
{% endif %}
{% set mapping_ct = {
  'pebc': 'ControlType.POWER_ENVELOPE_BASED_CONTROL',
  'frbc': 'ControlType.FILL_RATE_BASED_CONTROL',
  'ombc': 'ControlType.OPERATION_MODE_BASED_CONTROL',
  'ppbc': 'ControlType.POWER_PROFILE_BASED_CONTROL',
  'ddbc': 'ControlType.DEMAND_DRIVEN_BASED_CONTROL',    
  'none': 'ControlType.NOT_CONTROLABLE',
} %}
{% set raw_msm = cookiecutter.measurement.split(',') | map('trim') | map('lower') | list %}
{% set mapping_msm = {
  'l1': 'CommodityQuantity.ELECTRIC_POWER_L1',
  'l2': 'CommodityQuantity.ELECTRIC_POWER_L2',
  'l3': 'CommodityQuantity.ELECTRIC_POWER_L3',
  '3phase': 'CommodityQuantity.ELECTRIC_POWER_3_PHASE_SYMMETRIC',
  'temperature': 'CommodityQuantity.HEAT_TEMPERATURE',
  'heat_flow_rate': 'CommodityQuantity.HEAT_FLOW_RATE'
} %}
{% set raw_roles = cookiecutter.device_role.split(',') | map('trim') | map('lower') | list %}
{% set role_map = {
  'producer': 'RoleType.ENERGY_PRODUCER',
  'consumer': 'RoleType.ENERGY_CONSUMER',
  'storage':  'RoleType.ENERGY_STORAGE',
} %}
{% set com_map = {
  'electricity': 'Commodity.ELECTRICITY',
  'heat':        'Commodity.HEAT',
  'gas':         'Commodity.GAS',
  'oil':         'Commodity.OIL',
} %}
{% set raw_roles = cookiecutter.device_role
    .split(',')
    | map('trim')
    | map('lower')
    | list
%}

class {{ cookiecutter.class_prefix }}System(Device):

    def __init__(self):
        super().__init__()

        # S2 specific configurations
        self.availableControlTypes = [
            {% for ct in control_types if ct in mapping_ct %}
                {{ mapping_ct[ct] }},
            {% endfor %}
        ]
        self.measurements = [
            {% for msm in raw_msm if msm in mapping_msm %}
                {{ mapping_msm[msm] }},
            {% endfor %}
        ]
        self.roles = [
            {% for item in raw_roles if ':' in item %}
                {% set r = item.split(':', 1)[0].strip() %}
                {% set c = item.split(':', 1)[1].strip() %}
                Role(role={{ role_map[r] }}, commodity={{ com_map[c] }}),
            {% endfor %}
            ]
    
        # read MQTT connection details from environment
        self.mqttCEM = self.getConfig()
        self.timezone = self.mqttCEM.get('timezone', 'Europe/Berlin')
        self.{{ cookiecutter.prefix }}Details = self._load_{{ cookiecutter.prefix }}_config()
        self.rmd = self._set_rm_details()
        {% if cookiecutter.with_model == "yes" %}self.model_config = self._load_model_config()
        self.model = self._set_model(){% endif %}
        self.datasource = self._set_power_data_connector()

        self.stop_transmission = threading.Event()  # Shared flag for stopping the thread

    def stop(self):
        self.stop_transmission.set()  # Signal the thread to stop
        


    def _set_rm_details(self):
        return ResourceManagerDetails(
            message_type="ResourceManagerDetails",
            message_id=uuid.uuid4(),
            resource_id=self.rmUUID,
            name="{{ cookiecutter.name }}",
            roles=[
            {% for item in raw_roles if ':' in item %}
                {% set r = item.split(':', 1)[0] %}
                {% set c = item.split(':', 1)[1] %}
                Role(
                    role={{ role_map[r] }},
                    commodity={{ com_map[c] }},
                ),
            {% endfor %}
            ],
            manufacturer="N/A",
            model="N/A",
            serial_number="N/A",
            firmware_version="N/A",
            instruction_processing_delay=100,
            available_control_types=self.availableControlTypes,
            currency=Currency.EUR,
            provides_forecast={% if cookiecutter.with_model == "yes" %}True{% else  %}False{% endif  %},
            provides_power_measurement_types=self.measurements
        )

    {% if cookiecutter.with_model == "yes" %}
    def _set_model(self):
        # Set forecast horizon to 6 hours
        horizon_hours = int(self.model_config.get("horizon"))
        self.set_horizon(timedelta(hours=horizon_hours))
        
        # Model-Type: choose btw lstm , gru, rfr, h1 or h2 - set in config.json
        return {{ cookiecutter.class_prefix }}ForecastModel(
            {{ cookiecutter.prefix }}_details = self.{{ cookiecutter.prefix }}Details,
            model_params = self.model_config
        ){% endif  %}

    
    def _set_power_data_connector(self):

        return {{ cookiecutter.class_prefix }}DataConnector(
            {{ cookiecutter.prefix }}_details = self.{{ cookiecutter.prefix }}Details,
            measurements = self.measurements,
            timezone = self.timezone,
            {% if cookiecutter.with_model == "yes" %}model = self.get_model(){% endif %}
        )
    

    """ Load device specific config data """

    def _load_{{ cookiecutter.prefix }}_config(self):
        with open('./{{ cookiecutter.prefix }}_rm_interface/resources/config.json', 'r') as f:
            config = json.load(f)
        return config.get('{{ cookiecutter.prefix }}_details', {})

    {% if cookiecutter.with_model == "yes" %}
    def _load_model_config(self):
        with open('./{{ cookiecutter.prefix }}_rm_interface/resources/config.json', 'r') as f:
            config = json.load(f)
        return config.get('{{ cookiecutter.prefix }}_model', {}){% endif  %}  
    
    """ ================= Device Interface Methods ================= """

    def get_roles(self) -> List[Role]:    
        return self.roles

    def getAvailableControlTypes(self) -> List[ControlType]:
        return self.availableControlTypes
    
    {% if cookiecutter.with_model == "yes" %}def get_model(self) -> PowerForecastInterface:
        """Return the forecasting model."""
        return self.model{% endif  %}

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

{% if cookiecutter.with_model == "yes" %}
    def set_horizon(self, horizon: timedelta):
        self.horizon = horizon

    def get_horizon(self) -> timedelta:
        return self.horizon
{% endif %}
