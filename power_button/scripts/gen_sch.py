#!/usr/bin/env python3
"""Generate power_button.kicad_sch (KiCad 7 format) from KiCad's stock libraries.

Same approach as ../../scripts/gen_sch.py: every pin gets a short wire stub
ending in a net label or power symbol, so connectivity is defined by net names.
"""
import re
import sys
import uuid
from pathlib import Path

SYMDIR = Path('/usr/share/kicad/symbols')
OUT = Path(__file__).resolve().parent.parent / 'power_button.kicad_sch'
PROJECT = 'power_button'
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_DNS, 'power_button.root'))
STUB = 2.54

_ctr = 0


def uid():
    global _ctr
    _ctr += 1
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f'power_button.{_ctr}'))


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
    'Switch:SW_Push_LED': embed('Switch', 'SW_Push_LED'),
    'Connector_Generic:Conn_01x04': embed('Connector_Generic', 'Conn_01x04'),
    'Mechanical:MountingHole': embed('Mechanical', 'MountingHole'),
    'power:GND': embed('power', 'GND'),
    'power:+5V': embed('power', '+5V'),
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
          vjust=None, vangle=0, rpos=None, rjust=None, bom=True):
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
        f'    (in_bom {"no" if is_pwr or not bom else "yes"}) (on_board {"no" if is_pwr else "yes"}) (dnp no)\n'
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



# ---- J1: JST PH 2.0 4P to the main board -------------------------------------------
j1 = place('Connector_Generic:Conn_01x04', 'J1', 'PWR_KEY', 50.8, 76.2,
           footprint='Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical',
           fields={'MPN': 'JST B4B-PH-K-S(LF)(SN)'})
pwr(j1['1'], '+5V')
label(j1['2'], 'SW')
label(j1['3'], 'LED_CTRL')
pwr(j1['4'], 'GND')
text('J1 (JST PH 2.0, 4P)\n1: VCC 5V (LED supply)\n2: SW - pulled to GND while pressed\n'
     '   (pull-up on the main board)\n3: LED_CTRL - LED cathode; sink to GND to light\n'
     '   (open-drain / NPN on the main board, or tie to GND for always-on)\n4: GND',
     30.48, 96.52)

power('PWR_FLAG', 25.4, 45.72)
wire(25.4, 45.72, 25.4, 50.8)
power('+5V', 25.4, 50.8, (0, 1))
power('PWR_FLAG', 38.1, 45.72)
wire(38.1, 45.72, 38.1, 50.8)
power('GND', 38.1, 50.8)

# ---- SW1: KRHRO K6-6277D-02, right-angle tact switch with red LED -------------------
sw = place('Switch:SW_Push_LED', 'SW1', 'K6-6277D-02', 127.0, 78.74,
           footprint='power_button:KRHRO_K6-6277D',
           fields={'MPN': 'KRHRO K6-6277D-02', 'LCSC': 'C693836'})
label(sw['1'], 'SW')
# GND drawn past the LED_A label so the two do not overlap
x2, y2, _ = sw['2']
wire(x2, y2, x2 + 12.7, y2)
power('GND', x2 + 12.7, y2)
label(sw['4'], 'LED_A')       # LED anode
label(sw['3'], 'LED_CTRL')    # LED cathode
text('SW1 KRHRO K6-6277D-02 (red LED, DC 30V 0.3A)\npins 1-2: switch, 4: LED+ (A), 3: LED- (K)',
     109.22, 96.52)

# ---- R1: LED current limit -----------------------------------------------------------
r1 = place('Device:R', 'R1', '1k', 101.6, 116.84, footprint='Resistor_SMD:R_0603_1608Metric',
           fields={'MPN': 'YAGEO RC0603FR-071KL'})
pwr(r1['1'], '+5V')
label(r1['2'], 'LED_A')
text('R1: LED current limit\n(5V - ~2V red Vf) / 1k = ~3mA', 109.22, 116.84)

# ---- H1: M3 mounting hole ---------------------------------------------------------------
place('Mechanical:MountingHole', 'H1', 'M3', 40.64, 132.08,
      footprint='MountingHole:MountingHole_3.2mm_M3', bom=False)

# ---- write ---------------------------------------------------------------------------
lib_txt = '\n'.join('    ' + b.replace('\n', '\n  ') for b in LIBS.values())
sch = f'''(kicad_sch (version 20230121) (generator eeschema)

  (uuid {ROOT_UUID})

  (paper "A4")

  (title_block
    (title "Tablet Power Button Board")
    (date "2026-10-19")
    (rev "A")
    (comment 1 "KRHRO K6-6277D-02 LED tact switch, JST PH 4P")
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
