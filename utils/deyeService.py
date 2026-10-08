import asyncio
from dataclasses import dataclass
from typing import List, Optional
from pysolarmanv5 import PySolarmanV5Async
from .printStyler import styler

# Holding registers of Deye 3-phase LV hybrid inverters (SUN-*K-SG04LP3 / SG05LP3).
# Source: ha-solarman inverter definition deye_p3.yaml
FIRST_REGISTER = 552
REGISTER_COUNT = 74  # 552..625

REG_DEVICE_RELAY = 552     # bit 2 = grid relay closed
REG_BATTERY_SOC = 588      # %
REG_GRID_VOLTAGE_L1 = 598  # x0.1 V, L2 = 599, L3 = 600
REG_GRID_FREQUENCY = 609   # x0.01 Hz
REG_GRID_POWER = 625       # W, signed

GRID_RELAY_BIT = 0b100


@dataclass
class GridReading:
    voltages: List[float]
    frequency: float
    isGridRelayOn: bool
    gridPower: int
    batterySoc: int


def parseRegisters(registers: List[int]) -> GridReading:
    """Convert raw register values (starting at FIRST_REGISTER) into a GridReading"""
    def reg(address: int) -> int:
        return registers[address - FIRST_REGISTER]

    gridPower = reg(REG_GRID_POWER)
    if gridPower >= 0x8000:  # 16-bit two's complement
        gridPower -= 0x10000

    return GridReading(
        voltages=[round(reg(REG_GRID_VOLTAGE_L1 + i) * 0.1, 1) for i in range(3)],
        frequency=round(reg(REG_GRID_FREQUENCY) * 0.01, 2),
        isGridRelayOn=bool(reg(REG_DEVICE_RELAY) & GRID_RELAY_BIT),
        gridPower=gridPower,
        batterySoc=reg(REG_BATTERY_SOC),
    )


class DeyeService:
    def _getConfig(self) -> dict:
        from config import config  # imported lazily so deyeProbe.py works before config.yaml exists
        return config.get('deye-local', {})

    async def readGrid(self) -> Optional[GridReading]:
        """
        Read grid data from the inverter through the Solarman logger on the local network.
        Returns None if the logger did not respond.
        """
        deyeConfig = self._getConfig()
        loggerIp = deyeConfig['logger-ip']
        timeoutSeconds = deyeConfig.get('timeout', 15)

        modbus = PySolarmanV5Async(
            loggerIp,
            int(deyeConfig['logger-serial']),
            port=deyeConfig.get('port', 8899),
            mb_slave_id=deyeConfig.get('slave-id', 1),
            socket_timeout=timeoutSeconds,
        )

        styler.ping(f'Reading inverter data via logger {loggerIp}...')

        try:
            await modbus.connect()
            registers = await asyncio.wait_for(
                modbus.read_holding_registers(FIRST_REGISTER, REGISTER_COUNT),
                timeoutSeconds
            )
            return parseRegisters(registers)
        except Exception as e:
            styler.error(f'Failed to read inverter data: {e!r}')
            return None
        finally:
            try:
                await modbus.disconnect()
            except Exception:
                pass

    async def isGridOn(self) -> Optional[bool]:
        """
        Check if the city grid is present by grid voltage.
        Returns None when the state is unknown (logger did not respond).
        """
        reading = await self.readGrid()
        if reading is None:
            return None

        minVoltage = self._getConfig().get('min-grid-voltage', 180)
        isOn = max(reading.voltages) >= minVoltage

        voltagesText = ' / '.join(f'{v:.1f}' for v in reading.voltages)
        message = (f'Grid {"ON" if isOn else "OFF"}: {voltagesText} V, {reading.frequency:.2f} Hz, '
                   f'relay {"closed" if reading.isGridRelayOn else "open"}, '
                   f'grid power {reading.gridPower} W, battery {reading.batterySoc}%')
        styler.power(message, isOn=isOn)

        return isOn


deyeService = DeyeService()
