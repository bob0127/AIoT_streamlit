"""
CWA Weather API Data Fetcher and Processor
Corresponds to Steps 3, 4, 5, 6, 7, 8, and 20 in the course workflow.
Fetches 1-week forecast from Central Weather Administration (CWA), parses JSON,
organizes temperature data with Pandas, and stores into SQLite.
Supports both all 22 Cities/Counties (F-D0047-091) and 9 Regional Divisions (F-C0032-003).
"""

import requests
import json
import urllib3
import pandas as pd
from collections import defaultdict
from typing import List, Dict, Any, Optional
from database import save_forecasts, init_db

# Suppress insecure HTTPS warnings if unverified fallback is used
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Step 3: API Key & Endpoint Configuration
DEFAULT_API_KEY = "CWA-55FDA6D3-A43C-4AE0-BB30-E62D5F684FB2"
DATASET_ID_REGIONS = "F-C0032-003"   # 臺灣各區一週天氣預報 (9 大分區)
DATASET_ID_CITIES = "F-D0047-091"    # 臺灣各縣市一週天氣預報 (全臺 22 縣市)

API_URL_REGIONS = f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/{DATASET_ID_REGIONS}?downloadType=WEB&format=JSON"
API_URL_CITIES = f"https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/{DATASET_ID_CITIES}?downloadType=WEB&format=JSON"

# All 22 Cities and Counties in Taiwan
TARGET_CITIES = [
    "基隆市", "臺北市", "新北市", "桃園市", "新竹市", "新竹縣", "苗栗縣",
    "臺中市", "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣", "臺南市",
    "高雄市", "屏東縣", "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"
]

# Geographic coordinates for every city (Step 17 & 18 enhanced)
CITY_COORDINATES: Dict[str, Dict[str, Any]] = {
    "基隆市": {"lat": 25.1276, "lon": 121.7392, "area": "北部地區", "name": "基隆市"},
    "臺北市": {"lat": 25.0375, "lon": 121.5637, "area": "北部地區", "name": "臺北市"},
    "新北市": {"lat": 25.0118, "lon": 121.4657, "area": "北部地區", "name": "新北市"},
    "桃園市": {"lat": 24.9936, "lon": 121.3010, "area": "北部地區", "name": "桃園市"},
    "新竹市": {"lat": 24.8138, "lon": 120.9675, "area": "北部地區", "name": "新竹市"},
    "新竹縣": {"lat": 24.8387, "lon": 121.0177, "area": "北部地區", "name": "新竹縣"},
    "苗栗縣": {"lat": 24.5602, "lon": 120.8214, "area": "中部地區", "name": "苗栗縣"},
    "臺中市": {"lat": 24.1477, "lon": 120.6736, "area": "中部地區", "name": "臺中市"},
    "彰化縣": {"lat": 24.0518, "lon": 120.5161, "area": "中部地區", "name": "彰化縣"},
    "南投縣": {"lat": 23.9037, "lon": 120.6860, "area": "中部地區", "name": "南投縣"},
    "雲林縣": {"lat": 23.7092, "lon": 120.4313, "area": "中部地區", "name": "雲林縣"},
    "嘉義市": {"lat": 23.4800, "lon": 120.4491, "area": "南部地區", "name": "嘉義市"},
    "嘉義縣": {"lat": 23.4518, "lon": 120.2555, "area": "南部地區", "name": "嘉義縣"},
    "臺南市": {"lat": 22.9997, "lon": 120.2270, "area": "南部地區", "name": "臺南市"},
    "高雄市": {"lat": 22.6273, "lon": 120.3014, "area": "南部地區", "name": "高雄市"},
    "屏東縣": {"lat": 22.5519, "lon": 120.5487, "area": "南部地區", "name": "屏東縣"},
    "宜蘭縣": {"lat": 24.7021, "lon": 121.7377, "area": "東北部地區", "name": "宜蘭縣"},
    "花蓮縣": {"lat": 23.9872, "lon": 121.6016, "area": "東部地區", "name": "花蓮縣"},
    "臺東縣": {"lat": 22.7583, "lon": 121.1444, "area": "東南部地區", "name": "臺東縣"},
    "澎湖縣": {"lat": 23.5712, "lon": 119.5793, "area": "澎湖地區", "name": "澎湖縣"},
    "金門縣": {"lat": 24.4493, "lon": 118.3766, "area": "金門地區", "name": "金門縣"},
    "連江縣": {"lat": 26.1557, "lon": 119.9500, "area": "馬祖地區", "name": "連江縣"}
}

# Primary regional divisions featured in the course
TARGET_REGIONS = [
    "北部地區",
    "中部地區",
    "南部地區",
    "東北部地區",
    "東部地區",
    "東南部地區",
    "澎湖地區",
    "金門地區",
    "馬祖地區"
]

