# NanoPC-T4 40-pin 排針腳位

來源：FriendlyELEC Wiki 的 NanoPC-T4 頁面「GPIO Pin Spec」表格。

| Pin | 定義 | 電壓 | | Pin | 定義 | 電壓 |
|---|---|---|---|---|---|---|
| 1 | VCC3V3_SYS | 3.3V 電源 | | 2 | VCC5V0_SYS | 5V 電源 |
| 3 | **I2C2_SDA** | 3V | | 4 | VCC5V0_SYS | 5V 電源 |
| 5 | **I2C2_SCL** | 3V | | 6 | GND | |
| 7 | GPIO1_A0 | 3V | | 8 | GPIO4_C1 / I2C3_SCL | 3V |
| 9 | GND | | | 10 | GPIO4_C0 / I2C3_SDA | 3V |
| 11 | GPIO1_A1 | 3V | | 12 | GPIO1_C2 | 3V |
| 13 | GPIO1_A3 | 3V | | 14 | GND | |
| 15 | GPIO1_A4 | 3V | | 16 | GPIO1_C6 | 3V |
| 17 | VCC3V3_SYS | 3.3V 電源 | | 18 | GPIO1_C7 | 3V |
| 19 | SPI1_TXD / UART4_TX | 3V | | 20 | GND | |
| 21 | SPI1_RXD / UART4_RX | 3V | | 22 | GPIO1_D0 | 3V |
| 23 | SPI1_CLK | 3V | | 24 | SPI1_CSn0 | 3V |
| 25 | GND | | | 26 | GPIO4_C5 / SPDIF_TX | 3V |
| 27 | I2C2_SDA | **1.8V** | | 28 | I2C2_SCL | **1.8V** |
| 29 | I2S1_LRCK_RX | **1.8V** | | 30 | GND | |
| 31 | I2S1_LRCK_TX | **1.8V** | | 32 | I2S_CLK | **1.8V** |
| 33 | I2S1_SCLK | **1.8V** | | 34 | GND | |
| 35 | I2S1_SDI0 | **1.8V** | | 36 | I2S1_SDO0 | **1.8V** |
| 37 | GPIO3_D4 | **1.8V** | | 38 | GPIO3_D5 | **1.8V** |
| 39 | GND | | | 40 | GPIO3_D6 | **1.8V** |

## 和 LIS3DH 小板的對應
| 小板 J1 | 訊號 | T4 腳位 |
|---|---|---|
| 1 | VIN | 2（5V） |
| 2 | GND | 6 |
| 3 | SCL | 5（I2C2_SCL，3V） |
| 4 | SDA | 3（I2C2_SDA，3V） |
| 5 | INT1 | 11（GPIO1_A1，3V，選用） |
| 6 | CHG_INT | 7（GPIO1_A0，3V） |

## 注意
- **27、28 腳**也標成 I2C2，但準位是 1.8V，不要接 3.0V 的小板。這兩組腳位可能是同一條 I2C2 匯流排經過電位轉換拉出來的，所以 27/28 上如果有其他裝置，位址不能和 0x18 衝突。
- **29–40 腳**全部是 1.8V，不可以接 3V 訊號。
- **8、10 腳**的 I2C3（3V）是備用匯流排，在 Linux 裡對應 `/dev/i2c-3`。
- **19、21 腳**由 SPI1 和 UART4 共用，同時只能啟用其中一個。
- **3V 的 GPIO 不耐 5V**，5V 只能當電源輸入用。
