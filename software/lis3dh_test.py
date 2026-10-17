#!/usr/bin/env python3
"""Read the LIS3DH board from a NanoPC-T4 over I2C2 (/dev/i2c-2).

    sudo apt install i2c-tools python3-smbus2   # or: pip install smbus2
    sudo i2cdetect -y 2                          # expect 18
    python3 lis3dh_test.py
"""
import time

from smbus2 import SMBus

BUS = 2       # NanoPC-T4 I2C2
ADDR = 0x18   # SA0 tied to GND on the board

WHO_AM_I = 0x0F
CTRL_REG1 = 0x20
CTRL_REG4 = 0x23
OUT_X_L = 0x28
AUTO_INC = 0x80


def s16(lo, hi):
    v = (hi << 8) | lo
    return v - 65536 if v & 0x8000 else v


with SMBus(BUS) as bus:
    who = bus.read_byte_data(ADDR, WHO_AM_I)
    if who != 0x33:
        raise SystemExit(f'LIS3DH not found at 0x{ADDR:02X} (WHO_AM_I=0x{who:02X})')

    bus.write_byte_data(ADDR, CTRL_REG1, 0x57)  # 100 Hz, normal mode, X/Y/Z enabled
    bus.write_byte_data(ADDR, CTRL_REG4, 0x88)  # BDU, high-resolution 12-bit, +/-2 g

    while True:
        d = bus.read_i2c_block_data(ADDR, OUT_X_L | AUTO_INC, 6)
        # 12-bit left-justified, 1 mg/digit at +/-2 g high-resolution
        x, y, z = (s16(d[i], d[i + 1]) >> 4 for i in (0, 2, 4))
        print(f'X={x / 1000:+.3f} g  Y={y / 1000:+.3f} g  Z={z / 1000:+.3f} g')
        time.sleep(0.1)