# Regional geographic coordinates for Folium Map (Step 17 & 18)
REGION_COORDINATES: Dict[str, Dict[str, Any]] = {
    "北部地區": {
        "lat": 25.040,
        "lon": 121.530,
        "cities": "基隆市、臺北市、新北市、桃園市、新竹縣市",
        "description": "北部生活圈"
    },
    "中部地區": {
        "lat": 24.160,
        "lon": 120.670,
        "cities": "苗栗縣、臺中市、彰化縣、南投縣、雲林縣",
        "description": "中部平原與盆地"
    },
    "南部地區": {
        "lat": 22.950,
        "lon": 120.280,
        "cities": "嘉義縣市、臺南市、高雄市、屏東縣",
        "description": "南部平原與沿海"
    },
    "東北部地區": {
        "lat": 24.730,
        "lon": 121.750,
        "cities": "宜蘭縣",
        "description": "蘭陽平原與山區"
    },
    "東部地區": {
        "lat": 23.950,
        "lon": 121.550,
        "cities": "花蓮縣",
        "description": "花東縱谷與太平洋岸"
    },
    "東南部地區": {
        "lat": 22.760,
        "lon": 121.120,
        "cities": "臺東縣",
        "description": "東南部海岸與縱谷"
    },
    "澎湖地區": {
        "lat": 23.570,
        "lon": 119.580,
        "cities": "澎湖縣",
        "description": "澎湖群島"
    },
    "金門地區": {
        "lat": 24.440,
        "lon": 118.380,
        "cities": "金門縣",
        "description": "金門群島"
    },
    "馬祖地區": {
        "lat": 26.155,
        "lon": 119.950,
        "cities": "連江縣",
        "description": "馬祖列島"
    }
}

def fetch_cwa_raw_json(url: str = API_URL_REGIONS, api_key: str = DEFAULT_API_KEY) -> Dict[str, Any]:
    """
    Step 4: Fetch raw JSON weather forecast using Requests.
    Sends API Key via Authorization query parameter and header.
    """
    params = {"Authorization": api_key}
    headers = {"Authorization": api_key, "User-Agent": "Taiwan-Weather-Forecast/1.0"}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=12)
        resp.raise_for_status()
        return resp.json()
    except (requests.exceptions.SSLError, requests.exceptions.RequestException):
        # Fallback with unverified context if SSL handshake fails on local environment
        resp = requests.get(url, params=params, headers=headers, verify=False, timeout=15)
        resp.raise_for_status()
        return resp.json()

