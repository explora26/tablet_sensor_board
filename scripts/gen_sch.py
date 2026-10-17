#!/usr/bin/env python3
"""Generate lis3dh_board.kicad_sch (KiCad 7 format) from KiCad's stock libraries.

Every pin gets a short wire stub ending in a net label or power symbol, so
connectivity is defined purely by net names.
"""
import re
import sys
import uuid
from pathlib import Path

SYMDIR = Path('/usr/share/kicad/symbols')
OUT = Path(__file__).resolve().parent.parent / 'lis3dh_board.kicad_sch'
PROJECT = 'lis3dh_board'
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, 'lis3dh_board.root'))
STUB = 2.54

_ctr = 0


def uid():
    global _ctr
    _ctr += 1
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f'lis3dh_board.{_ctr}'))


_libcache = {}


def lib_block(lib, name):
    """Return the raw top-level (symbol "name" ...) block from a .kicad_sym file."""
    if lib not in _libcache:
        _libcache[lib] = (SYMDIR / f'{lib}.kicad_sym').read_text()
    t = _libcache[lib]
    i = t.find(f'\n  (symbol "{name}"')
    if i < 0:
        sys.exit(f'symbol {lib}:{name} not found')
    j = t.find('\n  (symbol "', i + 10)
    if j < 0:
        j = t.rfind(')')
    return t[i + 1:j].rstrip()


def embed(lib, name, base=None, overrides=None):
    """Embed a library symbol, flattening an 'extends' symbol onto its base."""
    blk = lib_block(lib, base or name)
    if base:
        blk = blk.replace(f'"{base}_', f'"{name}_')
        blk = blk.replace(f'(symbol "{base}"', f'(symbol "{name}"', 1)
        for k, v in (overrides or {}).items():
            blk = re.sub(rf'\(property "{k}" "[^"]*"', f'(property "{k}" "{v}"', blk, count=1)
    blk = blk.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)
    return blk


def pins_of(block):
    pins = {}
    for m in re.finditer(r'\(pin \w+ \w+ \(at ([-\d.]+) ([-\d.]+) (\d+)\).*?\(number "([^"]*)"',
                         block, re.S):
        x, y, a, num = float(m[1]), float(m[2]), int(m[3]), m[4]
        pins[num] = (x, y, a)
    return pins


LIBS = {
    'Device:R': embed('Device', 'R'),
    'Device:C': embed('Device', 'C'),
    'Device:C_Polarized': embed('Device', 'C_Polarized'),
    'Connector_Generic:Conn_01x02': embed('Connector_Generic', 'Conn_01x02'),
    'Connector_Generic:Conn_01x05': embed('Connector_Generic', 'Conn_01x05'),
    'Connector_Generic:Conn_01x07': embed('Connector_Generic', 'Conn_01x07'),
    'Connector_Generic:Conn_01x10': embed('Connector_Generic', 'Conn_01x10'),
    'Sensor_Motion:LIS3DH': embed('Sensor_Motion', 'LIS3DH'),
    'Regulator_Linear:TLV75530PDBV': embed(
        'Regulator_Linear', 'TLV75530PDBV', base='TLV70012_SOT23-5',
        overrides={
            'Value': 'TLV75530PDBV',
            'Datasheet': 'https://www.ti.com/lit/ds/symlink/tlv755p.pdf',
            'ki_description': '500mA Low Dropout Voltage Regulator, Fixed Output 3.0V, SOT-23-5',
        }),
    'Transistor_FET:BSS138': embed('Transistor_FET', 'BSS138'),
    'power:GND': embed('power', 'GND'),
    'power:+5V': embed('power', '+5V'),
    'power:+3V0': embed('power', '+3V0'),
    'power:PWR_FLAG': embed('power', 'PWR_FLAG'),
}
PINS = {k: pins_of(v) for k, v in LIBS.items()}

items = []
pwr_n = 0


def fmt(v):
    return f'{v:.2f}'.rstrip('0').rstrip('.')


def prop(name, value, x, y, hide=False, justify=None, angle=0):
    eff = '(effects (font (size 1.27 1.27))'
    if justify:
        eff += f' (justify {justify})'
    if hide:
        eff += ' hide'
    eff += ')'
    return f'    (property "{name}" "{value}" (at {fmt(x)} {fmt(y)} {angle})\n      {eff}\n    )'


