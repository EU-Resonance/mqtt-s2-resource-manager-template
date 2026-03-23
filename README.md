## S2 Resource Manager SDK

This repository hosts the **generic Resource Manager (RM) SDK** for building EN‑50491‑12‑2 (S2) compliant MQTT Resource Managers for any device (PV, heat pump, storage, EV charger, …).  

All S2 data classes are provided by the `s2-python` [package](`https://github.com/flexiblepower/s2-python`). The SDK wraps those types and adds MQTT transport, topic naming and basic validation.
##### Prerequisites 
To work with this repository you only need **`uv`**, a fast Python package manager.  Please follow the official installation instructions for your platform: https://docs.astral.sh/uv/

Also Python >= 3.10


### Quick Start

- Install **uv** (e.g. `pip install uv`)
- `uvx cookiecutter .`
   - Answer questions ➜ Code is generated
- `uv sync` from the project root containing now:
   - common/
   - <prefix>_rm_interface/ (generated)
   - pyproject.toml (generated)
   - uv.lock
- Copy `environment.env.example` to `environment.env` and edit `MQTT_SERVER=` and `MQTT_PORT=`
- `uv run --env-file environment.env python -m <prefix>_rm_interface.main`
- or using docker
  `<prefix>_rm_interface/$ docker compose up -d --build`

If a MQTT broker is running at the given endpoint, the RM will connect and automatically provide S2 information to a CEM.



---
## Generate a new Resource Manager (RM)

From the repository root, use cookiecutter 

```
uvx cookiecutter .
```

You will be asked questions related to the S2 standard about available control types, measurements, roles (see s2standard.org for more info) and if your resource provides a model for generating and providing power forecasts (yes/no).

Cookiecutter will generate the skeleton of your RM code in a new `<prefix>_rm_interface` project folder to connect your device to any MQTT-based Customer Energy Manager (CEM).


### MQTT broker

