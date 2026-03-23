import logging
import threading
import time

import pytz
from s2python.common import ControlType

from pv_rm_interface.pv_system import PvSystem

logging.basicConfig(level=logging.INFO)


def handle_callbacks(callback, pv_device):
    """Callback function for handling the CEM control messages"""

    if isinstance(callback, ControlType):
        pv_device.setControlType(callback)


pv_device = PvSystem()

#  connect to local mosquitto container
host = "mosquitto"
port = 1883
logging.info(f" >$ Connecting to {host}:{port} (MQTT Broker)")

# Start the device with CEM discovery
pv_device.startDiscovery(
    config=pv_device.mqttCEM,
    onCemDiscovered=lambda cemUUID: pv_device.startRmSubscription(
        pv_device.mqttCEM,
        rmCallback=lambda callback: handle_callbacks(callback, pv_device),
    ),
)

# Wait for CEM to be discovered
logging.info(" >> Waiting for RM-CEM connection to be established... \n")
while not pv_device.connection.on:
    time.sleep(1)

logging.info(" >> RM-CEM connection established. \n")
thread = threading.Thread(
    target=pv_device.startDataTransmission, args=(pytz.timezone("Europe/Berlin"), 15)
)
thread.start()

try:
    while thread.is_alive():
        time.sleep(1)
except KeyboardInterrupt:
    logging.info(" >> Stopping data transmission...")
    pv_device.stop()
    thread.join()
    logging.info(" >> Program exited cleanly.")