def place(lib_id, ref, value, x, y, footprint='', datasheet='~', fields=None, rot=0, vpos=None,
          vjust=None, vangle=0, rpos=None, rjust=None):
    pins = PINS[lib_id]
    is_pwr = ref.startswith('#')
    if lib_id.startswith('Connector_Generic:') and rpos is None:
        rpos, rjust = (x + 3.81, y - 1.27), 'left'
        vpos, vjust = (x + 3.81, y + 1.27), 'left'
    if lib_id in ('Device:R', 'Device:C', 'Device:C_Polarized') and rpos is None:
        rpos, rjust = (x + 2.54, y - 1.27), 'left'
        vpos, vjust = (x + 2.54, y + 1.27), 'left'
    props = [
        prop('Reference', ref, *(rpos or (x, y - 6 if not is_pwr else y + 6)), hide=is_pwr,
             justify=rjust),
        prop('Value', value, *(vpos or (x, y + 7 if not is_pwr else y - 3.5)), justify=vjust,
             angle=vangle),
        prop('Footprint', footprint, x, y, hide=True),
        prop('Datasheet', datasheet, x, y, hide=True),
    ]
    for k, v in (fields or {}).items():
        props.append(prop(k, v, x, y, hide=True))
    pin_lines = '\n'.join(f'    (pin "{n}" (uuid {uid()}))' for n in pins)
    items.append(
        f'  (symbol (lib_id "{lib_id}") (at {fmt(x)} {fmt(y)} {rot}) (unit 1)\n'
        f'    (in_bom {"no" if is_pwr else "yes"}) (on_board {"no" if is_pwr else "yes"}) (dnp no)\n'
        f'    (uuid {uid()})\n' + '\n'.join(props) + '\n' + pin_lines + '\n'
        f'    (instances\n      (project "{PROJECT}"\n'
        f'        (path "/{ROOT_UUID}" (reference "{ref}") (unit 1))\n      )\n    )\n  )')
    return {n: (x + px, y - py, a) for n, (px, py, a) in pins.items()}


# symbol rotation so the power symbol's graphic points along stub direction d
PWR_ROT = {
    'GND': {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270},
    'UP': {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270},
}


def power(kind, x, y, d=None):
    global pwr_n
    pwr_n += 1
    ref = f'#FLG0{pwr_n}' if kind == 'PWR_FLAG' else f'#PWR0{pwr_n}'
    if d is None:
        d = (0, 1) if kind == 'GND' else (0, -1)
    rot = PWR_ROT['GND' if kind == 'GND' else 'UP'][d]
    off = 4.0 if d[0] else 4.2
    vpos = (x + d[0] * off, y + d[1] * off)
    vjust = None if not d[0] else ('left' if d[0] < 0 else 'right')
    place(f'power:{kind}', ref, kind, x, y, rot=rot, vpos=vpos, vjust=vjust,
          vangle=rot if rot in (90, 270) else 0)


def wire(x1, y1, x2, y2):
    items.append(f'  (wire (pts (xy {fmt(x1)} {fmt(y1)}) (xy {fmt(x2)} {fmt(y2)}))\n'
                 f'    (stroke (width 0) (type default))\n    (uuid {uid()})\n  )')


# outward direction (schematic coords, y down) for a pin whose lib angle is a
OUTWARD = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}
LABEL_ROT = {(-1, 0): (180, 'right bottom'), (1, 0): (0, 'left bottom'),
             (0, -1): (90, 'left bottom'), (0, 1): (270, 'right bottom')}


def stub(pin):
    x, y, a = pin
    dx, dy = OUTWARD[a]
    ex, ey = x + dx * STUB, y + dy * STUB
    wire(x, y, ex, ey)
    return ex, ey, (dx, dy)


def label(pin, net):
    ex, ey, d = stub(pin)
    rot, just = LABEL_ROT[d]
    items.append(f'  (label "{net}" (at {fmt(ex)} {fmt(ey)} {rot}) (fields_autoplaced)\n'
                 f'    (effects (font (size 1.27 1.27)) (justify {just}))\n    (uuid {uid()})\n  )')


def pwr(pin, kind):
    ex, ey, d = stub(pin)
    power(kind, ex, ey, d)


def nc(pin):
    x, y, _ = pin
    items.append(f'  (no_connect (at {fmt(x)} {fmt(y)}) (uuid {uid()}))')


def text(s, x, y, size=1.27):
    s = s.replace('"', '\\"').replace('\n', '\\n')
    items.append(f'  (text "{s}" (at {fmt(x)} {fmt(y)} 0)\n'
                 f'    (effects (font (size {size} {size})) (justify left bottom))\n    (uuid {uid()})\n  )')


