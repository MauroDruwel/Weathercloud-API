"""
Weathercloud library usage example.
Demonstrates both the high-level typed API and raw dict access.
"""
import datetime

from weathercloud import VariableCode, WeathercloudClient, WeathercloudError

DEVICE_ID = "5726468552"


def main() -> None:
    client = WeathercloudClient()

    # ------------------------------------------------------------------
    # 1. Station info (metadata + scraped name)
    # ------------------------------------------------------------------
    print("=== Station Info ===")
    try:
        info = client.get_station_info(DEVICE_ID)
        print(f"Name:    {info.name}")
        print(f"City:    {info.city}  ({info.altitude} m)")
        print(f"Status:  {info.status}  ({info.seconds_since_update}s ago)")
        print(f"Tier:    {'premium' if info.account_type > 0 else 'free'}")
    except WeathercloudError as exc:
        print(f"Error: {exc}")

    # ------------------------------------------------------------------
    # 2. Live sensor readings (typed dataclass)
    # ------------------------------------------------------------------
    print("\n=== Current Conditions ===")
    try:
        cond = client.get_current_conditions(DEVICE_ID)
        ts = datetime.datetime.fromtimestamp(cond.epoch, tz=datetime.timezone.utc)
        print(f"Time:        {ts:%Y-%m-%d %H:%M} UTC")
        print(f"Temperature: {cond.temperature} °C  (feels like {cond.heat_index} °C)")
        print(f"Humidity:    {cond.humidity} %")
        print(f"Pressure:    {cond.pressure} hPa")
        print(
            f"Wind:        {cond.wind_speed_avg} m/s avg, "
            f"{cond.wind_gust} m/s gust @ {cond.wind_direction_avg}°"
        )
        print(f"Rain:        {cond.rain} mm  ({cond.rain_rate} mm/h)")
        print(f"UV index:    {cond.uv_index}")
        print(f"Solar rad:   {cond.solar_radiation} W/m²")
    except WeathercloudError as exc:
        print(f"Error: {exc}")

    # ------------------------------------------------------------------
    # 3. Period stats (raw dict — too many keys for a dataclass)
    # ------------------------------------------------------------------
    print("\n=== Today's Extremes ===")
    try:
        stats = client.get_device_stats(DEVICE_ID)

        def fmt(entry: list) -> str:
            if not entry or len(entry) < 2:
                return "N/A"
            ts = datetime.datetime.fromtimestamp(entry[0], tz=datetime.timezone.utc)
            return f"{entry[1]}  (at {ts:%H:%M} UTC)"

        print(f"Temp min/max:  {fmt(stats.get('temp_day_min'))} / {fmt(stats.get('temp_day_max'))}")
        print(f"Wind max:      {fmt(stats.get('wspd_day_max'))}")
        print(f"Rain today:    {stats.get('rain_day_total', [0, 'N/A'])[1]} mm")
    except WeathercloudError as exc:
        print(f"Error: {exc}")

    # ------------------------------------------------------------------
    # 4. 6-day forecast
    # ------------------------------------------------------------------
    print("\n=== 6-Day Forecast ===")
    try:
        forecast = client.get_forecast(DEVICE_ID)
        location = forecast.get("location", {}).get("name", "?")
        print(f"Location: {location}")
        for date, day in sorted(forecast.get("forecast", {}).items()):
            t = day.get("temperature", {})
            code = day.get("weather", {}).get("code", "?")
            print(f"  {date}  max {t.get('max')}°C  min {t.get('min')}°C  (WMO {code})")
    except WeathercloudError as exc:
        print(f"Error: {exc}")

    # ------------------------------------------------------------------
    # 5. Temperature history — last 24 h
    # ------------------------------------------------------------------
    print("\n=== Temperature History (last 24h) ===")
    try:
        evo = client.get_evolution(DEVICE_ID, VariableCode.TEMPERATURE, period="day")
        summary = evo.get("data", {}).get("summary", {}).get("101", {})
        print(
            f"Min: {summary.get('min')} °C   Max: {summary.get('max')} °C   "
            f"Samples: {summary.get('samples')}"
        )
    except WeathercloudError as exc:
        print(f"Error: {exc}")

    # ------------------------------------------------------------------
    # 6. Nearby stations
    # ------------------------------------------------------------------
    print("\n=== Nearby Stations (10 km) ===")
    try:
        nearby = client.get_nearby_stations(lat=50.9475, lon=3.1205, distance_km=10)
        for dev in nearby.get("devices", [])[:5]:
            raw_temp = dev.get("values", {}).get("temp")
            temp = f"{float(raw_temp) / 10:.1f} °C" if raw_temp else "N/A"
            print(f"  [{dev.get('code')}] {dev.get('name')} — {dev.get('data')} km  {temp}")
    except WeathercloudError as exc:
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