def parse_weather_json(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Step 5 & 6: Parse JSON data structure for 9 regional divisions.
    Extracts: regionName, dataDate, minT, maxT, weather.
    """
    records: List[Dict[str, Any]] = []
    dataset = raw_data.get("cwaopendata", {}).get("Dataset", {})
    locations_wrapper = dataset.get("Locations", {})
    locations = locations_wrapper.get("Location", [])
    
    if not locations and isinstance(dataset.get("location"), list):
        locations = dataset.get("location")
        
    for loc in locations:
        region_name = loc.get("LocationName") or loc.get("locationName")
        if not region_name or region_name not in TARGET_REGIONS:
            continue
            
        weather_elements = loc.get("WeatherElement") or loc.get("weatherElement", [])
        element_map = {}
        for elem in weather_elements:
            elem_name = elem.get("ElementName") or elem.get("elementName")
            element_map[elem_name] = elem.get("Time") or elem.get("time", [])
            
        max_t_times = element_map.get("最高溫度") or element_map.get("MaxT", [])
        min_t_times = element_map.get("最低溫度") or element_map.get("MinT", [])
        wx_times = element_map.get("天氣現象") or element_map.get("Wx", [])
        
        time_slots = len(max_t_times)
        for i in range(time_slots):
            max_elem = max_t_times[i]
            start_iso = max_elem.get("StartTime") or max_elem.get("startTime", "")
            data_date = start_iso[:10] if len(start_iso) >= 10 else ""
            
            max_val = None
            if "ElementValue" in max_elem:
                max_val = max_elem["ElementValue"].get("MaxTemperature")
            elif "parameter" in max_elem:
                max_val = max_elem["parameter"].get("parameterName")
                
            min_val = None
            if i < len(min_t_times):
                min_elem = min_t_times[i]
                if "ElementValue" in min_elem:
                    min_val = min_elem["ElementValue"].get("MinTemperature")
                elif "parameter" in min_elem:
                    min_val = min_elem["parameter"].get("parameterName")
                    
            weather_desc = ""
            if i < len(wx_times):
                wx_elem = wx_times[i]
                if "ElementValue" in wx_elem:
                    weather_desc = wx_elem["ElementValue"].get("Weather", "")
                elif "parameter" in wx_elem:
                    weather_desc = wx_elem["parameter"].get("parameterName", "")
                    
            if data_date and max_val is not None and min_val is not None:
                records.append({
                    "regionName": region_name,
                    "dataDate": data_date,
                    "minT": float(min_val),
                    "maxT": float(max_val),
                    "weather": str(weather_desc)
                })
                
    return records

def parse_cities_weather_json(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse F-D0047-091 JSON dataset for all 22 cities/counties across 7 days.
    Aggregates day and night forecasts to derive the daily MinT, MaxT, and weather.
    """
    records: List[Dict[str, Any]] = []
    dataset = raw_data.get("cwaopendata", {}).get("Dataset", {})
    locations_wrapper = dataset.get("Locations", {})
    locations = locations_wrapper.get("Location", [])
    
    for loc in locations:
        city_name = loc.get("LocationName") or loc.get("locationName")
        if not city_name or city_name not in TARGET_CITIES:
            continue
            
        weather_elements = loc.get("WeatherElement") or loc.get("weatherElement", [])
        elem_map = {}
        for elem in weather_elements:
            elem_name = elem.get("ElementName") or elem.get("elementName")
            elem_map[elem_name] = elem.get("Time") or elem.get("time", [])
            
        max_times = elem_map.get("最高溫度") or elem_map.get("MaxT", [])
        min_times = elem_map.get("最低溫度") or elem_map.get("MinT", [])
        wx_times = elem_map.get("天氣現象") or elem_map.get("Wx", [])
        
        by_date = defaultdict(lambda: {"maxT": -999.0, "minT": 999.0, "wx": []})
        
        for i in range(len(max_times)):
            t_elem = max_times[i]
            st_iso = t_elem.get("StartTime") or t_elem.get("startTime", "")
            data_date = st_iso[:10] if len(st_iso) >= 10 else ""
            if not data_date:
                continue
                
            max_val = None
            if "ElementValue" in t_elem:
                max_val = t_elem["ElementValue"].get("MaxTemperature")
            elif "parameter" in t_elem:
                max_val = t_elem["parameter"].get("parameterName")
                
            min_val = None
            if i < len(min_times):
                m_elem = min_times[i]
                if "ElementValue" in m_elem:
                    min_val = m_elem["ElementValue"].get("MinTemperature")
                elif "parameter" in m_elem:
                    min_val = m_elem["parameter"].get("parameterName")
                    
            wx_val = ""
            if i < len(wx_times):
                w_elem = wx_times[i]
                if "ElementValue" in w_elem:
                    wx_val = w_elem["ElementValue"].get("Weather", "")
                elif "parameter" in w_elem:
                    wx_val = w_elem["parameter"].get("parameterName", "")
                    
            if max_val is not None:
                try:
                    f_max = float(max_val)
                    if f_max > by_date[data_date]["maxT"]:
                        by_date[data_date]["maxT"] = f_max
                except ValueError:
                    pass
            if min_val is not None:
                try:
                    f_min = float(min_val)
                    if f_min < by_date[data_date]["minT"]:
                        by_date[data_date]["minT"] = f_min
                except ValueError:
                    pass
            if wx_val and wx_val not in by_date[data_date]["wx"]:
                by_date[data_date]["wx"].append(wx_val)
                
        for dt, v in sorted(by_date.items()):
            if v["maxT"] > -900 and v["minT"] < 900:
                wx_str = "、".join(v["wx"][:2]) if v["wx"] else "晴時多雲"
                records.append({
                    "regionName": city_name,
                    "dataDate": dt,
                    "minT": float(v["minT"]),
                    "maxT": float(v["maxT"]),
                    "weather": wx_str
                })
                
    return records

def fetch_and_sync_weather(api_key: str = DEFAULT_API_KEY) -> pd.DataFrame:
    """
    Step 7 & 8: High-level function to fetch, parse, organize in Pandas,
    and save both 22 Cities and 9 Regions directly into SQLite database data.db.
    Returns the consolidated Pandas DataFrame.
    """
    all_records: List[Dict[str, Any]] = []
    
    # 1. Fetch 22 Cities (F-D0047-091)
    try:
        raw_cities_json = fetch_cwa_raw_json(url=API_URL_CITIES, api_key=api_key)
        cities_records = parse_cities_weather_json(raw_cities_json)
        all_records.extend(cities_records)
    except Exception as e:
        print(f"Warning: Failed to fetch 22 cities dataset: {e}")
        
    # 2. Fetch 9 Regional Divisions (F-C0032-003)
    try:
        raw_regions_json = fetch_cwa_raw_json(url=API_URL_REGIONS, api_key=api_key)
        regions_records = parse_weather_json(raw_regions_json)
        all_records.extend(regions_records)
    except Exception as e:
        print(f"Warning: Failed to fetch regions dataset: {e}")
        
    df = pd.DataFrame(all_records)
    if not df.empty:
        save_forecasts(all_records)
        
    return df

if __name__ == "__main__":
    print("Testing CWA Weather API Fetcher (22 Cities + 9 Regions)...")
    try:
        df_result = fetch_and_sync_weather()
        print(f"Successfully fetched and synced {len(df_result)} records!")
        print("Unique locations stored:", df_result["regionName"].unique())
        print(df_result.head(10))
    except Exception as exc:
        print(f"Error fetching weather data: {exc}")
