#!/usr/bin/env python3
"""Build a simplified 3D model of the KRHRO K6-6277D LED tact switch (STEP).

Dimensions are taken from the KRHRO K6-6277D drawing (LCSC C693836). The
model origin is pin 4 at the board surface, matching the KiCad footprint
KRHRO_K6-6277D. KiCad 3D models use +Y up the screen, so the footprint's
+Y (toward the cap) is -Y here.

Outer envelope (what the enclosure needs):
  housing  7.6 wide, 4.05 behind pin 4 to 4.7 in front, 7.4 tall
  neck     5.9 wide, 4.7 -> 6.7 in front of pin 4
  cap      D8.3, 2.5 thick, 6.7 -> 9.2 in front of pin 4,
           axis 3.8 above the board (cap bottom 0.35 below the board top)
  pins     0.7 wide, 3.45 below the board; locating peg D1.0, 1.2 long
"""
from pathlib import Path

import cadquery as cq

OUT = Path(__file__).resolve().parent.parent / '3d' / 'KRHRO_K6-6277D.step'

AXIS_Z = 3.8      # button axis height above the board
TOP_Z = 7.4       # housing top (3.8 + 3.6)
BASE_Z = 0.8      # base plate thickness under the housing


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def fp(y):
    """Footprint Y (toward the cap) -> 3D model Y."""
    return -y


# housing: base plate plus the upper body, slightly narrower above the base
housing = (box(-3.8, 3.8, fp(4.7), fp(-4.05), 0, BASE_Z)
           .union(box(-3.6, 3.6, fp(4.7), fp(-4.05), BASE_Z, TOP_Z - 0.4))
           .union(box(-3.0, 3.0, fp(4.7), fp(-3.4), TOP_Z - 0.4, TOP_Z)))

# neck between housing and cap (plunger guide)
neck = box(-2.95, 2.95, fp(6.7), fp(4.7), AXIS_Z - 2.5, AXIS_Z + 2.5)

# cap: D8.3 x 2.5 along the button axis, small edge fillet on the front face
cap = (cq.Workplane('XZ', origin=(0, fp(6.7), AXIS_Z))
       .circle(8.3 / 2).extrude(2.5)
       .faces('<Y').edges().fillet(0.4))

# power symbol on the cap face, 0.05 proud so it shows in renders
sym = (cq.Workplane('XZ', origin=(0, fp(9.2) - 0.05, AXIS_Z))
       .circle(2.4).circle(1.9).extrude(-0.05)
       .cut(cq.Workplane('XZ', origin=(0, fp(9.2), AXIS_Z)).rect(1.6, 3.0).extrude(-0.2)
            .translate((0, 0, 1.5)))
       .union(cq.Workplane('XZ', origin=(0, fp(9.2) - 0.05, AXIS_Z)).center(0, 1.4)
              .rect(0.5, 2.4).extrude(-0.05)))

# pins: 0.7 x 0.4 blades, 3.45 below the board, 0.5 into the housing
pins = None
for x, y in [(-2.5, 0), (2.5, 0), (0, -2.5), (0, 0)]:
    p = box(x - 0.35, x + 0.35, fp(y) - 0.2, fp(y) + 0.2, -3.45, 0.5)
    pins = p if pins is None else pins.union(p)

# locating peg D1.0, 1.2 below the board
peg = cq.Workplane('XY', origin=(0, fp(3.1), -1.2)).circle(0.5).extrude(1.2 + BASE_Z)

asm = cq.Assembly(name='KRHRO_K6-6277D')
asm.add(housing.union(neck).union(peg), name='housing', color=cq.Color(0.08, 0.08, 0.08))
asm.add(cap, name='cap', color=cq.Color(0.85, 0.85, 0.85))
asm.add(sym, name='symbol', color=cq.Color(0.75, 0.1, 0.1))
asm.add(pins, name='pins', color=cq.Color(0.85, 0.7, 0.3))

OUT.parent.mkdir(exist_ok=True)
asm.export(str(OUT))
print('wrote', OUT)
