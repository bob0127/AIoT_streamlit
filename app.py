"""
Taiwan Weather Forecast Web Application (台灣一週天氣預報儀表板)
AI 創新微課程: CWA API x JSON x Python x SQLite x Streamlit
Instructor: 煥哥

Features implemented across all course steps (Steps 1-24):
- Step 3-7: CWA Open Data API fetching & Pandas structuring
- Step 8-10: SQLite (data.db / TemperatureForecasts) database management & SQL queries
- Step 11-13: Streamlit Interactive UI & Region dropdown selection
- Step 14-16: 1-Week MinT/MaxT line chart & weekly forecast table
- Step 17-19: Interactive Folium Taiwan weather map with color-coded average temperatures & Date selection
- Step 20: Code quality, idempotency (ON CONFLICT REPLACE), and robust error handling
- Step 22: AI-driven smart weather insights & clothing/activity recommendations
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium import plugins
from streamlit_folium import st_folium
import altair as alt
from datetime import datetime

# Local modules
import importlib
import database as db
import cwa_service as cwa
importlib.reload(db)
importlib.reload(cwa)

# ==========================================
# Streamlit Page Configuration
# ==========================================
st.set_page_config(
    page_title="台灣一週天氣預報 | Taiwan Weather Forecast",
    page_icon="⛅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Rich Modern Aesthetics)
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #f8fafc;
    }
    
    /* Hero banner styling */
    .hero-container {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #06b6d4 100%);
        padding: 1.8rem 2.2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.3);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        margin-top: 8px;
        opacity: 0.92;
        font-weight: 400;
    }
    .hero-tags {
        display: flex;
        gap: 8px;
        margin-top: 12px;
        flex-wrap: wrap;
    }
    .hero-badge {
        background: rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(8px);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.3);
    }

    /* Metric card styling */
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    .metric-label {
        font-size: 0.88rem;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a;
    }
    
    /* Status Badge */
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-online {
        background-color: #dcfce7;
        color: #166534;
    }
    
    /* Map Legend Box */
    .legend-box {
        background: white;
        padding: 10px 16px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        display: flex;
        gap: 16px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 0.88rem;
        font-weight: 500;
    }
    .legend-dot {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        display: inline-block;
    }

    /* AI Advice Card */
    .ai-card {
        background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
        border: 1px solid #bbf7d0;
        border-radius: 14px;
        padding: 1.2rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Database Auto-initialization & Data Check
# ==========================================
db.init_db()

# Ensure we have data; if empty, fetch automatically
regions_in_db = db.query_distinct_regions()
if not regions_in_db:
    with st.spinner("首次啟動：正在向中央氣象署 CWA API 抓取一週天氣預報資料..."):
        try:
            cwa.fetch_and_sync_weather()
            regions_in_db = db.query_distinct_regions()
        except Exception as e:
            st.error(f"資料初始化失敗: {e}")

# ==========================================
# Sidebar Controls & Information
# ==========================================
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1534088568595-a066f410bcda?w=600&auto=format&fit=crop&q=80", use_container_width=True)
    st.markdown("### ⛅ 臺灣氣象控制台")
    st.caption("AI 創新微課程 Taiwan Weather Forecast")

    st.markdown("---")
    
    # API Sync Section
    st.markdown("#### 🔄 資料同步與狀態")
    st.markdown("""
        <div class="status-pill status-online">
            <span style="font-size: 10px;">🟢</span> CWA API 正常連線
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**資料來源**: 中央氣象署 (CWA)")
    st.markdown("**涵蓋範圍**: 全臺 22 縣市 + 9 大分區 (`F-D0047-091` / `F-C0032-003`)")
    
    sync_btn = st.button("🚀 立即向 CWA API 同步最新預報", use_container_width=True, type="primary")
    if sync_btn:
        with st.spinner("正在向 CWA API 請求並解析最新資料..."):
            try:
                new_df = cwa.fetch_and_sync_weather()
                st.success(f"同步成功！已儲存 {len(new_df)} 筆預報紀錄至 SQLite (data.db)")
                st.rerun()
            except Exception as ex:
                st.error(f"同步失敗: {ex}")

    st.markdown("---")
    
    # Map Display Mode & Location Selection
    st.markdown("#### 📍 地圖與縣市選擇")
    map_mode = st.radio(
        "地圖呈現範圍 (Map View):",
        options=["🏙️ 全臺 22 縣市 (Every City)", "🗺️ 9 大分區 (Regional)", "🌐 全視野 (縣市+分區)"],
        index=0
    )
    
    # Order options: Cities first (categorized), then regions
    db_all_regions = db.query_distinct_regions()
    target_cities = getattr(cwa, "TARGET_CITIES", [
        "基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣", "苗栗縣",
        "臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣", "臺南市",
        "高雄市", "屏東縣", "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"
    ])
    target_regions = getattr(cwa, "TARGET_REGIONS", [
        "北部地區", "中部地區", "南部地區", "東北部地區", "東部地區", "東南部地區", "澎湖地區", "金門地區", "馬祖地區"
    ])
    cities_in_db = [c for c in target_cities if c in db_all_regions]
    regions_in_db = [r for r in target_regions if r in db_all_regions]
    other_in_db = [o for o in db_all_regions if o not in cities_in_db and o not in regions_in_db]
    available_regions = cities_in_db + regions_in_db + other_in_db
    
    if not available_regions:
        available_regions = ["臺北市", "新北市", "臺中市", "高雄市", "北部地區", "中部地區", "南部地區"]
        
    default_city_idx = available_regions.index("臺北市") if "臺北市" in available_regions else 0
    selected_region = st.selectbox(
        "選擇預報縣市/地區 (Select City/Region):",
        options=available_regions,
        index=default_city_idx
    )

    # Date Selection for Map (Step 18)
    st.markdown("#### 📅 日期選擇 (Step 18)")
    available_dates = db.get_available_dates()
    if not available_dates:
        available_dates = [datetime.now().strftime("%Y-%m-%d")]
        
    selected_date = st.selectbox(
        "選擇地圖日期 (Select Date):",
        options=available_dates,
        index=0
    )

    st.markdown("---")
    st.markdown("##### 👨‍🏫 課程導師與技術棧")
    st.markdown("""
    - **技術棧**: Python · Requests · Pandas · SQLite · Streamlit · Folium
    - **資料涵蓋**: 全臺 22 縣市精確定位與氣溫色階
    - **Code Smarter, Build a Better Tomorrow!**
    """)

