import asyncio
import os
from typing import Optional
from utils import styler, GridStatus

# Pairing keys live here. Losing the file means removing the bridge in the Home app and adding it again
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'storage', 'homekit.state')

CONTACT_DETECTED = 0      # closed = electricity
CONTACT_NOT_DETECTED = 1  # open = no electricity
NO_FAULT = 0
GENERAL_FAULT = 1         # inverter is not responding


class HomekitService:
    """
    Shows the grid state in the Apple Home app as a HomeKit bridge with two contact sensors:
    - Grid: closed when at least one phase has electricity (ON or PARTIAL)
    - All phases: closed only when all phases have electricity (ON)
    Battery level of the inverter is shown on the Grid sensor.
    """
    _driver = None
    _gridSensor = None
    _allPhasesSensor = None
    _battery = None
    _lowBatteryPercent = 20

    def isEnabled(self) -> bool:
        return self._driver is not None

    async def start(self, homekitConfig: dict) -> None:
        # Imported here so the bot works without HAP-python when HomeKit is not configured
        from pyhap.accessory import Accessory, Bridge
        from pyhap.accessory_driver import AccessoryDriver
        from pyhap.const import CATEGORY_SENSOR

        name = homekitConfig.get('name', 'Svitlo')
        pincode = homekitConfig.get('pincode')
        self._lowBatteryPercent = homekitConfig.get('low-battery', 20)

        driver = AccessoryDriver(
            loop=asyncio.get_running_loop(),
            port=homekitConfig.get('port', 51826),
            persist_file=STATE_FILE,
            pincode=str(pincode).encode() if pincode else None,
        )
        bridge = Bridge(driver, name)

        # Accessories are matched to the pairing by the order they are added: don't reorder them
        gridAccessory = Accessory(driver, 'Grid')
        gridAccessory.category = CATEGORY_SENSOR
        gridService = gridAccessory.add_preload_service('ContactSensor', chars=['StatusFault'])
        batteryService = gridAccessory.add_preload_service('BatteryService')
        bridge.add_accessory(gridAccessory)

        allPhasesAccessory = Accessory(driver, 'All phases')
        allPhasesAccessory.category = CATEGORY_SENSOR
        allPhasesService = allPhasesAccessory.add_preload_service('ContactSensor', chars=['StatusFault'])
        bridge.add_accessory(allPhasesAccessory)

        # No reading yet: show a fault instead of a made-up state
        for sensor in (gridService, allPhasesService):
            sensor.get_characteristic('StatusFault').set_value(GENERAL_FAULT, should_notify=False)

        driver.add_accessory(bridge)
        await driver.async_start()

        # Set only after a successful start, so update() does nothing if HomeKit failed to start
        self._driver = driver
        self._gridSensor = gridService
        self._allPhasesSensor = allPhasesService
        self._battery = batteryService
        styler.info(f"HomeKit bridge '{name}' started. Setup code is printed above if it is not paired yet.")

    async def stop(self) -> None:
        if self._driver:
            await self._driver.async_stop()
            self._driver = None

    def update(self, status: GridStatus, batterySoc: int) -> None:
        """Called after every successful inverter reading. HomeKit is notified only about changed values"""
        if not self._gridSensor:
            return

        self._setContact(self._gridSensor, status is not GridStatus.OFF)
        self._setContact(self._allPhasesSensor, status is GridStatus.ON)

        self._battery.get_characteristic('BatteryLevel').set_value(max(0, min(100, batterySoc)))
        self._battery.get_characteristic('StatusLowBattery').set_value(int(batterySoc <= self._lowBatteryPercent))

    def setUnknown(self) -> None:
        """Inverter did not respond: keep the last state and mark the sensors as faulty"""
        if not self._gridSensor:
            return

        for sensor in (self._gridSensor, self._allPhasesSensor):
            sensor.get_characteristic('StatusFault').set_value(GENERAL_FAULT)

    def _setContact(self, sensor, hasElectricity: bool) -> None:
        sensor.get_characteristic('ContactSensorState').set_value(
            CONTACT_DETECTED if hasElectricity else CONTACT_NOT_DETECTED
        )
        sensor.get_characteristic('StatusFault').set_value(NO_FAULT)


homekitService = HomekitService()
