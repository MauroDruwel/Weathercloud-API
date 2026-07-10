import os
import sys

# Add local src directory to path so example can be run without pip installation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from weathercloud import WeathercloudClient, WeathercloudError

# Configure your details here (Set USERNAME and PASSWORD to get inside sensors)
STATION_ID = "5726468552"  # Replace with your numeric station ID
USERNAME = None
PASSWORD = None

def main():
    print(f"Connecting to Weathercloud for station {STATION_ID}...")

    # Initialize the client inside a context manager to handle session teardown automatically
    with WeathercloudClient(username=USERNAME, password=PASSWORD) as client:
        try:
            # 1. Fetch station details
            info = client.get_station_info(STATION_ID)
            print("\n=== Station Info ===")
            print(f"Name:     {info.name}")
            print(f"City:     {info.city}")
            print(f"Altitude: {info.altitude} m")

            # 2. Fetch conditions (automatic login is handled internally on first fetch)
            conditions = client.get_current_conditions(STATION_ID)
            print("\n=== Current Conditions ===")
            print(f"Outdoor Temp:   {conditions.temperature} °C")
            print(f"Wind Speed:     {conditions.wind_speed} m/s")
            print(f"Barometer:      {conditions.pressure} hPa")

            # 3. Fetch private indoor sensors (only populated if login was successful)
            print("\n=== Indoor Sensors ===")
            print(f"Indoor Temp:    {conditions.inside_temperature} °C")
            print(f"Indoor Humid:   {conditions.inside_humidity} %")
            print(f"Indoor HeatIdx: {conditions.inside_heat_index} °C")

        except WeathercloudError as err:
            print(f"\n[Error] Weathercloud API error: {err}", file=sys.stderr)

if __name__ == "__main__":
    main()
