#!/bin/sh
# Full re-route: prep -> DSN -> Freerouting -> import -> refill + DRC (KiCad 10 in Docker).
# Usage: scripts/route.sh /path/to/freerouting-1.9.0.jar
set -e
cd "$(dirname "$0")/.."
K="docker run --rm --user $(id -u):$(id -g) -e HOME=/tmp -v $PWD:/w -w /w kicad/kicad:10.0.6"
python3 scripts/route_pcb.py prep
$K kicad-cli pcb drc --refill-zones --save-board -o out/drc.rpt lis3dh_board.kicad_pcb >/dev/null
$K python3 -c "import pcbnew; pcbnew.ExportSpecctraDSN(pcbnew.LoadBoard('lis3dh_board.kicad_pcb'), 'out/board.dsn')"
rm -f out/board.ses
(cd out && xvfb-run -a java -jar "$1" -de board.dsn -do board.ses -mp 100 > freerouting.log 2>&1)
python3 scripts/route_pcb.py finish out/board.ses
python3 scripts/route_pcb.py stitch
$K kicad-cli pcb drc --refill-zones --save-board --severity-all --schematic-parity -o out/drc.rpt lis3dh_board.kicad_pcb
