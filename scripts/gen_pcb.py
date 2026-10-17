#!/usr/bin/env python3
"""Build lis3dh_board.kicad_pcb (KiCad 7) from the schematic netlist.

  gen_pcb.py place          -> placed, unrouted board + out/lis3dh_board.dsn
  gen_pcb.py finish <ses>   -> import Freerouting session, fill zones, DRC report
"""
import re
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / 'lis3dh_board.kicad_pcb'
NET = ROOT / 'out' / 'lis3dh_board.net'
FPDIR = Path('/usr/share/kicad/footprints')

MM = pcbnew.FromMM
X0, Y0, W, H = 100.0, 100.0, 24.0, 16.0

# ref: (x, y, rotation deg, side)
PLACE = {
    'J1': (102.0, 102.92, 0, 'F'),    # pin 1 at top, pins 2.54 mm down
    'C1': (106.8, 104.0, 90, 'F'),
    'U1': (110.0, 104.0, 0, 'F'),
    'C2': (113.2, 104.0, 90, 'F'),
    'R1': (108.6, 108.0, 0, 'F'),
    'R2': (108.6, 110.54, 0, 'F'),
    'U2': (116.0, 110.0, 0, 'F'),
    'C3': (117.0, 106.6, 0, 'F'),
    'C4': (114.0, 106.6, 0, 'F'),
}
HOLES = [(121.5, 102.5), (121.5, 113.5)]
J1_LABELS = ['5V', 'GND', 'SCL', 'SDA', 'INT1']


def parse_netlist():
    t = NET.read_text()
    comps = {}
    for m in re.finditer(r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)\s*\(footprint "([^"]*)"\)', t):
        comps[m[1]] = (m[2], m[3])
    pads = {}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]+)"\)(.*?)\)\s*\)\s*(?=\(net |\)\s*\)\s*$)', t, re.S):
        name = m[1].lstrip('/')
        if name.startswith('unconnected-'):
            continue
        for ref, pin in re.findall(r'\(ref "([^"]+)"\) \(pin "([^"]+)"\)', m[2]):
            pads[(ref, pin)] = name
    return comps, pads


def silk_text(board, s, x, y, layer, size=0.8, justify=None, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15))
    if justify == 'left':
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    if mirror:
        t.SetMirrored(True)
    board.Add(t)


