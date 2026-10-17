#!/usr/bin/env python3
"""Route lis3dh_board.kicad_pcb with Freerouting.

KiCad 10's Python bindings in the container can't iterate board items or build
zone outlines, so this edits the .kicad_pcb s-expression text directly and
leaves zone filling and DRC to kicad-cli (KiCad 10).

  route_pcb.py prep             remove stale parts and old routing, add B.Cu GND plane
  (KiCad 10)   ExportSpecctraDSN -> out/board.dsn ; Freerouting -> out/board.ses
  route_pcb.py finish <ses>     add tracks/vias from the session, add F.Cu GND pour
  kicad-cli pcb drc --refill-zones --save-board
Netclasses (Default / Power / ANT) come from lis3dh_board.kicad_pro.
"""
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / 'lis3dh_board.kicad_pcb'
REMOVED = {'R3'}          # no longer in the schematic
ZONE_INSET = 0.0          # zone outline = board outline; edge clearance comes from the rules


def blocks(t, head):
    """Yield (start, end) spans of top-level '\\t(head' blocks."""
    for m in re.finditer(rf'\n\t\({head}\b', t):
        i = m.start() + 1
        depth = 0
        for j in range(i, len(t)):
            c = t[j]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    yield i, j + 1
                    break


def cut(t, spans):
    for i, j in sorted(spans, reverse=True):
        t = t[:i].rstrip('\t') + t[j:].lstrip('\n')
    return t


def board_rect(t):
    xs, ys = [], []
    for i, j in blocks(t, 'gr_(?:line|rect|arc)'):
        b = t[i:j]
        if '"Edge.Cuts"' in b:
            for x, y in re.findall(r'\((?:start|end|mid) ([-\d.]+) ([-\d.]+)\)', b):
                xs.append(float(x))
                ys.append(float(y))
    return min(xs), min(ys), max(xs), max(ys)


def zone_text(t, layer):
    x0, y0, x1, y1 = board_rect(t)
    d = ZONE_INSET
    pts = ' '.join(f'(xy {x:.4f} {y:.4f})' for x, y in
                   [(x0 + d, y0 + d), (x1 - d, y0 + d), (x1 - d, y1 - d), (x0 + d, y1 - d)])
    return (f'\t(zone\n\t\t(net "GND")\n\t\t(layer "{layer}")\n\t\t(uuid "{uuid.uuid4()}")\n'
            f'\t\t(name "GND_{layer.split(".")[0]}")\n\t\t(hatch edge 0.5)\n'
            f'\t\t(connect_pads thru_hole_only\n\t\t\t(clearance 0.25)\n\t\t)\n'
            f'\t\t(min_thickness 0.2)\n\t\t(filled_areas_thickness no)\n'
            f'\t\t(fill yes\n\t\t\t(thermal_gap 0.25)\n\t\t\t(thermal_bridge_width 0.4)\n\t\t)\n'
            f'\t\t(polygon\n\t\t\t(pts {pts})\n\t\t)\n\t)\n')


def insert(t, text):
    k = t.rstrip().rfind(')')
    return t[:k] + text + t[k:]


def prep():
    t = PCB.read_text()
    spans = []
    for i, j in blocks(t, 'footprint'):
        ref = re.search(r'\(property "Reference" "([^"]+)"', t[i:j])
        if ref and ref[1] in REMOVED:
            spans.append((i, j))
    for head in ('zone', 'segment', 'via', 'arc'):
        spans += list(blocks(t, head))
    t = cut(t, spans)
    t = insert(t, zone_text(t, 'B.Cu'))
    PCB.write_text(t)
    print('prep done:', PCB)


def finish(ses):
    s = Path(ses).read_text()
    scale = 1 / (1000 * int(re.search(r'\(routes\s*\(resolution um (\d+)\)', s)[1]))  # -> mm
    out = s[s.index('(network_out'):]
    items = []
    for m in re.finditer(r'\(net ("[^"]+"|\S+)(.*?)(?=\n      \(net |\Z)', out, re.S):
        net = m[1].strip('"')
        for w in re.finditer(r'\(path (\S+) (\d+)\s+([-\d\s]+)\)', m[2]):
            n = [int(v) for v in w[3].split()]
            pts = [(n[i] * scale, -n[i + 1] * scale) for i in range(0, len(n), 2)]
            width = int(w[2]) * scale
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                items.append(f'\t(segment\n\t\t(start {ax:.4f} {ay:.4f})\n\t\t(end {bx:.4f} {by:.4f})\n'
                             f'\t\t(width {width:.4f})\n\t\t(layer "{w[1]}")\n\t\t(net "{net}")\n'
                             f'\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
        for v in re.finditer(r'\(via "Via\[0-1\]_(\d+):(\d+)_um" (-?\d+) (-?\d+)', m[2]):
            items.append(f'\t(via\n\t\t(at {int(v[3]) * scale:.4f} {-int(v[4]) * scale:.4f})\n'
                         f'\t\t(size {int(v[1]) / 1000:.3f})\n\t\t(drill {int(v[2]) / 1000:.3f})\n'
                         f'\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "{net}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')
    t = PCB.read_text()
    t = insert(t, ''.join(items) + zone_text(t, 'F.Cu'))
    PCB.write_text(t)
    print(f'added {sum(i.startswith(chr(9) + "(segment") for i in items)} segments, '
          f'{sum(i.startswith(chr(9) + "(via") for i in items)} vias, F.Cu GND pour')


# GND stitching vias: tie the F.Cu pour to the B.Cu plane where the pour is
# enclosed by tracks (otherwise those F.Cu areas are removed as islands)
STITCH = [(x, 94.0) for x in (130, 140, 150, 160, 170, 180)]


def stitch():
    vias = ''.join(f'\t(via\n\t\t(at {x:.4f} {y:.4f})\n\t\t(size 0.6)\n\t\t(drill 0.3)\n'
                   f'\t\t(layers "F.Cu" "B.Cu")\n\t\t(net "GND")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n'
                   for x, y in STITCH)
    PCB.write_text(insert(PCB.read_text(), vias))
    print(f'added {len(STITCH)} GND stitching vias')


if __name__ == '__main__':
    {'prep': prep, 'stitch': stitch}.get(sys.argv[1], lambda: finish(sys.argv[2]))()
