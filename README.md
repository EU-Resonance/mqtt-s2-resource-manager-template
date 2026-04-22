# S2 Resource Manager SDK

This repository provides a Python framework for implementing EN‑50491‑12‑2 (**S2 Standard**) compliant Resource Managers (**RM**) interfaces for any device (PV, heat pump, storage, EV charger, …) that enables communication with a Central Energy Manager (**CEM**) via MQTT.  



#### Acknowledgements 
This work is based on the work of the RESONANCE research project (Grant Agreement no. 101096200) and will be advanced within the INDEPENDENT project (Grant Agreement no. 101172675). Native S2 data classes are provided by the `s2-python` [project](`https://github.com/flexiblepower/s2-python`).

A documentation of the **S2 Standard** and support in using it to define flexibility can be found under https://docs.s2standard.org/

#### Prerequisites 
To work with this repository you only need **Python >= 3.10** and **`uv`**, a fast Python package manager.  Please follow the official installation instructions for your platform: https://docs.astral.sh/uv/.

**Docker** *(optional)* — required to run the RM as a container and for End-to-End Verification. Install from https://docs.docker.com/get-docker/.



## Quick Start

This **End-to-End Test Setup** creates a RM container from this repo that offers all five Control Types. The second command pulls external images for a CEM interface and a mosquitto broker to locally showcase the communication.

```
uvx cookiecutter . --no-input run_tests=yes
docker compose -f xx_rm_interface/compose.yaml up -d
```



> **Note:** Only **PEBC** is configured in this test (placeholder values), so you will receive validation errors for **OMBC**, **PPBC**, **FRBC** and **DDBC** unless you configure them manually.

## SDK Architecture

The SDK provides:

- a reusable RM abstraction (`Device`)
- standardized MQTT communication (`RMClient`)
- interfaces for power measurements `power_data_connector.py` and resource model (forecasting) `model_interface.py`
- a cookiecutter template to bootstrap new RM implementations

The `common/` package is intentionally device‑agnostic and should not contain device‑specific logic. All resource specific implementation is defined in the child classes, that are generated in the respective interface folder.

```
root/
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
└── <prefix>_rm_interface/       # device interface implementation
```

### Example PV System
An example implementation for a PV system is available in the `device/pv` branch, which demonstrates:
- device configuration in `pv_rm_interface/pv_system.py`
- measurement ingestion (reading csv data) in `pv_rm_interface/pv_power_adapter.py`
- forecast generation in `pv_rm_interface/pv_model_caller.py`
- S2-compliant message exchange and control type activation with a CEM

### Using the Interface in Your Codebase

For a deeper integration, you can install the generated device-specific part as a Python package in any environment using

```
uv pip install -e .
```
This allows you to import it in your codebase and use its helper functions from within your own project or RM controller.

    

## Generate a New RM Interface

From the repository root, use cookiecutter to start the process

```
uvx cookiecutter .
```