To test the communication with a local MQTT broker like Eclipse Mosquitto (https://hub.docker.com/_/eclipse-mosquitto), the easiest way is creating a minimal `mosquitto.conf`
``` conf
listener 1883
allow_anonymous true
```
and then run
```
docker run -d --name mqtt-broker -p 1883:1883 eclipse-mosquitto
```

Create an `environment.env` file in the project root with the connection details of your broker e.g.

```environment.env
TZ=Europe/Berlin
MQTT_SERVER=host.docker.internal
MQTT_PORT=1883
```

### Secure MQTT (TLS)

The current implementation assumes **plain MQTT over TCP** by default, but supports enabling TLS via configuration.

- **Port selection**
  - The MQTT port is taken from `MQTT_PORT` (environment) or the `port` field in the `config` dict.
  - If TLS is used, the typical port is **8883**; otherwise the default is **1883**.
- **TLS status**
  - TLS is configured in `common/messaging.py` based on:
    - `ca_cert` / `MQTT_CA_CERT`
    - `certfile` / `MQTT_CERTFILE`
    - `keyfile` / `MQTT_KEYFILE`
  - If any of these are provided or the port is `8883`, TLS will be enabled using `ssl.PROTOCOL_TLS_CLIENT`.
- **Certificate fields**
  - `MQTT_CA_CERT` / `ca_cert`: path to a CA certificate bundle.
  - `MQTT_CERTFILE` / `certfile`: path to the client certificate.
  - `MQTT_KEYFILE` / `keyfile`: path to the client private key.
  - For mutual TLS, both `certfile` and `keyfile` must be provided.


### Run RM via Docker

The container is started via docker compose in the project folder
```
cd <prefix>_rm_interface
docker compose up -d --build
```

### Run manually

You can also manually run the script using
```
uv run python -m <prefix>_rm_interface.main
```
or by using the sandbox test script to try out things
```
python -m <prefix>_rm_interface.test.cem_onboarding
```

### Testing

For usign `pytest` run 
```
uv run pytest <prefix>_rm_interface/.
```

### Communication with a CEM

`   [RM]   <-- S2/JSON -->   [MQTT Broker]  <-- S2/JSON-->  [CEM]`

To test all functionalities, a MQTT-based counter-interface is needed.
This will be provided as docker image in a harbor registry soon.

---

# Customize your interface

With respect to the questionnaire, the generated files will be best suited to your application and most of the logic is additionally provided by the SDK in the `common/` files 

However, the final link to your resource (read power data / write control commands) has to come from your custom implementation. 

You should customize the generated code as depicted in the following table

| Generated files                 | What you have to add                                                                                                                                                                                                                                    |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<prefix>_rm_interface/`        |                                                                                                                                                                                                                                                         |
| ├──`<prefix>_power_adapter.py`  | How measurements / power consumption data is provided<br><br>For the chosen control types, you have to provide the corresponding **flexibility information in form of S2 data classes**.<br><br>See https://docs.s2standard.org/docs/welcome/ for help. |
| ├──`resources/config.json`      | *(Optional, local only)* Runtime configuration such as API endpoints, model input and resource-specific parameters. **Do not commit this file**.                                                                                                                                                       |
| ├──`<prefix>_system.py`         | _(Optional)_ Get parameters from your `config.json`and pass them to the `power_adapter` and `model_caller` (e.g. forecast horizon)                                                                                                                      |
| ├──`<prefix>_model_caller.py`   | *(Optional)* If you have a resource model, that can predict its power consumption, add this here.                                                                                                                                                       |
| ├──`test/cem_onboarding.py`<br> | *(Optional)* Use/Change for testing                                                                                                                                                                                                                     |
| └──`main.py`                    |                                                                                                                                                                                                                                                         |


##### Create / update the virtual environment

With the generated `pyproject.toml` you can wrap all dependencies in a virtual environment by using

```
uv sync
```
`uv` creates a local `.venv/` folder, with all dependencies from `pyproject.toml` are installed

If additional libraries are needed (typically for forecast models), you can either add them manualy to `pyproject.toml` or use `uv add <package-name>` before building the docker image.
```
uv add keras tensorflow sklearn
```

In General `uv` automatically uses the correct virtual environment when running commands.  
Manual activation is usually not required, but if you want to activate the `.venv` manually, use 
- `.venv\Scripts\Activate` *(Windows*) 
- `source .venv/bin/activate` *(macOS / Linux*) 
- `deactivate` to leave the virtual environment.
## Using the interface in your codebase

For a deeper integration, you can also install this device-specific part as a python package in any environment
```
uv pip install -e .
```
In that way, you can import in your code and use all of its logic and helper functions from within your own project or resource controller.


## Core SDK Concepts
---
```plaintext
sampleRMs/
├── common/                      ← generic SDK: S2 + MQTT building blocks
│   ├── device.py                ← base `Device` (RM) abstraction
│   ├── power_data_connector.py  ← data adapter base + S2 helpers
│   ├── model_interface.py       ← forecasting/model interface
│   ├── rmClient.py              ← MQTT client + topic wiring
│   └── messaging.py             ← Paho MQTT integration
│
├── cookiecutter.json            # RM project template configuration
├── hooks/                       # Cookiecutter validation & setup logic
│   ├── pre_gen_project.py
│   └── post_gen_project.py
│
└── <prefix>_rm_interface/     # e.g. hp_rm_interface, pv_rm_interface, ...
```

- **`common/device.py`**  
  Base class representing a single S2 Resource Manager. Subclasses must provide:
  - `get_rm_details()` → returns `ResourceManagerDetails`
  - `get_power_data_connector()` → returns a `PowerDataConnector`
  - `get_model()` → returns a `PowerForecastInterface` (optional, only if forecasting is provided)
- **`common/power_data_connector.py`**  
  Abstracts how **measurements** and **forecasts** are obtained from a device or data source and converted into S2 messages. It provides helpers to build:
  - `PowerValue`
  - `PowerForecastValue`
  - `PowerForecastElement`
  - `Duration`
- **`common/model_interface.py`**  
  Defines the contract for forecasting models. Any implementation (rule‑based, ML model, external service) can be plugged in as long as it adheres to this interface.


The `common/` package is intentionally device‑agnostic and should **not** contain device‑specific logic. Each concrete RM instance is implemented in its own `<device>_rm_interface/` folder and ideally uses a dedicated feature branch 


---


## MQTT & Message Flow (Conceptual)

- RMs act as **clients** to a shared MQTT broker and use S2‑shaped JSON payloads.
- Onboarding typically starts with an S2 `ResourceManagerDetails` message from the RM to the CEM.
- The CEM responds with a `responseMessage` on a dedicated topic using the UUIDs of RM and CEM.
- Measurements and forecasts are published on resource‑specific topics to avoid feedback loops and self‑subscriptions.


## Troubleshooting
- Validation errors from `s2python`: ensure you use `PowerForecastValue` (with `value_expected`) for forecasts, and `Duration(root=int_ms)` for element durations.
- Feature shape/dtype issues: the PV model pipeline coerces dataframe columns to numeric and enforces the expected 12-feature order prior to inference.
- Forecast length vs. element duration: the per-element duration is `total_horizon / len(forecast_values)`.

---

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.