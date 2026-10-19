# LIS3DH 三軸加速度計小板（NanoPC-T4 I2C2）

> 另一塊平板電源鍵小板在 [`power_button/`](power_button/README.md)。

板上用 LDO 轉出 3.0V，讓 I2C 電位和 NanoPC-T4 的 I2C2（3.0V I/O）一致，同時經 JST 接頭供電和 I2C 給 BQ25798 充電板。

**狀態：原理圖和 layout 完成（87.6 × 25.4 mm，雙層板），DRC 無錯誤。**

## 規格
| 項目 | 內容 |
|---|---|
| 感測器 | ST LIS3DH，LGA-16 3×3 mm |
| I2C 位址 | 0x18（SA0 接 GND），WHO_AM_I = 0x33 |
| 電源 | VIN 3.3–5.5V → TLV75530（3.0V，500 mA） |
| 上拉電阻 | SCL/SDA 各 4.7k 上拉到 3.0V（R1/R2，T4 的上拉夠用時可以不焊） |
| 介面 | J1：1×7 排針，2.54 mm，接 T4；J2：JST PH 2.0 5 pin，接 BQ25798 充電板；J3：1×10 排母，插 WL-125 RFID 模組；J4：Molex PicoBlade 1.25 mm 2 pin，接 RFID 天線 |
| 固定 | H1、H2：2 個 M3 鎖孔（3.2 mm，不鍍銅），layout 時靠近 LIS3DH 擺放，讓加速度計鎖緊固定 |

## J1 ↔ NanoPC-T4 40-pin
| J1 | 訊號 | T4 腳位 |
|---|---|---|
| 1 | VIN | Pin 2（5V） |
| 2 | GND | Pin 6 |
| 3 | SCL | Pin 5（I2C2_SCL） |
| 4 | SDA | Pin 3（I2C2_SDA） |
| 5 | INT1 | Pin 11（GPIO1_A1，3V，選用） |
| 6 | CHG_INT | Pin 7（GPIO1_A0，3V） |
| 7 | RFID_TX | Pin 21（UART4_RX，3V），需在 device tree 啟用 UART4、關閉 SPI1 |

## J2 ↔ BQ25798 充電板（JST PH 2.0，5 pin）
| J2 | 訊號 | 說明 |
|---|---|---|
| 1 | GND | |
| 2 | INT | BQ25798 的 /INT（開汲極，低電位觸發），上拉電阻在充電板上（小板不另加），經 J1 第 6 腳送到 T4 |
| 3 | I2C_SCL | 和 T4 的 I2C2 共用匯流排 |
| 4 | I2C_SDA | 同上 |
| 5 | 3V | 小板輸出的 3.0V（來自 U1），供充電板的上拉電阻和邏輯電路使用 |

I2C2 上的位址：LIS3DH 是 0x18，BQ25798 是 0x6B，沒有衝突。

## J3 ↔ WL-125 125kHz RFID 模組（1×10 排母，2.54 mm）
模組焊 10P 排針直接插上，排針從模組元件面（有 IC 的那面）焊接。模組只有 9 支腳，多出來的防呆腳在**模組第 1 腳旁邊**，所以 J3 腳位 = 模組腳位 + 1。

| J3 | 模組腳位 | 小板上的接法 |
|---|---|---|
| 1 | — | 防呆腳，不接 |
| 2 | 1 天線 1 | ANT1 → J4 第 1 腳（天線線圈），有 50–100 Vpp 諧振電壓 |
| 3 | 2 天線 2 | ANT2 → J4 第 2 腳 |
| 4 | 3 輸出模式選擇 | 接 VCC_RF（高電位 = UART 輸出，規格書規定不可懸空） |
| 5 | 4 蜂鳴器輸出 | 不接 |
| 6 | 5 TX（9600 8N1，5V TTL） | 經 Q1 BSS138 電位轉換成 3.0V（RFID_TX），送到 J1 第 7 腳 |
| 7 | 6 維根 D0 | 不接 |
| 8 | 7 /RESET（低電位有效） | R7 10k 上拉到 VCC_RF |
| 9 | 8 GND | GND |
| 10 | 9 VCC（5V） | VCC_RF：+5V 經三階 RC 濾波（見下方） |