R_FP = 'Resistor_SMD:R_0603_1608Metric'
C_FP = 'Capacitor_SMD:C_0603_1608Metric'

# ---- J1: connector to NanoPC-T4 40-pin header --------------------------------
j1 = place('Connector_Generic:Conn_01x07', 'J1', 'T4_IF', 50.8, 76.2,
           footprint='Connector_PinHeader_2.54mm:PinHeader_1x07_P2.54mm_Vertical')
pwr(j1['1'], '+5V')
pwr(j1['2'], 'GND')
label(j1['3'], 'SCL')
label(j1['4'], 'SDA')
label(j1['5'], 'INT1')
label(j1['6'], 'CHG_INT')
label(j1['7'], 'RFID_TX')
text('J1 -> NanoPC-T4 40-pin\n1: VIN  -> pin 2  (5V)\n2: GND  -> pin 6\n'
     '3: SCL  -> pin 5  (I2C2_SCL, 3V)\n4: SDA  -> pin 3  (I2C2_SDA, 3V)\n5: INT1 -> pin 11 (GPIO1_A1, 3V, optional)\n6: CHG_INT -> pin 7 (GPIO1_A0, 3V)\n7: RFID_TX -> pin 21 (UART4_RX, 3V)\nDo NOT use pins 27/28 (I2C2 1.8V)',
     30.48, 104.14)

# power flags: +5V and GND come only from the connector
power('PWR_FLAG', 25.4, 45.72)
wire(25.4, 45.72, 25.4, 50.8)
power('+5V', 25.4, 50.8, (0, 1))
power('PWR_FLAG', 38.1, 45.72)
wire(38.1, 45.72, 38.1, 50.8)
power('GND', 38.1, 50.8)

# ---- U1: 5V -> 3.0V LDO ------------------------------------------------------------
u1 = place('Regulator_Linear:TLV75530PDBV', 'U1', 'TLV75530PDBV', 101.6, 76.2,
           footprint='Package_TO_SOT_SMD:SOT-23-5',
           datasheet='https://www.ti.com/lit/ds/symlink/tlv755p.pdf')
pwr(u1['1'], '+5V')
# EN tied to IN
ex, ey, a = u1['3']
wire(ex, ey, ex - STUB, ey)
wire(ex - STUB, ey, ex - STUB, u1['1'][1])
items.append(f'  (junction (at {fmt(ex - STUB)} {fmt(u1["1"][1])}) (diameter 0) (color 0 0 0 0)\n'
             f'    (uuid {uid()})\n  )')
pwr(u1['2'], 'GND')
pwr(u1['5'], '+3V0')
c1 = place('Device:C', 'C1', '1uF', 81.28, 78.74, footprint=C_FP)
pwr(c1['1'], '+5V')
pwr(c1['2'], 'GND')
c2 = place('Device:C', 'C2', '1uF', 119.38, 78.74, footprint=C_FP)
pwr(c2['1'], '+3V0')
pwr(c2['2'], 'GND')
text('VIN 3.3-5.5V, 3.0V out\n(matches T4 I2C2 3.0V I/O)', 86.36, 99.06)

# ---- I2C pull-ups to 3.0V ------------------------------------------------------------
r1 = place('Device:R', 'R1', '4.7k', 81.28, 116.84, footprint=R_FP)
pwr(r1['1'], '+3V0')
label(r1['2'], 'SCL')
r2 = place('Device:R', 'R2', '4.7k', 91.44, 116.84, footprint=R_FP)
pwr(r2['1'], '+3V0')
label(r2['2'], 'SDA')
text('I2C pull-ups to 3.0V\n(DNP if T4 pull-ups suffice)', 76.2, 133.35)

# ---- J2: JST PH 2.0 to BQ25798 charger board --------------------------------------
j2 = place('Connector_Generic:Conn_01x05', 'J2', 'BQ25798_BOARD', 50.8, 142.24,
           footprint='Connector_JST:JST_PH_B5B-PH-K_1x05_P2.00mm_Vertical')
pwr(j2['1'], 'GND')
label(j2['2'], 'CHG_INT')
label(j2['3'], 'SCL')
label(j2['4'], 'SDA')
pwr(j2['5'], '+3V0')     # 3.0V supplied to the charger board (pull-ups / logic)
text('J2 -> BQ25798 charger board (JST PH 2.0)\n1: GND\n2: INT (BQ25798 /INT, open-drain, active low)\n'
     '3: I2C_SCL\n4: I2C_SDA\n5: 3V (out, from U1)\nBQ25798 I2C addr 0x6B', 30.48, 165.1)
