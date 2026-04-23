import logging
import threading
import time

from datetime import datetime, timedelta, timezone
from s2python.common import ControlType

from pv_rm_interface.pv_system import PvSystem


def main():
    logging.basicConfig(level=logging.INFO)
    logging.info(" >> ======= Start of My Pv System RM ======= ")

    # Create My Pv System RM
    pv_device = PvSystem()
    rmUUID = str(pv_device.rmUUID)
    logging.info(f" >> with UUID: {rmUUID} \n ")
    local_tz = pv_device.mqttCEM.get("timezone", "Europe/Berlin")

    # Start the device with CEM discovery
    pv_device.startDiscovery(
        config=pv_device.mqttCEM,
        onCemDiscovered=lambda cemUUID: pv_device.startRmSubscription(
            pv_device.mqttCEM,
            rmCallback=lambda callback: handle_callbacks(callback, pv_device),
        ),
    )

    # Wait for CEM to be discovered
    logging.info(" >> [RM] Waiting for RM-CEM connection to be established... \n")
    while not pv_device.connection.on:
        time.sleep(1)

    thread = threading.Thread(
        target=pv_device.startDataTransmission,
        args=(local_tz, 60),  # frequency in seconds
        daemon=True,
    )
    thread.start()

    try:
        while thread.is_alive():
            thread.join(timeout=1)
    except KeyboardInterrupt:
        logging.info(" >> Stopping data transmission...")
        pv_device.stop()
    finally:
        thread.join(timeout=10)
        logging.info(" >> Program exited cleanly.")


def setControlType(controlType, pv_device):
    """If a control type is selected, more information has to provided to the CEM"""
    pv_device.activeControlType = controlType
    logging.info(f" >> [RM] ControlType activated: {controlType}. \n")


def handle_callbacks(callback, pv_device):
    """Callback function for handling the CEM control and activation messages"""

    if isinstance(callback, ControlType):
        setControlType(callback, pv_device)

        pv_device.sendSystemDescription()

    ###############################################
    #    Logic for handling CEM control messages
    ###############################################

    """
    # Example:

    if isinstance(callback, PEBCInstruction):
        logging.info(f" >> [PEBC] Activating power envelope 
            {callback.power_constraints_id} ... \n")
    """


if __name__ == "__main__":
    main()