- 電源濾波（三階 RC，依 WL-125 規格書附錄）：
  `+5V → R6 4.7Ω → C5 1000µF → R8 1Ω → C7 1000µF → R9 1Ω → C8 1000µF + C6 100nF → VCC_RF`
  - C5、C7、C8：Panasonic EEE-FT1A102AP（1000µF 10V，SMD 8 × 10.2 mm，LCSC C278408），封裝 `CP_Elec_8x10.5`；缺貨時可用 EEE-FK1A102P（C278397），但它是 10 mm，要改封裝 `CP_Elec_10x10.5`
  - R6 用 4.7Ω 限制上電湧浪電流（3000µF 從 T4 的 5V 充電，峰值約 1A）
  - 25 mA 時總壓降約 0.17V，模組約 4.8V
  - C6 補 1 MHz 以上的高頻；C8、C6 要緊貼 J3 第 10 腳
  - 1 kHz–500 kHz 約衰減 60 dB（估算值，未含走線）
- 電位轉換：Q1 BSS138 + R4/R5 各 10k 上拉（3.0V 側 / 5V 側），和 Adafruit #757 相同架構
- 卡號格式：`02` + 10 字元 ASCII 卡號 + 1 byte 校驗（XOR）+ `03`，共 13 bytes
- 規格書強調電源要乾淨：不要從 DC-DC 電感附近供電，C5 要靠近 J3
- 天線：線圈（預設 700µH）接 J4（Molex PicoBlade 53047-0210，1.25 mm 2 pin 直立），經小板走線到 J3 第 2、3 腳
- Layout 注意：ANT1/ANT2 走線（J4 ↔ J3 第 2、3 腳）有 50–100 Vpp
  - 兩條線短、平行、等長，盡量靠近，降低對外輻射和寄生電容
  - 與其他走線和鋪銅間距至少 0.5 mm，兩條線底下和周圍不要鋪銅（多餘的對地電容會讓諧振點偏移、讀卡距離變短）
  - 線圈本身遠離金屬和大面積鋪銅

> 不要接 27、28 腳：那組 I2C2 是 1.8V。完整腳位見 `docs/nanopc-t4_40pin.md`。

## 檔案
- `lis3dh_board.kicad_pro`、`lis3dh_board.kicad_sch`、`lis3dh_board.kicad_pcb`：KiCad 專案（PCB 為 KiCad 10 格式）
- `fab/lis3dh_board_gerbers.zip`：Gerber 和鑽孔檔（`fab/gerbers/` 為解開的檔案）
- `fab/bom.csv`：完整 BOM（廠牌、MPN、LCSC 料號、組裝方式、確認狀態）；電阻和陶瓷電容用國巨（YAGEO），C4 例外用 Samsung CL10A106KP8NNNC（JLC 基礎料）
- `fab/jlc_bom.csv`、`fab/jlc_cpl.csv`：JLCPCB SMT 代焊用的 BOM 和座標檔（只含 SMD 零件；J1–J4 插件手焊）
- `fab/positions.csv`：KiCad 原始座標檔
- `docs/schematic.pdf`、`docs/pcb_front.png`：原理圖 PDF 和 PCB 正面預覽
- `docs/nanopc-t4_40pin.md`：NanoPC-T4 40-pin 腳位表和接線注意事項
- `software/lis3dh_test.py`：在 T4 上讀取 X/Y/Z 的測試程式
- `scripts/gen_sch.py`：產生原理圖的腳本
- `scripts/route.sh`、`scripts/route_pcb.py`：自動佈線流程（KiCad 10 Docker + Freerouting 1.9）

## Layout
- 板子 87.6 × 25.4 mm，雙層；零件擺放和最終走線為手動調整（初版由 Freerouting 自動佈線）
- B.Cu 整面 GND；F.Cu 空白處鋪 GND，另加 6 顆 GND 縫合過孔
- 網路類別（定義在 `.kicad_pro`）：

| 類別 | 網路 | 線寬 | 間距 |
|---|---|---|---|
| Default | 訊號、+3V0、GND | 0.25 mm | 0.13 mm |
| Power | +5V、VRF1、VRF2、VCC_RF | 0.4 mm | 0.15 mm |
| ANT | ANT1、ANT2（天線，50–100 Vpp） | 0.3 mm | 0.4 mm |

- +3V0 和 GND 用 0.25 mm，因為要接進 LIS3DH 0.5 mm 腳距的焊墊；這兩個網路電流都很小
- ANT 間距 0.4 mm：PicoBlade 兩腳本身只有 0.45 mm，走線上有防焊漆覆蓋，100 Vpp 在 IPC-2221 塗覆走線的範圍內
- 過孔 0.6/0.3 mm，在 JLCPCB 標準製程範圍內

重新佈線（會清掉現有走線，零件位置不動）：
```bash
scripts/route.sh /path/to/freerouting-1.9.0.jar
```