r3 = place('Device:R', 'R3', '10k', 101.6, 116.84, footprint=R_FP)
pwr(r3['1'], '+3V0')
label(r3['2'], 'CHG_INT')
text('R3: CHG_INT pull-up\n(BQ25798 /INT is open-drain)', 76.2, 138.43)

# ---- J3: WL-125 125kHz RFID module (plugs in, 1x10 socket) ----------------------
# J3 pin 1 is the polarization key (next to module pin 1); module pins 1-9 map to J3 2-10.
j3 = place('Connector_Generic:Conn_01x10', 'J3', 'WL-125', 228.6, 144.78,
           footprint='Connector_PinSocket_2.54mm:PinSocket_1x10_P2.54mm_Vertical')
nc(j3['1'])                   # key
label(j3['2'], 'ANT1')        # module 1 ANT1: ~100 Vpp resonant voltage
label(j3['3'], 'ANT2')        # module 2 ANT2
label(j3['4'], 'VCC_RF')      # module 3 ASCII select: high = UART output (must not float)
nc(j3['5'])                   # module 4 BEEP
label(j3['6'], 'RFID_TX_5V')  # module 5 TX 9600 8N1, 5V TTL
nc(j3['7'])                   # module 6 Wiegand D0
label(j3['8'], 'RFID_RST')    # module 7 /RESET, active low
pwr(j3['9'], 'GND')           # module 8 GND
label(j3['10'], 'VCC_RF')     # module 9 VCC
text('J3 -> WL-125 RFID (1x10 socket, 2.54mm)\n'
     'J3 pin = module pin + 1\n'
     '1: key (next to module pin 1), NC\n'
     '2,3: ANT1/2 -> J4 antenna connector, ~100Vpp\n'
     '4: ASCII select = VCC_RF (UART mode)\n5: BEEP (NC)\n'
     '6: TX 9600 8N1, 5V -> Q1 level shifter -> RFID_TX 3.0V\n7: Wiegand D0 (NC)\n'
     '8: /RESET (R7 pull-up)\n9: GND\n10: VCC_RF (5V, 3-stage RC filtered)',
     213.36, 106.68)

# ---- J4: 125kHz antenna coil, Molex PicoBlade 1.25mm 2-pin -------------------------
j4 = place('Connector_Generic:Conn_01x02', 'J4', 'RFID_ANT', 228.6, 172.72,
           footprint='Connector_Molex:Molex_PicoBlade_53047-0210_1x02_P1.25mm_Vertical',
           fields={'MPN': 'Molex 53047-0210'})
label(j4['1'], 'ANT1')
label(j4['2'], 'ANT2')
text('J4 -> RFID antenna coil (Molex PicoBlade 1.25mm, 2-pin)\n'
     'ANT1/ANT2 carry ~50-100Vpp at 125kHz:\n'
     'short, parallel traces; >=0.5mm clearance; no copper pour around them',
     213.36, 182.88)

# TX level shift 5V -> 3.0V for T4 UART4_RX: BSS138 bidirectional shifter
# (same topology as Adafruit #757), LV side 3.0V, HV side VCC_RF
r5 = place('Device:R', 'R5', '10k', 104.14, 152.4, footprint=R_FP)
label(r5['1'], 'VCC_RF')
label(r5['2'], 'RFID_TX_5V')
r4 = place('Device:R', 'R4', '10k', 114.3, 152.4, footprint=R_FP)
pwr(r4['1'], '+3V0')
label(r4['2'], 'RFID_TX')
q1 = place('Transistor_FET:BSS138', 'Q1', 'BSS138', 142.24, 152.4,
           footprint='Package_TO_SOT_SMD:SOT-23',
           rpos=(147.32, 151.13), rjust='left', vpos=(147.32, 153.67), vjust='left')
pwr(q1['1'], '+3V0')          # G -> LV supply
label(q1['2'], 'RFID_TX')     # S -> LV side (T4)
label(q1['3'], 'RFID_TX_5V')  # D -> HV side (WL-125 TX)
text('Q1/R4/R5: BSS138 level shifter (Adafruit #757 topology)\n'
     'LV 3.0V (T4 UART4_RX) <-> HV 5V (WL-125 TX)', 99.06, 175.26)
r7 = place('Device:R', 'R7', '10k', 157.48, 152.4, footprint=R_FP)
label(r7['1'], 'VCC_RF')
label(r7['2'], 'RFID_RST')

