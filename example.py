import datetime
from weathercloud import WeathercloudClient

def print_section(title: str):
    print(f"\n{'='*10} {title} {'='*10}")

def main():
    # Initialize the unofficial client
    client = WeathercloudClient()
    
    # Using the active test ID provided in the OpenAPI spec
    DEVICE_ID = "5726468552" 
    
    print(f"Extracting all possible data layers for Device ID: {DEVICE_ID}")
    
    # ---------------------------------------------------------
    # 1. SCRAPE STATION NAME
    # ---------------------------------------------------------
    print_section("STATION IDENTITY")
    try:
        station_name = client.scrape_station_name(DEVICE_ID)
        print(f"Station Name: {station_name}")
    except Exception as e:
        print(f"[-] Could not scrape station name: {e}")

    # ---------------------------------------------------------
    # 2. METADATA & STATUS (GET /device/info/{id})
    # ---------------------------------------------------------
    print_section("STATION METADATA & STATUS")
    try:
        info = client.get_device_info(DEVICE_ID)
        dev_meta = info.get("device", {})
        
        status_map = {"1": "Online", "2": "Recently Online", "3": "Offline"}
        status_code = dev_meta.get("status")
        
        print(f"City:           {dev_meta.get('city')}")
        print(f"Altitude:       {dev_meta.get('altitude')} meters")
        print(f"Status:         {status_map.get(status_code, 'Unknown')} ({status_code})")
        print(f"Last Update:    {dev_meta.get('update')} seconds ago")
        print(f"Account Tier:   {'Premium/Pro' if dev_meta.get('account', 0) > 0 else 'Free'}")
        
        # Pull owner profile data
        profile = client.get_owner_profile(DEVICE_ID)
        obs = profile.get("observer", {})
        dev_hardware = profile.get("device", {})
        print(f"Observer:       {obs.get('name')} aka '{obs.get('nickname')}'")
        print(f"Hardware:       {dev_hardware.get('brand')} - {dev_hardware.get('model')}")
        print(f"Followers:      {profile.get('followers', {}).get('number', '0')}")
        
    except Exception as e:
        print(f"[-] Failed to fetch station metadata layers: {e}")

    # ---------------------------------------------------------
    # 3. LIVE SENSOR READINGS (GET /device/values/{id})
    # ---------------------------------------------------------
    print_section("LIVE SENSOR READINGS")
    try:
        live = client.get_device_values(DEVICE_ID)
        
        if "epoch" in live:
            obs_time = datetime.datetime.fromtimestamp(live["epoch"], tz=datetime.timezone.utc)
            print(f"Observation Time (UTC): {obs_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        print(f"Temperature:      {live.get('temp')} °C  (Feels Like: {live.get('heat')} °C / Chill: {live.get('chill')} °C)")
        print(f"Dew Point:        {live.get('dew')} °C")
        print(f"Humidity:         {live.get('hum')}%")
        print(f"Barometer:        {live.get('bar')} hPa")
        print(f"Wind:             {live.get('wspd')} m/s (Avg: {live.get('wspdavg')} m/s, Gust: {live.get('wspdhi')} m/s)")
        print(f"Wind Direction:   {live.get('wdir')}° (Avg Direction: {live.get('wdiravg')}°)")
        print(f"Rain:             {live.get('rain')} mm (Current Rate: {live.get('rainrate')} mm/h)")
        print(f"Solar Radiation:  {live.get('solarrad')} W/m²")
        print(f"UV Index:         {live.get('uvi')}")
    except Exception as e:
        print(f"[-] Failed to extract live metrics: {e}")

    # ---------------------------------------------------------
    # 4. STATISTICAL HISTOGRAMS / EXTREMES (GET /device/stats)
    # ---------------------------------------------------------
    print_section("PERIOD MIN/MAX STATISTICS")
    try:
        stats = client.get_device_stats(DEVICE_ID)
        
        # Weathercloud returns records as [unix_timestamp, value]
        def format_tuple(stat_tuple):
            if not stat_tuple or len(stat_tuple) < 2:
                return "N/A"
            ts, val = stat_tuple
            time_str = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime('%H:%M UTC')
            return f"{val} [at {time_str}]"

        print(f"Today's Temp Range:  Min: {format_tuple(stats.get('temp_day_min'))} | Max: {format_tuple(stats.get('temp_day_max'))}")
        print(f"Today's Max Wind:    {format_tuple(stats.get('wspd_day_max'))}")
        print(f"Today's Total Rain:  {stats.get('rain_day_total', [0, 'N/A'])[1]} mm")
        print(f"Month Total Rain:    {stats.get('rain_month_total', [0, 'N/A'])[1]} mm")
        print(f"Year Max Temp:       {format_tuple(stats.get('temp_year_max'))}")
    except Exception as e:
        print(f"[-] Failed to parse statistical data points: {e}")

    # ---------------------------------------------------------
    # 5. 6-DAY REGIONAL FORECAST (GET /forecast/daily)
    # ---------------------------------------------------------
    print_section("6-DAY WEATHER FORECAST (WMO)")
    try:
        forecast_data = client.get_daily_forecast(DEVICE_ID)
        print(f"Forecast Location Target: {forecast_data.get('location', {}).get('name')}")
        
        forecast_days = forecast_data.get("forecast", {})
        for date_str, day_info in sorted(forecast_days.items()):
            w_code = day_info.get("weather", {}).get("code", "Unknown")
            temps = day_info.get("temperature", {})
            print(f"  {date_str} -> Max: {temps.get('max')}°C | Min: {temps.get('min')}°C | WMO Code: {w_code}")
    except Exception as e:
        print(f"[-] Forecast data layer empty or unavailable: {e}")

    # ---------------------------------------------------------
    # 6. HISTORICAL TIME-SERIES HOURLY AGGREGATION (POST /device/evolution)
    # ---------------------------------------------------------
    print_section("HOURLY HISTORY EVOLUTION (LAST 24 HOURS)")
    try:
        # Code 101 pulls the core temperature time-series history
        evolution = client.get_historical_evolution(DEVICE_ID, variable_code=101, period="day")
        data_block = evolution.get("data", {})
        print(f"Timezone: {data_block.get('timezone')}")
        
        # Display summary calculations generated by the server
        summary = data_block.get("summary", {}).get("101", {})
        print(f"Server Aggregation Summary -> Samples: {summary.get('samples')} | Min: {summary.get('min')}°C | Max: {summary.get('max')}°C")
        
        # Display the actual hourly time-series entries
        hourly_values = data_block.get("values", {})
        print("  Sample Trend History:")
        
        # Sort by timestamp keys and show up to the first 5 records
        sorted_hours = sorted(hourly_values.keys())
        for ts_str in sorted_hours[:5]:
            hour_time = datetime.datetime.fromtimestamp(int(ts_str), tz=datetime.timezone.utc)
            # Drill into variable entry 101 -> stats block
            stats_101 = hourly_values[ts_str].get("101", {}).get("stats", {})
            print(f"    {hour_time.strftime('%H:%M')} UTC -> Avg: {stats_101.get('sum')}°C | Range: {stats_101.get('min')}°C to {stats_101.get('max')}°C")
            
        if len(sorted_hours) > 5:
            print(f"    ... [{len(sorted_hours) - 5} more hourly data points parsed]")
            
    except Exception as e:
        print(f"[-] Could not unpack time-series arrays: {e}")

    # ---------------------------------------------------------
    # 7. REGIONAL DISCOVERY / RADIUS SCANNING (GET /page/coordinates/...)
    # ---------------------------------------------------------
    print_section("DISCOVERING NEARBY STATIONS")
    try:
        # Scan near coordinate zone (example coordinates near Ingelmunster, Belgium)
        scan_results = client.get_nearby_stations(lat=50.9475, lon=3.1205, distance_km=10)
        devices_found = scan_results.get("devices", [])
        
        print(f"Found {len(devices_found)} stations within a 10km radius:")
        for neighbor in devices_found[:3]:
            # WARNING: Values inside the coordinate/page sub-components are 
            # returned as strings containing integers multiplied by 10.
            raw_temp = neighbor.get("values", {}).get("temp")
            scaled_temp = float(raw_temp) / 10.0 if raw_temp else "N/A"
            
            print(f"  - [{neighbor.get('code')}] {neighbor.get('name')} ({neighbor.get('city')})")
            print(f"    Distance: {neighbor.get('data')} km away | Temperature: {scaled_temp} °C")
            
        if len(devices_found) > 3:
            print(f"  ... and {len(devices_found) - 3} other nearby stations.")
            
    except Exception as e:
        print(f"[-] Geographic discovery function returned an error: {e}")

if __name__ == "__main__":
    main()