import logging
import threading
import time

from datetime import datetime, timedelta, timezone
from s2python.common import ControlType

from {{ cookiecutter.package_name }}.{{ cookiecutter.prefix }}_system import {{ cookiecutter.class_prefix }}System

def main():
    logging.basicConfig(level=logging.INFO)
    logging.info(" >> ======= Start of {{ cookiecutter.name }} RM ======= ")

    # Create {{ cookiecutter.name }} RM
    {{ cookiecutter.prefix }}_device = {{ cookiecutter.class_prefix }}System()
    rmUUID = str({{ cookiecutter.prefix }}_device.rmUUID)
    logging.info(f" >> with UUID: {rmUUID} \n ")
    local_tz = {{ cookiecutter.prefix }}_device.mqttCEM.get('timezone', 'Europe/Berlin')
    
    # Start the device with CEM discovery
    {{ cookiecutter.prefix }}_device.startDiscovery(
        config={{ cookiecutter.prefix }}_device.mqttCEM,
        onCemDiscovered=lambda cemUUID: {{ cookiecutter.prefix }}_device.startRmSubscription(
            {{ cookiecutter.prefix }}_device.mqttCEM, 
            rmCallback=lambda callback: handle_callbacks(callback, {{ cookiecutter.prefix }}_device)
        )
    )

    # Wait for CEM to be discovered
    logging.info(" >> [RM] Waiting for RM-CEM connection to be established... \n")
    while not {{ cookiecutter.prefix }}_device.connection.on:
        time.sleep(1)

    thread = threading.Thread(
        target={{ cookiecutter.prefix }}_device.startDataTransmission,
        args=(local_tz, 60), # frequency in seconds
        daemon=True
    )
    thread.start()


    try:
        while thread.is_alive():
            thread.join(timeout=1)  
    except KeyboardInterrupt:
        logging.info(" >> Stopping data transmission...") 
        {{ cookiecutter.prefix }}_device.stop()
    finally:
        thread.join(timeout=10)
        logging.info(" >> Program exited cleanly.")




def setControlType(controlType, {{ cookiecutter.prefix }}_device):
        ''' If a control type is selected, more information has to provided to the CEM '''
        {{ cookiecutter.prefix }}_device.activeControlType = controlType
        logging.info(f" >> [RM] ControlType activated: {controlType}. \n")



def handle_callbacks(callback, {{ cookiecutter.prefix }}_device):
    ''' Callback function for handling the CEM control and activation messages '''

    if isinstance(callback, ControlType):
        setControlType(callback, {{ cookiecutter.prefix }}_device)

        {{ cookiecutter.prefix }}_device.sendSystemDescription()
        

    ###############################################
    #    Logic for handling CEM control messages
    ###############################################

    '''
    # Example:

    if isinstance(callback, PEBCInstruction):
        logging.info(f" >> [PEBC] Activating power envelope 
            {callback.power_constraints_id} ... \n")
    '''


if __name__ == '__main__':
    main()
