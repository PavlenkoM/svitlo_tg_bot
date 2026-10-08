#!/usr/bin/env python3
"""
One-off check of the Deye inverter connection. Run it on the device that runs the bot.

  python3 deyeProbe.py --discover                  # find logger IP and serial on the local network
  python3 deyeProbe.py <logger-ip> <logger-serial> # read grid data
  python3 deyeProbe.py                             # read grid data using 'deye-local' from config.yaml
"""
import argparse
import asyncio
import socket
from pysolarmanv5 import PySolarmanV5Async
from config import config
from utils.deyeService import FIRST_REGISTER, REGISTER_COUNT, parseRegisters

DISCOVERY_PORT = 48899
DISCOVERY_MESSAGE = b'WIFIKIT-214028-READ'


def discover() -> None:
    """Broadcast the Solarman discovery message. Loggers answer with 'ip,mac,serial'"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(3)
    sock.sendto(DISCOVERY_MESSAGE, ('255.255.255.255', DISCOVERY_PORT))

    found = False
    try:
        while True:
            data, _ = sock.recvfrom(1024)
            ip, mac, serial = data.decode(errors='replace').split(',')[:3]
            print(f'Logger found: ip={ip} mac={mac} serial={serial}')
            found = True
    except socket.timeout:
        pass

    if not found:
        print('No loggers answered. Take the serial number from the logger sticker or the Deye Cloud app.')


async def probe(ip: str, serial: int) -> None:
    modbus = PySolarmanV5Async(ip, serial, socket_timeout=15)
    await modbus.connect()
    try:
        registers = await modbus.read_holding_registers(FIRST_REGISTER, REGISTER_COUNT)
        device = await modbus.read_holding_registers(500, 1)
    finally:
        await modbus.disconnect()

    reading = parseRegisters(registers)
    deviceStates = {0: 'Standby', 1: 'Self-test', 2: 'Normal', 3: 'Alarm', 4: 'Fault'}

    print(f'Device state:    {deviceStates.get(device[0], device[0])}')
    print(f'Grid voltage:    L1 {reading.voltages[0]} V, L2 {reading.voltages[1]} V, L3 {reading.voltages[2]} V')
    print(f'Grid frequency:  {reading.frequency} Hz')
    print(f'Grid relay:      {"closed" if reading.isGridRelayOn else "open"}')
    print(f'Grid power:      {reading.gridPower} W')
    print(f'Battery SOC:     {reading.batterySoc} %')
    print()
    print('Raw registers:')
    for i in range(0, REGISTER_COUNT, 8):
        chunk = registers[i:i + 8]
        print(f'  {FIRST_REGISTER + i}: ' + ' '.join(f'{value:5d}' for value in chunk))


def main() -> None:
    parser = argparse.ArgumentParser(description='Check Deye inverter connection via Solarman logger')
    parser.add_argument('ip', nargs='?', help='logger IP address')
    parser.add_argument('serial', nargs='?', type=int, help='logger serial number')
    parser.add_argument('--discover', action='store_true', help='find loggers on the local network')
    args = parser.parse_args()

    if args.discover:
        discover()
        return

    deyeConfig = config.get('deye-local', {})
    ip = args.ip or deyeConfig.get('logger-ip')
    serial = args.serial or deyeConfig.get('logger-serial')
    if not ip or not serial:
        parser.error('pass <logger-ip> <logger-serial> or set them in config.yaml under deye-local')

    asyncio.run(probe(ip, int(serial)))


if __name__ == '__main__':
    main()
