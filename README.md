# 🌤️ Taiwan Weather Forecast — 台灣一週天氣預報互動式 Web App

> **AI 創新微課程：CWA API × JSON × Python × SQLite × Streamlit**  
> *從氣象資料到互動式天氣預報應用 · Code Smarter, Build a Better Tomorrow!*  
> 導師：煥哥

---

## 📌 專案架構概覽 (24 步驟完整實作)

本專案嚴格遵循「煥哥 - AI 創新微課程」24 步驟學習地圖打造：

| 階段 | 步驟 | 重點內容 | 對應檔案 |
|---|---|---|---|
| **基礎概念** | 1 ~ 3 | 課程介紹、生活應用重要性、中央氣象署 CWA API 授權取得 | `README.md` |
| **資料獲取** | 4 ~ 7 | `requests` 串接 CWA API、JSON 結構解析、提取 MinT/MaxT、Pandas 整理 | `cwa_service.py` |
| **資料庫構建** | 8 ~ 10 | 建立 SQLite `data.db`、`TemperatureForecasts` 表設計、SQL 檢驗驗證 | `database.py` |
| **Web 應用開發** | 11 ~ 16 | Streamlit 入門、SQL 讀取資料、地區下拉選單、繪製一週最高/最低溫折線圖、資料表格整合 | `app.py` |
| **進階視覺化** | 17 ~ 19 | Folium 台灣地圖視覺化、依平均氣溫自適應呈色、選擇日期動態地圖展示、完整儀表板 | `app.py` |
| **工程優化** | 20 ~ 21 | 重複執行不重複寫入 (`ON CONFLICT REPLACE`)、錯誤回退機制、Git / GitHub 準備 | `database.py`, `requirements.txt` |
| **創新延伸** | 22 ~ 24 | AI 穿衣/降雨生活指南、LINE Bot / 智慧旅遊延伸發想、重點回顧與總結 | `app.py` |

---

## 🚀 快速啟動指南

### 1. 安裝所需相依套件

```bash
pip install -r requirements.txt
```

### 2. 同步氣象署資料至 SQLite 資料庫

```bash
python cwa_service.py
```
> 會自動連線至中央氣象署 Open Data API（包含全臺 22 縣市 `F-D0047-091` 與 9 大分區 `F-C0032-003`），並將全臺一週高低溫預報存入 `data.db` 中的 `TemperatureForecasts` 資料表。

### 3. 啟動 Streamlit 互動式 Web 網站

```bash
python -m streamlit run app.py
```
瀏覽器會自動開啟 `http://localhost:8501`。

---

## 📊 資料庫設計 (Step 9)

```sql
CREATE TABLE IF NOT EXISTS TemperatureForecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regionName TEXT NOT NULL,          -- 地區名稱 (如：中部地區、北部地區...)
    dataDate TEXT NOT NULL,            -- 預報日期 (YYYY-MM-DD)
    minT REAL NOT NULL,                -- 最低氣溫 (°C)
    maxT REAL NOT NULL,                -- 最高氣溫 (°C)
    weather TEXT DEFAULT '',           -- 天氣現象描述 (如：晴時多雲、陣雨)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(regionName, dataDate) ON CONFLICT REPLACE  -- 防止重複插入 (Step 20)
);
```

---

## 🗺️ 台灣地圖色階標準 (Step 17)

地圖圓形標記根據「平均氣溫 $(MinT + MaxT) / 2$」自動呈現對應色彩：

- 🔵 **寒冷**：$< 20^\circ\text{C}$ (`#2563eb`)
- 🟢 **舒適**：$20 \sim 25^\circ\text{C}$ (`#10b981`)
- 🟡 **溫暖**：$25 \sim 30^\circ\text{C}$ (`#f59e0b`)
- 🔴 **炎熱**：$> 30^\circ\text{C}$ (`#ef4444`)

---

## 🛠️ 技術模組說明

- **`cwa_service.py`**：封裝 CWA API 請求、支援 SSL 異常自動 Fallback、JSON 階層遞迴解析與座標對應。
- **`database.py`**：SQLite 連線池管理、查詢封裝（包含 SQL 注入防護與多維度查詢）。
- **`app.py`**：全功能 Streamlit 前端應用，包含互動式 Folium 地圖、Altair 雙色折線圖、動態資料表格與 AI 生活指引。
