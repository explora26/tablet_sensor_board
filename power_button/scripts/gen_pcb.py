#!/usr/bin/env python3
"""Build power_button.kicad_pcb (KiCad 7 pcbnew API) from the schematic netlist.

  gen_pcb.py place          -> placed board + out/board.dsn for Freerouting
  gen_pcb.py finish <ses>   -> import the Freerouting session, F.Cu GND pour, fill, DRC

The switch cap overhangs the bottom board edge: its bottom sits 0.35 mm below
the board top, so the edge is placed at the cap's rear face (pin 4 + 6.7 mm).
"""
import re
import sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / 'power_button.kicad_pcb'
NET = ROOT / 'out' / 'net.net'
SYSFP = Path('/usr/share/kicad/footprints')
LIBS = {'power_button': ROOT / 'power_button.pretty'}

MM = pcbnew.FromMM
X0, Y0, W, H = 100.0, 100.0, 24.0, 20.0
SW_X, SW_Y = 114.0, Y0 + H - 6.7          # pin 4; cap rear face on the bottom edge

# ref: (x, y, rotation)
PLACE = {
    'J1': (111.0, 103.0, 0),
    'SW1': (SW_X, SW_Y, 0),
    'R1': (121.0, 112.0, 90),
    'H1': (104.5, 113.0, 0),
}


def parse_netlist():
    t = NET.read_text()
    comps = {m[1]: (m[2], m[3]) for m in re.finditer(
        r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)\s*\(footprint "([^"]*)"\)', t)}
    fields = {}
    for m in re.finditer(r'\(comp \(ref "([^"]+)"\)(.*?)\(libsource', t, re.S):
        fields[m[1]] = dict(re.findall(r'\(field \(name "([^"]+)"\) "([^"]*)"\)', m[2]))
    pads = {}
    for m in re.finditer(r'\(net \(code "\d+"\) \(name "([^"]+)"\)(.*?)\)\s*\)\s*(?=\(net |\)\s*\)\s*$)', t, re.S):
        if m[1].startswith('unconnected-'):
            continue
        for ref, pin in re.findall(r'\(ref "([^"]+)"\) \(pin "([^"]+)"\)', m[2]):
            pads[(ref, pin)] = m[1]
    return comps, fields, pads


def load_fp(fpid):
    lib, name = fpid.split(':')
    return pcbnew.FootprintLoad(str(LIBS.get(lib, SYSFP / f'{lib}.pretty')), name)


def text(board, s, x, y, layer, size=1.0, mirror=False, angle=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15))
    t.SetMirrored(mirror)
    t.SetTextAngleDegrees(angle)
    board.Add(t)


def zone(board, layer):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet('GND'))
    z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(0.3))
    z.SetThermalReliefSpokeWidth(MM(0.4))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in [(X0, Y0), (X0 + W, Y0), (X0 + W, Y0 + H), (X0, Y0 + H)]:
        ol.Append(MM(x), MM(y))
    board.Add(z)


