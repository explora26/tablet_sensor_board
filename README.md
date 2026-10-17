# LIS3DH 三軸加速度計小板（NanoPC-T4 I2C2）

板上用 LDO 轉出 3.0V，讓 I2C 電位和 NanoPC-T4 的 I2C2（3.0V I/O）一致，同時經 JST 接頭供電和 I2C 給 BQ25798 充電板。

**狀態：原理圖完成，layout 尚未開始（板子尺寸待定）。**

## 規格
| 項目 | 內容 |
|---|---|
| 感測器 | ST LIS3DH，LGA-16 3×3 mm |
| I2C 位址 | 0x18（SA0 接 GND），WHO_AM_I = 0x33 |
| 電源 | VIN 3.3–5.5V → TLV75530（3.0V，500 mA） |
| 上拉電阻 | SCL/SDA 各 4.7k 上拉到 3.0V（R1/R2，T4 的上拉夠用時可以不焊） |
| 介面 | J1：1×7 排針，2.54 mm，接 T4；J2：JST PH 2.0 5 pin，接 BQ25798 充電板；J3：1×10 排母，插 WL-125 RFID 模組 |
| 固定 | 建議至少 2 個螺絲孔（加速度計要鎖緊固定，量測才準），layout 時決定 |

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
| 2 | INT | BQ25798 的 /INT（開汲極，低電位觸發），在小板上用 R3（10k）上拉到 3.0V，再經 J1 第 6 腳送到 T4 |
| 3 | I2C_SCL | 和 T4 的 I2C2 共用匯流排 |
| 4 | I2C_SDA | 同上 |
| 5 | 3V | 小板輸出的 3.0V（來自 U1），供充電板的上拉電阻和邏輯電路使用 |

I2C2 上的位址：LIS3DH 是 0x18，BQ25798 是 0x6B，沒有衝突。

## J3 ↔ WL-125 125kHz RFID 模組（1×10 排母，2.54 mm）
模組焊 10P 排針直接插上；模組只有 9 支腳，J3 第 10 腳是防呆位。

| J3 | 模組腳位 | 小板上的接法 |
|---|---|---|
| 1 | 天線 1 | 不接。天線線圈直接焊在模組上，這兩腳有 50–100 Vpp 諧振電壓 |
| 2 | 天線 2 | 不接，同上 |
| 3 | 輸出模式選擇 | 接 VCC_RF（高電位 = UART 輸出，規格書規定不可懸空） |
| 4 | 蜂鳴器輸出 | 不接 |
| 5 | TX（9600 8N1，5V TTL） | 經 Q1 BSS138 電位轉換成 3.0V（RFID_TX），送到 J1 第 7 腳 |
| 6 | 維根 D0 | 不接 |
| 7 | /RESET（低電位有效） | R7 10k 上拉到 VCC_RF |
| 8 | GND | GND |
| 9 | VCC（5V） | VCC_RF：+5V 經 R6 2.2Ω，再並 C5 1000µF + C6 100nF 濾波 |
| 10 | — | 防呆位，不接 |

- 電位轉換：Q1 BSS138 + R4/R5 各 10k 上拉（3.0V 側 / 5V 側），和 Adafruit #757 相同架構
- 卡號格式：`02` + 10 字元 ASCII 卡號 + 1 byte 校驗（XOR）+ `03`，共 13 bytes
- 規格書強調電源要乾淨：不要從 DC-DC 電感附近供電，C5 要靠近 J3
- Layout 注意：J3 第 1、2 腳周圍不要鋪銅、不要走線，間距拉大；天線線圈遠離金屬和鋪銅

> 不要接 27、28 腳：那組 I2C2 是 1.8V。完整腳位見 `docs/nanopc-t4_40pin.md`。

## 檔案
- `lis3dh_board.kicad_pro`、`lis3dh_board.kicad_sch`：KiCad 專案（以 KiCad 7 格式產生，KiCad 10 開啟後會提示升級格式）
- `docs/schematic.pdf`：原理圖 PDF
- `docs/nanopc-t4_40pin.md`：NanoPC-T4 40-pin 腳位表和接線注意事項
- `fab/bom.csv`：BOM（尚未對應 LCSC 料號）
- `software/lis3dh_test.py`：在 T4 上讀取 X/Y/Z 的測試程式
- `scripts/gen_sch.py`：產生原理圖的腳本
- `scripts/gen_pcb.py`：自動擺放零件和佈線的實驗腳本，零件位置是寫死的，加入 J2、R3 之後還沒更新

## Layout（待辦）
板子尺寸決定後，在 KiCad 10 裡開啟 PCB 編輯器，按 F8（從原理圖更新 PCB）帶入零件，再進行擺放和佈線。

建議：
- C3、C4 靠近 LIS3DH 的 VDD（pin 14）
- LIS3DH 放在螺絲孔附近、遠離接頭，減少拔插時的應力
- B.Cu 整面 GND
- 線寬 0.25 mm、間距 0.13 mm、過孔 0.6/0.3 mm，在 JLCPCB 標準製程範圍內
