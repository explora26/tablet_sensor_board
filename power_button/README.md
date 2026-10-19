# 平板電源鍵小板

KRHRO K6-6277D-02 直角 LED 輕觸開關（紅光）、LED 限流電阻、JST PH 2.0 4P 接頭和一個 M3 鎖孔。

**狀態：原理圖、layout、3D 模型完成（16 × 25 mm，雙層板）；KiCad 10 ERC / DRC 無錯誤。**

## J1（JST PH 2.0，4P）
| J1 | 訊號 | 說明 |
|---|---|---|
| 1 | VCC | 5V，LED 電源（經 R1 1k 到 LED 正極） |
| 2 | SW | 按下時接到 GND；上拉電阻放在主板 |
| 3 | LED_CTRL | LED 負極；主板拉到 GND 時 LED 亮 |
| 4 | GND | |

- LED 電流：(5V − 紅光約 2V) / 1k ≈ 3 mA
- LED_CTRL 會被 LED 拉到接近 5V − Vf，**不可直接接 3V GPIO**；主板請用 NPN / N-MOSFET 或開汲極輸出控制，要常亮就直接接 GND
- 開關額定 DC 30V 0.3A

## 機構重點
- 按鍵中心離板面 3.80 mm，按鍵帽 Ø8.30 × 2.50 mm，帽子底部比板面低 0.35 mm，所以**按鍵帽必須伸出板邊**
- 板子下緣在第 4 腳往前 4.58 mm（本體前緣附近），頸部和按鍵帽伸出板外；按鍵帽後緣在第 4 腳往前 6.7 mm、帽面 9.2 mm
- 本體外框：寬 7.6 mm，第 4 腳往後 4.05 mm 到往前 4.7 mm，高 7.4 mm
- H1：M3 鎖孔（3.2 mm，不鍍銅）
- `3d/power_button_board.step`：整片板子含零件的 STEP，可直接匯入機構軟體
- `3d/KRHRO_K6-6277D.step`：開關的簡化模型（依 KRHRO 圖面尺寸建立，外形包絡正確，內部細節省略）

## 檔案
- `power_button.kicad_pro / .kicad_sch / .kicad_pcb`：KiCad 專案；`fp-lib-table` 指到專案內的 `power_button.pretty`
- `power_button.pretty/KRHRO_K6-6277D.kicad_mod`：開關封裝（依圖面 PCB Layout 繪製，已掛 3D 模型）
- `fab/power_button_gerbers.zip`、`fab/positions.csv`、`fab/bom.csv`：製造檔
- `docs/schematic.pdf`、`docs/pcb_3d_top.png`、`docs/pcb_3d_iso.png`
- `scripts/gen_sch.py`、`scripts/gen_pcb.py`、`scripts/gen_3d.py`：產生原理圖、PCB（Freerouting 佈線）和 3D 模型的腳本