# clean 5V for the 125kHz reader: 3-stage RC (per WL-125 datasheet appendix).
# First R is 4.7R to limit inrush into 3 x 1000uF from the T4 5V pin (~1A peak);
# the 100nF at the last stage covers what the electrolytics miss above ~1MHz.
RF_R = 'Resistor_SMD:R_0805_2012Metric'
RF_C = 'Capacitor_SMD:CP_Elec_8x10.5'
r6 = place('Device:R', 'R6', '4.7R', 104.14, 193.04, footprint=RF_R)
pwr(r6['1'], '+5V')
label(r6['2'], 'VRF1')
c5 = place('Device:C_Polarized', 'C5', '1000uF 10V', 116.84, 193.04, footprint=RF_C,
           fields={'MPN': 'Panasonic EEE-FT1A102AP', 'LCSC': 'C278408'})
label(c5['1'], 'VRF1')
pwr(c5['2'], 'GND')
r8 = place('Device:R', 'R8', '1R', 134.62, 193.04, footprint=RF_R)
label(r8['1'], 'VRF1')
label(r8['2'], 'VRF2')
c7 = place('Device:C_Polarized', 'C7', '1000uF 10V', 147.32, 193.04, footprint=RF_C,
           fields={'MPN': 'Panasonic EEE-FT1A102AP', 'LCSC': 'C278408'})
label(c7['1'], 'VRF2')
pwr(c7['2'], 'GND')
r9 = place('Device:R', 'R9', '1R', 165.1, 193.04, footprint=RF_R)
label(r9['1'], 'VRF2')
label(r9['2'], 'VCC_RF')
c8 = place('Device:C_Polarized', 'C8', '1000uF 10V', 177.8, 193.04, footprint=RF_C,
           fields={'MPN': 'Panasonic EEE-FT1A102AP', 'LCSC': 'C278408'})
label(c8['1'], 'VCC_RF')
pwr(c8['2'], 'GND')
c6 = place('Device:C', 'C6', '100nF', 195.58, 193.04, footprint=C_FP)
label(c6['1'], 'VCC_RF')
pwr(c6['2'], 'GND')
text('WL-125 supply: 3-stage RC filter +5V -> VRF1 -> VRF2 -> VCC_RF\n'
     'R6 4.7R limits inrush (~1A); drop ~0.17V @ 25mA\n'
     'C8 + C6 close to J3 pin 10 (module VCC)', 99.06, 213.36)

# ---- U2: LIS3DH --------------------------------------------------------------------
u2 = place('Sensor_Motion:LIS3DH', 'U2', 'LIS3DH', 167.64, 81.28,
           footprint='Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y',
           datasheet='https://www.st.com/resource/en/datasheet/lis3dh.pdf')
pwr(u2['1'], '+3V0')    # VDD_IO
pwr(u2['14'], '+3V0')   # VDD
pwr(u2['5'], 'GND')     # GND (10, 12 stacked)
label(u2['4'], 'SCL')
label(u2['6'], 'SDA')
pwr(u2['7'], 'GND')     # SA0 = 0 -> address 0x18
pwr(u2['8'], '+3V0')    # CS high -> I2C mode
label(u2['11'], 'INT1')
nc(u2['9'])             # INT2
for p in ('13', '15', '16'):
    nc(u2[p])           # ADC1..3 unused
c3 = place('Device:C', 'C3', '100nF', 190.5, 78.74, footprint=C_FP)
pwr(c3['1'], '+3V0')
pwr(c3['2'], 'GND')
c4 = place('Device:C', 'C4', '10uF', 200.66, 78.74, footprint=C_FP)
pwr(c4['1'], '+3V0')
pwr(c4['2'], 'GND')
text('LIS3DH, I2C addr 0x18 (SA0=GND)\nCS=VDD_IO selects I2C\nC3/C4 close to pin 14',
     149.86, 116.84)

# ---- write --------------------------------------------------------------------------
lib_txt = '\n'.join('    ' + b.replace('\n', '\n  ') for b in LIBS.values())
sch = f'''(kicad_sch (version 20230121) (generator eeschema)

  (uuid {ROOT_UUID})

  (paper "A3")

  (title_block
    (title "LIS3DH I2C Accelerometer Board")
    (date "2026-10-16")
    (rev "A")
    (comment 1 "Host: NanoPC-T4 I2C2 (3.0V I/O)")
  )

  (lib_symbols
{lib_txt}
  )

''' + '\n\n'.join(items) + '''

  (sheet_instances
    (path "/" (page "1"))
  )
)
'''
OUT.write_text(sch)
print('wrote', OUT)
