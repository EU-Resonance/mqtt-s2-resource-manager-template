
# Example PV System
This branch provides an example output of the cookiecutter generation process from the `main` branch. It documents each step so you can replicate it for other Resource Manager (RM) interfaces.

 1. Code generation based on 10 questions
 2. Edit `environment.env` and `config.json`
 3. Test against CEM interface
 4. Extend the code and customize to your flexibility

## 1. Generation Process

From the repository root, use cookiecutter to start the process:

```bash
uvx cookiecutter .
```

Then the following questions were answered:

```bash
  [1/10] name (My Device): My Pv System
  [2/10] prefix (xx): pv
  [3/10] package_name (pv_rm_interface): 
  [4/10] class_prefix (Pv): 
  [5/10] device_role (producer:electricity): producer:electricity
  [6/10] available_control_types (pebc, ombc, ppbc, frbc, ddbc, none): pebc
  [7/10] measurement (L1, L2, L3, 3phase, temperature, heat_flow_rate): 3phase
  [8/10] Select with_model
    1 - no
    2 - yes
    Choose from [1/2] (1): 2
  [9/10] Select create_new_branch
    1 - no
    2 - yes
    Choose from [1/2] (1): 2
  [10/10] Select run_tests
    1 - no
    2 - yes
    Choose from [1/2] (1): 2
```

After that, the code is auto-formatted to fill cookiecutter gaps and basic tests are run. Finally, device-specific files are created in `pv_rm_interface/`:

- `pv_system.py`: defines `PvDevice` as the device instance, containing all **ResourceManagerDetails** information and managing the power adapter and model interface.
- `pv_power_adapter.py`: defines `PvDataConnector`, which provides the `read_current_power()` method to define the source of power measurement data.
- `pv_model_caller.py`: defines `PvForecastModel`, which provides the `get_forecast()` method to calculate a time-series power forecast (in this case _generation_) that is called by the `PvDataConnector`.
- `main.py`: initiating discovery, data transmission, and response handling.
- `Dockerfile` and `compose.yaml`: Enable containerized deployment/testing of this service
- `resources/config.json`: Place to provide resource-specific secrets (endpoints, API tokens, etc.)

The template file `cookiecutter.json` as well as the folders `{{ cookiecutter.package_name }}/` and `hooks/` are not needed anymore and were removed from the new `device/pv` branch.

### 2. Configuration

Next, `environment.env.example` was renamed to `environment.env`, where you can provide your connection details. For testing with Docker Compose, it was set to:
```
TZ=Europe/Berlin
MQTT_SERVER=host.docker.internal
MQTT_PORT=1883
```

To configure the two main interfaces to your device, `read_current_power()` and `get_forecast()`, you may need site-specific inputs. These can be provided in `resources/config.json` (in `.gitignore`), for example:

```JSON
{
    "pv_details": {
        "lon": "11.59",
        "lat": "48.17",
        "peak_power": "50",
        "power_api": "https://mysolarapi.inverter"
    },
    "pv_model": {
        "weather_api": "https://some-weather-service.io/forecast",
        "model_type": "lstm",
        "stepsize": "15min",
        "horizon": "24"
    }
}
```

The `"pv_details"` and `"pv_model"` values are automatically passed to the power adapter and model interface instances, respectively, and can be used there to implement, for example, a basic API call in `read_current_power()`:

```python
import requests

def __init__(self, pv_details,...):
  ...
  self.api_connection = pv_details.get('power_api')

def read_current_power(self) -> float:
  try:
    response = requests.get(self.api_connection)
    data = response.json()
    value = data["main"]["currentPower"]
    return value
```

> **Note:** [Pull Request #1](https://github.com/EU-Resonance/mqtt-s2-resource-manager-template/pull/1) will offer a new way to semantically fetch resource data via an SAREF4ENER-based ontology using MQTT.

In the same way, you can modify `PvForecastModel.get_forecast()` and implement or link your forecast model (providing forecasts is optional).


### 3. Test Setup

If `run_tests=yes` is chosen in step 1, the generated `compose.yaml` contains a broker, a CEM interface, and a visualization service for testing. You can start the test setup with:

```bash
docker compose -f pv_rm_interface/compose.yaml up -d
```
(Older versions of Docker need to use `docker-compose ...` instead of `docker compose`.)

Then go to [http://localhost:5001](http://localhost:5001) and monitor the data received by a CEM.

> **Note:** PEBC is configured in this test (placeholder values), so you can directly start and test the system using `docker compose -f pv_rm_interface/compose.yaml up -d`.


### 4. Customization

The most resource-specific part will be the choice and configuration of control types. Have a look at [the S2 Standard website](https://s2standard.org/) for guidance on this.

In the current codebase, this is defined in `provide_flexibility_information()` in `PvDataConnector`. Since `pebc` was chosen in step 1, a PEBC flexibility information example is already configured after generation and can be adjusted according to your needs.

For other Control Type descriptions, only the skeleton is provided, since more in-depth knowledge of the resource and the S2 data model is needed.


### Integration as a Package

For deeper integration, you can also install the RM interface as a Python package in your existing environment using
```
pip install -e .
```
This allows you to import it in your codebase, similar to `pv_rm_interface/main.py`, and use its methods from within your own project or RM controller, as shown below.


```python
import threading
from s2python.common import ControlType
from pv_rm_interface.pv_system import PvSystem

def handle_callbacks(callback, pv_device):
  """Callback function for handling the CEM control and activation messages"""

  if isinstance(callback, ControlType):
    pv_device.activeControlType = callback
    pv_device.sendSystemDescription()

# Create PV RM instance
pv_device = PvSystem()

# Start the device with CEM discovery
pv_device.startDiscovery(
  config=pv_device.mqttCEM,
    onCemDiscovered=lambda cemUUID: pv_device.startRmSubscription(
        pv_device.mqttCEM,
        rmCallback=lambda callback: handle_callbacks(callback, pv_device),
    ),
)

# Start transmission thread, updateing the power measurement (and power forecast) every 60 seconds
thread = threading.Thread(
  target=pv_device.startDataTransmission,
  args=( pv_device.mqttCEM.get("timezone"), 60 ),  
  daemon=True,
)
thread.start()
```