def place():
    comps, fields, pads = parse_netlist()
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(MM(0.2))
    nc.SetTrackWidth(MM(0.4))
    nc.SetViaDiameter(MM(0.6))
    nc.SetViaDrill(MM(0.3))
    ds.m_CopperEdgeClearance = MM(0.3)

    nets = {}
    for name in sorted(set(pads.values())):
        nets[name] = pcbnew.NETINFO_ITEM(board, name)
        board.Add(nets[name])

    fps = dict(comps)
    fps['H1'] = ('M3', 'MountingHole:MountingHole_3.2mm_M3')
    for ref, (value, fpid) in fps.items():
        fp = load_fp(fpid)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetFPIDAsString(fpid)
        for m in fp.Models():      # point stock models at KiCad 10's STEP library
            m.m_Filename = (m.m_Filename.replace('${KICAD6_3DMODEL_DIR}', '${KICAD10_3DMODEL_DIR}')
                            .replace('.wrl', '.step'))
        for k, v in fields.get(ref, {}).items():
            fp.SetProperty(k, v)
        board.Add(fp)
        x, y, rot = PLACE[ref]
        fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        fp.SetOrientationDegrees(rot)
        fp.Value().SetVisible(False)
        if ref == 'H1':
            fp.Reference().SetVisible(False)
        for pad in fp.Pads():
            n = pads.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(nets[n])

    for ref, (x, y) in {'J1': (107.4, 103.0), 'R1': (121.0, 109.6), 'SW1': (108.0, 109.6)}.items():
        r = board.FindFootprintByReference(ref).Reference()
        r.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        r.SetTextAngleDegrees(0)
        r.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8)))
        r.SetTextThickness(MM(0.12))

    # board outline, 1 mm corner radius on the top corners only (bottom edge carries the switch)
    segs = [((X0, Y0 + H), (X0, Y0 + 1)), ((X0 + 1, Y0), (X0 + W - 1, Y0)),
            ((X0 + W, Y0 + 1), (X0 + W, Y0 + H)), ((X0 + W, Y0 + H), (X0, Y0 + H))]
    for (ax, ay), (bx, by) in segs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(MM(ax), MM(ay)))
        s.SetEnd(pcbnew.VECTOR2I(MM(bx), MM(by)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(MM(0.1))
        board.Add(s)
    for cx, cy, sx, sy in [(X0 + 1, Y0 + 1, X0, Y0 + 1), (X0 + W - 1, Y0 + 1, X0 + W - 1, Y0)]:
        a = pcbnew.PCB_SHAPE(board)
        a.SetShape(pcbnew.SHAPE_T_ARC)
        a.SetCenter(pcbnew.VECTOR2I(MM(cx), MM(cy)))
        a.SetStart(pcbnew.VECTOR2I(MM(sx), MM(sy)))
        a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
        a.SetLayer(pcbnew.Edge_Cuts)
        a.SetWidth(MM(0.1))
        board.Add(a)

    # J1 pin labels on the back (front is covered by the connector body)
    for i, lab in enumerate(['5V', 'SW', 'LED', 'GND']):
        text(board, lab, 111.0 + 2 * i, 106.6, pcbnew.B_SilkS, size=0.8, mirror=True, angle=90)
    text(board, 'PWR KEY  rev A', 112.0, 117.5, pcbnew.B_SilkS, size=0.8, mirror=True)

    zone(board, pcbnew.B_Cu)
    pcbnew.SaveBoard(str(PCB), board)
    if not pcbnew.ExportSpecctraDSN(board, str(ROOT / 'out' / 'board.dsn')):
        sys.exit('DSN export failed')
    print('wrote', PCB)


def import_ses(board, ses):
    t = Path(ses).read_text()
    scale = 1000 / int(re.search(r'\(routes\s*\(resolution um (\d+)\)', t)[1])
    layers = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}
    out = t[t.index('(network_out'):]
    for m in re.finditer(r'\(net ("[^"]+"|\S+)(.*?)(?=\n      \(net |\Z)', out, re.S):
        net = board.FindNet(m[1].strip('"'))
        for w in re.finditer(r'\(path (\S+) (\d+)\s+([-\d\s]+)\)', m[2]):
            n = [int(v) for v in w[3].split()]
            pts = [(round(n[i] * scale), round(-n[i + 1] * scale)) for i in range(0, len(n), 2)]
            for a, b in zip(pts, pts[1:]):
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(pcbnew.VECTOR2I(*a))
                tr.SetEnd(pcbnew.VECTOR2I(*b))
                tr.SetWidth(round(int(w[2]) * scale))
                tr.SetLayer(layers[w[1]])
                tr.SetNet(net)
                board.Add(tr)
        for v in re.finditer(r'\(via "Via\[0-1\]_(\d+):(\d+)_um" (-?\d+) (-?\d+)', m[2]):
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(round(int(v[3]) * scale), round(-int(v[4]) * scale)))
            via.SetWidth(int(v[1]) * 1000)
            via.SetDrill(int(v[2]) * 1000)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetNet(net)
            board.Add(via)


def finish(ses):
    board = pcbnew.LoadBoard(str(PCB))
    import_ses(board, ses)
    zone(board, pcbnew.F_Cu)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(PCB), board)
    print('wrote', PCB)


if __name__ == '__main__':
    place() if sys.argv[1] == 'place' else finish(sys.argv[2])
