
import time
import threading
import pytz
import logging

from s2python.common import ControlType
from {{ cookiecutter.package_name }}.{{ cookiecutter.prefix }}_system import {{ cookiecutter.class_prefix }}System

logging.basicConfig(level=logging.INFO)

def handle_callbacks(callback, {{ cookiecutter.prefix }}_device):
    ''' Callback function for handling the CEM control messages '''

    if isinstance(callback, ControlType):
        {{ cookiecutter.prefix }}_device.setControlType(callback)



{{ cookiecutter.prefix }}_device= {{ cookiecutter.class_prefix }}System()

#  connect to local mosquitto container
host = 'mosquitto'
port = 1883
logging.info(f" >$ Connecting to {host}:{port} (MQTT Broker)")

# Start the device with CEM discovery
{{ cookiecutter.prefix }}_device.startDiscovery(
    config={{ cookiecutter.prefix }}_device.mqttCEM,
    onCemDiscovered=lambda cemUUID: {{ cookiecutter.prefix }}_device.startRmSubscription(
        {{ cookiecutter.prefix }}_device.mqttCEM, 
        rmCallback=lambda callback: handle_callbacks(callback, {{ cookiecutter.prefix }}_device)
    )
)

# Wait for CEM to be discovered
logging.info(" >> Waiting for RM-CEM connection to be established... \n")
while not {{ cookiecutter.prefix }}_device.connection.on:
    time.sleep(1)

logging.info(" >> RM-CEM connection established. \n")
thread = threading.Thread(
    target={{ cookiecutter.prefix }}_device.startDataTransmission,
    args=(pytz.timezone('Europe/Berlin'), 15)
)
thread.start()

try:
    while thread.is_alive():
        time.sleep(1)
except KeyboardInterrupt:
    logging.info(" >> Stopping data transmission...")
    {{ cookiecutter.prefix }}_device.stop()
    thread.join()
    logging.info(" >> Program exited cleanly.")