def zone(board, net, layer):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetLocalClearance(MM(0.2))
    z.SetMinThickness(MM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
    z.SetThermalReliefGap(MM(0.25))
    z.SetThermalReliefSpokeWidth(MM(0.3))
    ol = z.Outline()
    ol.NewOutline()
    m = 0.3
    for x, y in [(X0 + m, Y0 + m), (X0 + W - m, Y0 + m), (X0 + W - m, Y0 + H - m), (X0 + m, Y0 + H - m)]:
        ol.Append(MM(x), MM(y))
    board.Add(z)


def place():
    comps, pads = parse_netlist()
    board = pcbnew.BOARD()

    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(MM(0.13))
    nc.SetTrackWidth(MM(0.25))
    nc.SetViaDiameter(MM(0.6))
    nc.SetViaDrill(MM(0.3))
    ds.m_MinClearance = MM(0.13)
    ds.m_TrackMinWidth = MM(0.15)
    ds.m_ViasMinSize = MM(0.5)
    ds.m_MinThroughDrill = MM(0.3)
    ds.m_CopperEdgeClearance = MM(0.3)

    nets = {}
    for name in sorted(set(pads.values())):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    for ref, (value, fpid) in comps.items():
        lib, name = fpid.split(':')
        fp = pcbnew.FootprintLoad(str(FPDIR / f'{lib}.pretty'), name)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetFPIDAsString(fpid)
        board.Add(fp)
        x, y, rot, side = PLACE[ref]
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            n = pads.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(nets[n])
        fp.Value().SetVisible(False)
        r = fp.Reference()
        r.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
        r.SetTextThickness(MM(0.12))

    # reference designator positions that stay clear of pads
    refpos = {'J1': (102.0, 100.9), 'U1': (110.0, 101.6), 'C1': (106.8, 101.9), 'C2': (113.2, 101.9),
              'R1': (111.2, 108.0), 'R2': (111.2, 110.54), 'U2': (116.0, 112.2), 'C3': (119.5, 106.6),
              'C4': (111.6, 106.6)}
    for fp in board.GetFootprints():
        x, y = refpos[fp.GetReference()]
        fp.Reference().SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        fp.Reference().SetTextAngleDegrees(0)

    for hx, hy in HOLES:
        fp = pcbnew.FootprintLoad(str(FPDIR / 'MountingHole.pretty'), 'MountingHole_2.2mm_M2')
        fp.SetReference(f'H{HOLES.index((hx, hy)) + 1}')
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetPosition(pcbnew.VECTOR2I(MM(hx), MM(hy)))
        board.Add(fp)

    # board outline with 1 mm corner radius
    r = 1.0
    segs = [((X0 + r, Y0), (X0 + W - r, Y0)), ((X0 + W, Y0 + r), (X0 + W, Y0 + H - r)),
            ((X0 + W - r, Y0 + H), (X0 + r, Y0 + H)), ((X0, Y0 + H - r), (X0, Y0 + r))]
    for (ax, ay), (bx, by) in segs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(MM(ax), MM(ay)))
        s.SetEnd(pcbnew.VECTOR2I(MM(bx), MM(by)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)
    for cx, cy, sx, sy in [(X0 + r, Y0 + r, X0, Y0 + r), (X0 + W - r, Y0 + r, X0 + W - r, Y0),
                           (X0 + W - r, Y0 + H - r, X0 + W, Y0 + H - r), (X0 + r, Y0 + H - r, X0 + r, Y0 + H)]:
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetCenter(pcbnew.VECTOR2I(MM(cx), MM(cy)))
        a.SetStart(pcbnew.VECTOR2I(MM(sx), MM(sy)))
        a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
        a.SetLayer(pcbnew.Edge_Cuts)
        a.SetWidth(MM(0.1))
        board.Add(a)

    # silkscreen
    for i, lab in enumerate(J1_LABELS):
        silk_text(board, lab, 103.6, 102.92 + 2.54 * i, pcbnew.F_SilkS, size=0.8, justify='left')
    silk_text(board, 'LIS3DH  I2C 0x18', 112.0, 115.0, pcbnew.B_SilkS, size=0.8, mirror=True)
    silk_text(board, 'VIN 3.3-5.5V  IO 3.0V', 112.0, 101.2, pcbnew.B_SilkS, size=0.8, mirror=True)
    silk_text(board, 'rev A', 106.0, 108.0, pcbnew.B_SilkS, size=0.8, mirror=True)

    # B.Cu is a solid GND plane; the router reaches it with vias. The F.Cu pour is
    # added after routing so it does not count as a connection for the router.
    zone(board, nets['GND'], pcbnew.B_Cu)

    pcbnew.SaveBoard(str(PCB), board)
    dsn = ROOT / 'out' / 'lis3dh_board.dsn'
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        sys.exit('DSN export failed')
    print('wrote', PCB, 'and', dsn)


def import_ses(board, ses):
    """Add Freerouting wires/vias to the board (KiCad 7's SES import needs the GUI)."""
    t = Path(ses).read_text()
    res = re.search(r'\(routes\s*\(resolution um (\d+)\)', t)
    scale = 1000 / int(res[1])            # SES units -> nm
    layers = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}
    out = t[t.index('(network_out'):]
    ntracks = nvias = 0
    for m in re.finditer(r'\(net ("[^"]+"|\S+)(.*?)(?=\n      \(net |\Z)', out, re.S):
        net = board.FindNet(m[1].strip('"'))
        body = m[2]
        for w in re.finditer(r'\(path (\S+) (\d+)\s+([-\d\s]+)\)', body):
            nums = [int(v) for v in w[3].split()]
            pts = [(round(nums[i] * scale), round(-nums[i + 1] * scale)) for i in range(0, len(nums), 2)]
            for a, b in zip(pts, pts[1:]):
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(pcbnew.VECTOR2I(*a))
                tr.SetEnd(pcbnew.VECTOR2I(*b))
                tr.SetWidth(round(int(w[2]) * scale))
                tr.SetLayer(layers[w[1]])
                tr.SetNet(net)
                board.Add(tr)
                ntracks += 1
        for v in re.finditer(r'\(via "Via\[0-1\]_(\d+):(\d+)_um" (-?\d+) (-?\d+)', body):
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(round(int(v[3]) * scale), round(-int(v[4]) * scale)))
            via.SetWidth(int(v[1]) * 1000)
            via.SetDrill(int(v[2]) * 1000)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetNet(net)
            board.Add(via)
            nvias += 1
    print(f'imported {ntracks} track segments, {nvias} vias')


def finish(ses):
    board = pcbnew.LoadBoard(str(PCB))
    import_ses(board, ses)
    zone(board, board.FindNet('GND'), pcbnew.F_Cu)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board)
    rpt = ROOT / 'out' / 'drc.rpt'
    pcbnew.WriteDRCReport(board, str(rpt), pcbnew.EDA_UNITS_MILLIMETRES, True)
    print('wrote', PCB, 'and', rpt)


if __name__ == '__main__':
    if sys.argv[1] == 'place':
        place()
    else:
        finish(sys.argv[2])
