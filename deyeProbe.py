#!/usr/bin/env python3
"""
One-off check of the Deye inverter connection. Run it on the device that runs the bot.

  python3 deyeProbe.py --discover                  # find logger IP and serial on the local network
  python3 deyeProbe.py --find-serial <logger-ip>   # get serial from a logger that ignores discovery
  python3 deyeProbe.py <logger-ip> <logger-serial> # read grid data
  python3 deyeProbe.py                             # read grid data using 'deye-local' from config.yaml
"""
import argparse
import asyncio
import socket
import struct
import sys
from typing import Optional
from pysolarmanv5 import PySolarmanV5Async
from umodbus.client.serial import rtu
from utils.deyeService import FIRST_REGISTER, REGISTER_COUNT, parseRegisters

DISCOVERY_PORT = 48899
DISCOVERY_MESSAGE = b'WIFIKIT-214028-READ'
LOGGER_PORT = 8899


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
        print('No loggers answered. If you know the logger IP, run: python3 deyeProbe.py --find-serial <logger-ip>')


def findLoggerSerial(ip: str) -> Optional[int]:
    """
    Send one read request with serial 0. The logger puts its own serial
    into the header of every reply, even when the request serial is wrong.
    """
    modbusFrame = rtu.read_holding_registers(1, FIRST_REGISTER, 1)
    payload = b'\x02' + bytes(14) + modbusFrame  # frame type + sensor type + 3 timestamps
    frame = b'\xa5' + struct.pack('<HHHI', len(payload), 0x4510, 0, 0) + payload
    frame += bytes([sum(frame[1:]) & 0xFF, 0x15])  # checksum + end byte

    with socket.create_connection((ip, LOGGER_PORT), timeout=10) as sock:
        sock.sendall(frame)
        reply = sock.recv(1024)

    if len(reply) < 11 or reply[0] != 0xA5:
        return None
    return struct.unpack('<I', reply[7:11])[0]


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
    parser.add_argument('--find-serial', metavar='LOGGER_IP', help='print the serial number of the logger at this IP')
    args = parser.parse_args()

    if args.discover:
        discover()
        return

    if args.find_serial:
        try:
            serial = findLoggerSerial(args.find_serial)
        except OSError as e:
            print(f'Cannot connect to logger {args.find_serial}:{LOGGER_PORT}: {e}')
            sys.exit(1)
        if serial is None:
            print('Logger reply was not recognized')
            sys.exit(1)
        print(serial)
        return

    ip, serial = args.ip, args.serial
    if not ip or not serial:
        try:
            from config import config  # only needed here: config.yaml may not exist yet during install
        except FileNotFoundError:
            parser.error('config/config.yaml not found: pass <logger-ip> <logger-serial>')
        deyeConfig = config.get('deye-local', {})
        ip = ip or deyeConfig.get('logger-ip')
        serial = serial or deyeConfig.get('logger-serial')
    if not ip or not serial:
        parser.error('pass <logger-ip> <logger-serial> or set them in config.yaml under deye-local')

    try:
        asyncio.run(probe(ip, int(serial)))
    except Exception as e:
        print(f'Failed to read inverter via logger {ip} (serial {serial}): {e!r}')
        sys.exit(1)


if __name__ == '__main__':
    main()