You will be asked questions related to the **S2 standard** about available control types, measurements, roles (see https://s2standard.org for more information) and if your resource provides a model for generating power forecasts (yes/no). 

Cookiecutter will generate the skeleton of your RM code in a new `<prefix>_rm_interface` project folder. However, the connection to your physical device or data source (where to read power data / write control commands) must be defined in your custom implementation.

You can then refine your implementation as described below.


| Generated files                 | What you have to add                                                                                                                                                                                                                                    |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `<prefix>_rm_interface/`        |                                                                                                                                                                                                                                                         |
| ├──`<prefix>_power_adapter.py`  | How measurements / power consumption data is provided<br><br>For the chosen control types, you have to provide the corresponding **flexibility information in form of S2 data classes**.<br><br>See https://docs.s2standard.org/docs/welcome/ for help. |
| ├──`resources/config.json`      | *(Optional, local only)* Runtime configuration such as API endpoints, model input and resource-specific parameters. **Do not commit this file**.                                                                                                                                                       |
| ├──`<prefix>_system.py`         | _(Optional)_ Get parameters from your `config.json`and pass them to the `power_adapter` and `model_caller` (e.g. forecast horizon)                                                                                                                      |
| ├──`<prefix>_model_caller.py`   | *(Optional)* Implement or link your resource model here if it can predict power consumption.                                                                                                                                                       |
| ├──`test/cem_onboarding.py`<br> | *(Optional)* Use/Change for testing                                                                                                                                                                                                                     |
| └──`main.py`                    |                                                                                                                                                                            

After generation, you may delete the cookiecutter.json as well as the template and 'hooks' folder.                               

---
### Configure TLS

The current implementation assumes **plain MQTT over TCP** by default, but supports TLS configuration via the `environment.env` file.

- **Port selection**
  - The MQTT port is taken from `MQTT_PORT` (environment) or the `port` field in the `config` dict.
  - If TLS is used, the typical port is **8883**; otherwise the default is **1883**.
- **TLS status**
  - TLS is configured in `common/messaging.py` based on:
    - `ca_cert` / `MQTT_CA_CERT`
    - `certfile` / `MQTT_CERTFILE`
    - `keyfile` / `MQTT_KEYFILE`
  - If any of these are provided or the port is `8883`, the SDK enables TLS using `ssl.PROTOCOL_TLS_CLIENT`.
- **Certificate fields**
  - `MQTT_CA_CERT` / `ca_cert`: path to a CA certificate bundle.
  - `MQTT_CERTFILE` / `certfile`: path to the client certificate.
  - `MQTT_KEYFILE` / `keyfile`: path to the client private key.
  - For mutual TLS, both `certfile` and `keyfile` must be provided.





## Developing with the SDK

### Set Up the Virtual Environment

With the generated `pyproject.toml` you can wrap all dependencies in a virtual environment by using

```
uv sync
```
`uv` creates a local `.venv/` folder, in which all dependencies from `pyproject.toml` are installed

If additional libraries are needed (typically for forecast models), you can either add them manually to `pyproject.toml` or use `uv add <package-name>` before building the Docker image.
```
uv add keras tensorflow sklearn
```

In general, `uv` automatically uses the correct virtual environment when running commands.  
Manual activation is usually not required, but if you want to activate the `.venv` manually, use 
- `.venv\Scripts\Activate` *(Windows*) 
- `source .venv/bin/activate` *(macOS / Linux*) 
- `deactivate` to leave the virtual environment.



### Testing Against a CEM

To test the Resource Manager interface, an MQTT-based CEM counterpart is needed. The RM and CEM exchange messages according to EN-50491-12-2, Chapter 9.

`   [RM]   <-- S2/JSON -->   [MQTT Broker]  <-- S2/JSON-->  [CEM]`

To establish the connection with a CEM, the current implementation looks for a CEM's _alive-message_ published to the connected mqtt-broker under the topic
`/resonance/cem/{cem_uuid}` :

```JSON
{
  "message_id": "7ff6626c-856e-492a-82b3-87f6d0f438cb",
  "message_type": "CEM_ALIVE_MESSAGE"
}
```

A (dummy) CEM interface which emulates this behaviour and responds to the RM messages and can be set up by
```
docker run -d \
  --name cem_interface \
  -p 127.0.0.1:5000:5000 \
  --env-file environment.env \
  harbor.need.energy/resonance/cem_interface:latest
```

> **Note:** If you start this from the repository root, it will use the same `.env` file (same MQTT connection) as your RM. If you use a local mosquitto container as MQTT broker, set `MQTT_SERVER=host.docker.internal`.

### MQTT & Message Flow (Conceptual)

- RMs act as **clients** to a shared MQTT broker and use S2‑shaped JSON payloads.
- Onboarding typically starts with an S2 `ResourceManagerDetails` message from the RM to the CEM.
- The CEM responds with a `responseMessage` on a dedicated topic using the UUIDs of RM and CEM.
- Measurements and forecasts are published on resource‑specific topics to avoid feedback loops and self‑subscriptions.


## Troubleshooting
- Validation errors from `s2python`: ensure you use `PowerForecastValue` (with `value_expected`) for forecasts, and `Duration(root=int_ms)` for element durations.
- Feature shape/dtype issues: the PV model pipeline coerces dataframe columns to numeric and enforces the expected 12-feature order prior to inference.
- Forecast length vs. element duration: the per-element duration is `total_horizon / len(forecast_values)`.



## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.