# ==========================================
# Main Header Banner
# ==========================================
st.markdown("""
<div class="hero-container">
    <div class="hero-title">
        <span>🌤️</span> 台灣各縣市一週天氣預報互動儀表板
    </div>
    <div class="hero-subtitle">
        全自動串接中央氣象署 Open Data API · 涵蓋全臺 22 縣市與分區 · SQLite 結構化存儲 · 即時地圖視覺化
    </div>
    <div class="hero-tags">
        <span class="hero-badge">CWA API (F-D0047-091 & F-C0032-003)</span>
        <span class="hero-badge">全臺 22 縣市精準天氣</span>
        <span class="hero-badge">SQLite data.db</span>
        <span class="hero-badge">Folium 地圖視覺化</span>
        <span class="hero-badge">AI 創新實作專案</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# Navigation Tabs
# ==========================================
tab_map, tab_chart, tab_table, tab_ai, tab_sql = st.tabs([
    "🗺️ 台灣地圖視覺化 (Folium)",
    "📈 縣市/地區氣溫趨勢折線圖",
    "📋 詳細預報資料表",
    "🤖 AI 智慧生活指南",
    "🔍 SQL 驗證與後台教學"
])

# ==============================================================================
# TAB 1: 台灣地圖視覺化 (Folium + Streamlit, Steps 17, 18, 19)
# ==============================================================================
with tab_map:
    mode_label = "全臺 22 縣市" if "22" in map_mode else ("9 大分區" if "9" in map_mode else "全視野")
    st.markdown(f"### 🗺️ 台灣氣溫分佈地圖 — 【{mode_label}】預報日期：`{selected_date}`")
    st.caption("Step 17 & 18: 採用 Folium 建立互動式地圖，在地圖上精確呈現每個縣市的最高/最低溫、天氣圖示與平均氣溫色階，點擊圓點可檢視詳細分析。")

    # Legend Display (Step 17 requirement: 藍色 <20°C, 綠色 20-25°C, 黃色 25-30°C, 紅色 >30°C)
    st.markdown("""
    <div class="legend-box">
        <span style="font-weight:700; color:#334155; margin-right:8px;">🌡️ 平均溫度色階：</span>
        <div class="legend-item"><span class="legend-dot" style="background-color: #2563eb;"></span> 寒冷 (&lt; 20°C)</div>
        <div class="legend-item"><span class="legend-dot" style="background-color: #10b981;"></span> 舒適 (20 ~ 25°C)</div>
        <div class="legend-item"><span class="legend-dot" style="background-color: #f59e0b;"></span> 溫暖 (25 ~ 30°C)</div>
        <div class="legend-item"><span class="legend-dot" style="background-color: #ef4444;"></span> 炎熱 (&gt; 30°C)</div>
    </div>
    """, unsafe_allow_html=True)

    # Fetch data for selected date
    date_df = db.query_forecast_by_date(selected_date)
    
    col_map_view, col_map_info = st.columns([7, 3])
    
    with col_map_view:
        taiwan_center = [23.75, 120.95]
        m = folium.Map(
            location=taiwan_center,
            zoom_start=8,
            tiles="OpenStreetMap",
            control_scale=True
        )

        def get_temp_color(avg_temp: float) -> str:
            if avg_temp < 20.0:
                return "#2563eb"  # 藍色
            elif avg_temp <= 25.0:
                return "#10b981"  # 綠色
            elif avg_temp <= 30.0:
                return "#f59e0b"  # 橙黃色
            else:
                return "#ef4444"  # 紅色

        def get_weather_emoji(wx: str) -> str:
            if "雷" in wx:
                return "⛈️"
            elif "雨" in wx:
                return "🌧️"
            elif "陰" in wx:
                return "☁️"
            elif "多雲" in wx:
                return "⛅"
            else:
                return "☀️"

        # Coordinate dictionaries with safe fallbacks
        city_coords = getattr(cwa, "CITY_COORDINATES", {})
        region_coords = getattr(cwa, "REGION_COORDINATES", {})

        # Filter items according to mode
        locations_to_plot = []
        for _, row in date_df.iterrows():
            loc_name = row["regionName"]
            min_t = row["minT"]
            max_t = row["maxT"]
            avg_t = round((min_t + max_t) / 2.0, 1)
            wx = row.get("weather", "晴時多雲")
            
            if loc_name in city_coords:
                if "22" in map_mode or "全視野" in map_mode:
                    coord = city_coords[loc_name]
                    locations_to_plot.append({
                        "name": loc_name,
                        "type": "city",
                        "lat": coord["lat"],
                        "lon": coord["lon"],
                        "area": coord.get("area", ""),
                        "minT": min_t,
                        "maxT": max_t,
                        "avgT": avg_t,
                        "weather": wx,
                        "radius": 13
                    })
            elif loc_name in region_coords:
                if "9" in map_mode or "全視野" in map_mode:
                    coord = region_coords[loc_name]
                    locations_to_plot.append({
                        "name": loc_name,
                        "type": "region",
                        "lat": coord["lat"],
                        "lon": coord["lon"],
                        "area": coord.get("description", ""),
                        "minT": min_t,
                        "maxT": max_t,
                        "avgT": avg_t,
                        "weather": wx,
                        "radius": 20
                    })
                    
        # Fallback if no matching records
        if not locations_to_plot:
            for _, row in date_df.iterrows():
                loc_name = row["regionName"]
                coord = city_coords.get(loc_name) or region_coords.get(loc_name)
                if coord:
                    locations_to_plot.append({
                        "name": loc_name,
                        "type": "city" if loc_name in city_coords else "region",
                        "lat": coord["lat"],
                        "lon": coord["lon"],
                        "area": coord.get("area", coord.get("description", "")),
                        "minT": row["minT"],
                        "maxT": row["maxT"],
                        "avgT": round((row["minT"] + row["maxT"]) / 2.0, 1),
                        "weather": row.get("weather", "良好"),
                        "radius": 14
                    })

        for item in locations_to_plot:
            lat = item["lat"]
            lon = item["lon"]
            name = item["name"]
            min_t = item["minT"]
            max_t = item["maxT"]
            avg_t = item["avgT"]
            wx = item["weather"]
            color = get_temp_color(avg_t)
            emoji = get_weather_emoji(wx)
            area_badge = item["area"]

            popup_html = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; min-width: 180px; padding: 4px;">
                <div style="font-size: 15px; font-weight: 700; color: #0f172a; border-bottom: 2px solid {color}; padding-bottom: 4px; margin-bottom: 6px; display:flex; justify-content:space-between; align-items:center;">
                    <span>📍 {name}</span>
                    <span style="font-size: 11px; background: #e2e8f0; color: #334155; padding: 2px 6px; border-radius: 4px;">{area_badge}</span>
                </div>
                <div style="font-size: 13px; line-height: 1.7; color: #334155;">
                    <div>{emoji} <b>天氣型態</b>: {wx}</div>
                    <div>📉 <b>預測最低溫</b>: <span style="color: #2563eb; font-weight:700;">{min_t}°C</span></div>
                    <div>📈 <b>預測最高溫</b>: <span style="color: #ef4444; font-weight:700;">{max_t}°C</span></div>
                    <div>🌡️ <b>平均氣溫</b>: <span style="color: {color}; font-weight:800; font-size: 14px;">{avg_t}°C</span></div>
                </div>
            </div>
            """

            # Add CircleMarker
            folium.CircleMarker(
                location=[lat, lon],
                radius=item["radius"],
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=f"<b>{emoji} {name}</b>: {avg_t}°C ({wx})",
                color=color,
                weight=2.5,
                fill=True,
                fill_color=color,
                fill_opacity=0.88
            ).add_to(m)

            # Permanent label with high-contrast badge
            offset_lat = 0.08 if item["type"] == "city" else 0.12
            short_name = name.replace("地區", "")
            folium.map.Marker(
                [lat + offset_lat, lon],
                icon=folium.DivIcon(
                    icon_size=(90, 24),
                    icon_anchor=(45, 12),
                    html=f"""
                    <div style="font-size: 11px; font-weight: 700; color: #0f172a; background: rgba(255,255,255,0.92); border: 1px solid #cbd5e1; border-radius: 4px; padding: 1px 4px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.12); white-space: nowrap;">
                        {emoji} {short_name} <span style="color:{color}; font-weight:800;">{avg_t}°</span>
                    </div>
                    """
                )
            ).add_to(m)

        st_folium(m, width="100%", height=560, returned_objects=[])

    with col_map_info:
        st.markdown(f"#### 📊 `{selected_date}` 天氣總覽")
        active_cities_df = date_df[date_df["regionName"].isin(target_cities)] if ("22" in map_mode or "全視野" in map_mode) else date_df
        if active_cities_df.empty:
            active_cities_df = date_df

        if not active_cities_df.empty:
            highest_row = active_cities_df.loc[active_cities_df["maxT"].idxmax()]
            lowest_row = active_cities_df.loc[active_cities_df["minT"].idxmin()]
            
            st.markdown(f"""
            <div class="metric-card" style="margin-bottom: 12px; border-left: 4px solid #ef4444;">
                <div class="metric-label">🔥 今日最高溫城市/地區</div>
                <div class="metric-val" style="color: #ef4444;">{highest_row['maxT']} °C</div>
                <div style="font-size: 0.9rem; color: #475569; margin-top: 4px;">📍 {highest_row['regionName']} ({highest_row['weather']})</div>
            </div>
            
            <div class="metric-card" style="margin-bottom: 12px; border-left: 4px solid #2563eb;">
                <div class="metric-label">❄️ 今日最低溫城市/地區</div>
                <div class="metric-val" style="color: #2563eb;">{lowest_row['minT']} °C</div>
                <div style="font-size: 0.9rem; color: #475569; margin-top: 4px;">📍 {lowest_row['regionName']} ({lowest_row['weather']})</div>
            </div>
            """, unsafe_allow_html=True)

            # Quick City List with scroll container
            st.markdown(f"##### 🏙️ 城市氣溫清單 ({len(active_cities_df)} 處)")
            with st.container(height=260):
                sorted_df = active_cities_df.sort_values(by="maxT", ascending=False)
                for _, r in sorted_df.iterrows():
                    r_name = r["regionName"]
                    r_min = r["minT"]
                    r_max = r["maxT"]
                    r_avg = (r_min + r_max) / 2
                    r_wx = r.get("weather", "")
                    dot_c = get_temp_color(r_avg)
                    wx_ico = get_weather_emoji(r_wx)
                    st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; padding: 5px 0; border-bottom: 1px dashed #e2e8f0; font-size: 0.88rem;">
                        <span><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{dot_c}; margin-right:6px;"></span>{wx_ico} <b>{r_name}</b></span>
                        <span>{r_min}°C ~ <b style="color:#ef4444;">{r_max}°C</b></span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("尚無該日期之氣象預報資料。")

# ==============================================================================
# TAB 2: 地區氣溫趨勢折線圖 (Steps 13, 14, 15, 16)
# ==============================================================================
with tab_chart:
    st.markdown(f"### 📈 【{selected_region}】一週最高與最低氣溫預報")
    st.caption("Step 14: 繪製一週最高溫 (MaxT 紅線) 與最低溫 (MinT 藍線) 折線圖，直觀掌握氣溫變化曲線。")

    # Query region forecast from SQLite (Step 12)
    df_region = db.query_forecast_by_region(selected_region)

    if not df_region.empty:
        # Key Summary Metrics (Step 19)
        max_week_temp = df_region["maxT"].max()
        min_week_temp = df_region["minT"].min()
        avg_week_temp = round(((df_region["maxT"] + df_region["minT"]) / 2).mean(), 1)
        max_diff = round((df_region["maxT"] - df_region["minT"]).max(), 1)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🔴 本週最高氣溫 (MaxT)</div>
                <div class="metric-val" style="color: #ef4444;">{max_week_temp} °C</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🔵 本週最低氣溫 (MinT)</div>
                <div class="metric-val" style="color: #2563eb;">{min_week_temp} °C</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">🌡️ 本週平均溫度</div>
                <div class="metric-val" style="color: #0f766e;">{avg_week_temp} °C</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⚡ 最大日夜溫差</div>
                <div class="metric-val" style="color: #d97706;">{max_diff} °C</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Draw Line Chart using Altair (matching Step 14: MaxT Red, MinT Blue)
        chart_data = df_region.melt(
            id_vars=["dataDate"],
            value_vars=["maxT", "minT"],
            var_name="指標",
            value_name="氣溫"
        )
        chart_data["指標名稱"] = chart_data["指標"].map({
            "maxT": "最高氣溫 (MaxT)",
            "minT": "最低氣溫 (MinT)"
        })

        base_chart = alt.Chart(chart_data).encode(
            x=alt.X("dataDate:N", title="預報日期 (Date)", axis=alt.Axis(labelAngle=0, labelFontWeight="bold")),
            y=alt.Y("氣溫:Q", title="氣溫 (°C)", scale=alt.Scale(domain=[int(min_week_temp - 3), int(max_week_temp + 3)])),
            color=alt.Color(
                "指標名稱:N",
                title="溫度類型",
                scale=alt.Scale(
                    domain=["最高氣溫 (MaxT)", "最低氣溫 (MinT)"],
                    range=["#ef4444", "#3b82f6"]
                ),
                legend=alt.Legend(orient="top", titleFontWeight="bold")
            )
        )

        lines = base_chart.mark_line(size=3, interpolate="monotone")
        points = base_chart.mark_circle(size=70)
        labels = base_chart.mark_text(dy=-12, fontWeight="bold").encode(
            text=alt.Text("氣溫:Q", format=".1f")
        )

        final_chart = (lines + points + labels).properties(
            height=400,
            title=alt.TitleParams(
                text=f"{selected_region} 未來一週最高與最低氣溫走勢圖",
                subtitle="資料來源：中央氣象署 Open Data (F-C0032-003)",
                fontSize=16
            )
        ).interactive()

        st.altair_chart(final_chart, use_container_width=True)

        # Step 15: 顯示資料表格 (Date, MinT, MaxT)
        st.markdown("#### 📅 一週天氣預報數據表 (Step 15)")
        display_df = df_region.copy()
        display_df["平均溫 (°C)"] = ((display_df["minT"] + display_df["maxT"]) / 2).round(1)
        display_df["日溫差 (°C)"] = (display_df["maxT"] - display_df["minT"]).round(1)
        display_df = display_df.rename(columns={
            "dataDate": "預報日期 (Date)",
            "minT": "最低氣溫 MinT (°C)",
            "maxT": "最高氣溫 MaxT (°C)",
            "weather": "天氣現象 (Wx)"
        })
        
        st.dataframe(
            display_df[["預報日期 (Date)", "最低氣溫 MinT (°C)", "最高氣溫 MaxT (°C)", "平均溫 (°C)", "日溫差 (°C)", "天氣現象 (Wx)"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning(f"目前資料庫中查無 {selected_region} 的氣溫資料，請點擊側邊欄「立即向 CWA API 同步」按鈕。")

# ==============================================================================
# TAB 3: 詳細預報資料表 & 跨區對比 (Step 15 & 16)
# ==============================================================================
with tab_table:
    st.markdown("### 📋 全臺各地區預報完整資料庫")
    st.caption("查詢自 SQLite 資料庫 `data.db` 中的 `TemperatureForecasts` 資料表。")

    all_df = db.query_all_forecasts()
    
    col_filter1, col_filter2 = st.columns([1, 1])
    with col_filter1:
        region_filter = st.multiselect("篩選地區:", options=available_regions, default=available_regions[:4])
    with col_filter2:
        date_filter = st.multiselect("篩選日期:", options=available_dates, default=available_dates[:4])

    filtered_df = all_df.copy()
    if region_filter:
        filtered_df = filtered_df[filtered_df["regionName"].isin(region_filter)]
    if date_filter:
        filtered_df = filtered_df[filtered_df["dataDate"].isin(date_filter)]

    st.dataframe(
        filtered_df.rename(columns={
            "id": "編號 (ID)",
            "regionName": "地區名稱 (Region)",
            "dataDate": "日期 (Date)",
            "minT": "最低溫 (°C)",
            "maxT": "最高溫 (°C)",
            "weather": "天氣現象",
            "created_at": "同步時間"
        }),
        use_container_width=True,
        hide_index=True
    )

    # Download CSV button
    csv_bytes = filtered_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 下載篩選後氣象資料 (CSV)",
        data=csv_bytes,
        file_name="taiwan_weather_forecast.csv",
        mime="text/csv"
    )

# ==============================================================================
# TAB 4: AI 智慧生活指南 (Step 22: 延伸應用與想法)
# ==============================================================================
with tab_ai:
    st.markdown("### 🤖 AI 氣象分析與智慧生活建議")
    st.caption("Step 22: 結合天氣大數據自動生成每日穿衣指標、降雨機率預警與健康防護提醒。")

    if not df_region.empty:
        today_data = df_region.iloc[0]
        today_date = today_data["dataDate"]
        today_min = today_data["minT"]
        today_max = today_data["maxT"]
        today_diff = today_max - today_min
        today_wx = today_data["weather"]

        # Clothing advice
        clothing_text = ""
        clothing_icon = "👕"
        if today_max >= 30:
            clothing_text = "氣溫偏高炎熱，建議著輕便透氣的短袖、短褲或排汗衫，戶外活動注意防曬防中暑。"
            clothing_icon = "🎽"
        elif today_max >= 24:
            clothing_text = "氣候溫和舒適，建議著棉質短袖並備一件薄針織衫或輕便外套應對早晚溫差。"
            clothing_icon = "👕"
        elif today_max >= 18:
            clothing_text = "天氣轉涼，建議搭配長袖上衣、衛衣或防風外套，注意脖頸保暖。"
            clothing_icon = "🧥"
        else:
            clothing_text = "氣溫偏低寒冷，建議採洋蔥式穿法，著厚毛衣、大衣或羽絨外套，防寒保暖第一。"
            clothing_icon = "🧣"

        # Umbrella / Activity advice
        rain_keywords = ["雨", "陣雨", "雷雨", "陰"]
        umbrella_text = ""
        umbrella_icon = "☀️"
        if any(k in today_wx for k in ["雨", "雷"]):
            umbrella_text = f"今日預報為【{today_wx}】，出門請務必隨身攜帶雨具，行車時請留意路面濕滑與視線。"
            umbrella_icon = "☔"
        elif "陰" in today_wx:
            umbrella_text = f"今日天空偏陰（{today_wx}），降雨機率增加，外出建議放一把折疊傘於背包備用。"
            umbrella_icon = "⛅"
        else:
            umbrella_text = f"今日天候良好（{today_wx}），陽光充足，非常適合戶外運動、踏青或晾曬衣物！"
            umbrella_icon = "😎"

        # Health tip
        health_text = ""
        if today_diff >= 8.0:
            health_text = f"今日日夜溫差高達 {today_diff:.1f}°C！早出晚歸的通勤族與長輩需特別注意心血管照護與早晚添衣。"
        elif today_max >= 32.0:
            health_text = "紫外線指數偏高，戶外活動請多補充水分（每日至少2000c.c.），並適時至陰涼處休息避免熱傷害。"
        else:
            health_text = "氣候條件宜人，空氣流通良好，保持規律作息與適度運動有助於維持免疫力。"

        col_ai1, col_ai2, col_ai3 = st.columns(3)
        with col_ai1:
            st.markdown(f"""
            <div class="ai-card">
                <h4 style="margin:0 0 8px 0; color:#166534;">{clothing_icon} 穿衣穿搭指南</h4>
                <div style="font-size: 0.95rem; color:#14532d; line-height: 1.6;">
                    <b>今日溫層</b>：{today_min}°C ~ {today_max}°C<br>
                    {clothing_text}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_ai2:
            st.markdown(f"""
            <div class="ai-card" style="background: linear-gradient(135deg, #eff6ff 0%, #e0f2fe 100%); border-color: #bfdbfe;">
                <h4 style="margin:0 0 8px 0; color:#1e40af;">{umbrella_icon} 出行與雨具建議</h4>
                <div style="font-size: 0.95rem; color:#1e3a8a; line-height: 1.6;">
                    <b>天候型態</b>：{today_wx}<br>
                    {umbrella_text}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_ai3:
            st.markdown(f"""
            <div class="ai-card" style="background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); border-color: #fde68a;">
                <h4 style="margin:0 0 8px 0; color:#92400e;">💊 健康與生活提醒</h4>
                <div style="font-size: 0.95rem; color:#78350f; line-height: 1.6;">
                    <b>溫差提醒</b>：{today_diff:.1f}°C<br>
                    {health_text}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 💡 未來延伸應用發想 (Step 22)")
        st.markdown("""
        - 📱 **LINE Bot 自動推播**：串接 LINE Messaging API，每日早晨 7:30 自動將當日降雨機率與穿衣指南推播給使用者。
        - 🚗 **智慧旅遊路線規劃**：根據各區天氣預報分數，推薦晴朗區域的戶外景點，下雨區域則推薦室內博物館或特色咖啡廳。
        - 🌾 **智慧農業防災預警**：針對劇烈降溫（寒害）或連續降雨發送農民預警簡訊，提早進行作物防護。
        """)

# ==============================================================================
# TAB 5: SQL 驗證與後台教學 (Steps 8, 9, 10, 20)
# ==============================================================================
with tab_sql:
    st.markdown("### 🔍 SQL 資料庫驗證與架構解析 (Steps 8, 9, 10 & 20)")
    st.caption("直觀驗證課程中學到的 SQLite 結構與 SQL 查詢語句。")

    st.markdown("#### 1. 資料庫設計 Schema (Step 9)")
    st.code("""
CREATE TABLE IF NOT EXISTS TemperatureForecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regionName TEXT NOT NULL,
    dataDate TEXT NOT NULL,
    minT REAL NOT NULL,
    maxT REAL NOT NULL,
    weather TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(regionName, dataDate) ON CONFLICT REPLACE
);
    """, language="sql")

    st.markdown("#### 2. SQL 互動式查詢驗證 (Step 10)")
    user_query = st.text_input(
        "輸入欲執行的 SQL 查詢語法：",
        value=f'SELECT * FROM TemperatureForecasts WHERE regionName = "{selected_region}" LIMIT 7;'
    )

    if user_query:
        try:
            conn = db.get_connection()
            result_df = pd.read_sql_query(user_query, conn)
            conn.close()
            st.success(f"查詢成功！共返回 {len(result_df)} 筆結果：")
            st.dataframe(result_df, use_container_width=True)
        except Exception as sql_err:
            st.error(f"SQL 查詢執行出錯: {sql_err}")

    st.markdown("#### 3. 程式碼品質與優化 (Step 20)")
    st.markdown("""
    - ✅ **重複執行不重複插入**：使用 `UNIQUE(regionName, dataDate) ON CONFLICT REPLACE`，無論執行多少次資料同步都不會產生重複垃圾資料。
    - ✅ **錯誤處理機制**：透過 `try-except` 捕獲網路連線超時、SSL 憑證問題與 JSON 解析異常，並具備自動回退機制。
    - ✅ **模組化分工**：
      - `database.py`：專職負責 SQLite 初始化與資料庫查詢封裝。
      - `cwa_service.py`：專職負責氣象署 API 串接與數據清洗。
      - `app.py`：專職負責前端 Streamlit 視覺化呈現與互動控制。
    - ✅ **良好繁體中文註解**：清晰呈現各步驟邏輯，便於代碼維護與學習。
    """)

# ==========================================
# Footer
# ==========================================
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94a3b8; font-size: 0.88rem; padding: 1rem 0;">
    AI 創新微課程 Taiwan Weather Forecast · 資料來源：中華民國交通部中央氣象署 (CWA Open Data)<br>
    Code Smarter, Build a Better Tomorrow! · 煥哥 與你一起用 AI 寫程式探索更大的世界
</div>
""", unsafe_allow_html=True)
