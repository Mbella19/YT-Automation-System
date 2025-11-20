import requests
from datetime import datetime

class WeatherService:
    """Service to get weather information"""
    
    def __init__(self):
        # Using Open-Meteo (free, no API key required)
        self.geocoding_url = "https://geocoding-api.open-meteo.com/v1/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"
    
    def get_weather(self, location):
        """
        Get current weather for a location
        
        Args:
            location: Location string (e.g., "New York, NY")
            
        Returns:
            dict with temperature, conditions, etc.
        """
        try:
            # Get coordinates from location name
            geocode_response = requests.get(
                self.geocoding_url,
                params={'name': location, 'count': 1, 'language': 'en', 'format': 'json'}
            )
            
            if geocode_response.status_code != 200:
                raise Exception("Failed to geocode location")
            
            geocode_data = geocode_response.json()
            
            if not geocode_data.get('results'):
                raise Exception(f"Location '{location}' not found")
            
            result = geocode_data['results'][0]
            latitude = result['latitude']
            longitude = result['longitude']
            location_name = result['name']
            
            # Get weather
            weather_response = requests.get(
                self.weather_url,
                params={
                    'latitude': latitude,
                    'longitude': longitude,
                    'current': 'temperature_2m,weather_code,wind_speed_10m',
                    'temperature_unit': 'fahrenheit'
                }
            )
            
            if weather_response.status_code != 200:
                raise Exception("Failed to get weather data")
            
            weather_data = weather_response.json()
            current = weather_data['current']
            
            # Weather code mapping
            weather_codes = {
                0: "Clear sky",
                1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Foggy", 48: "Depositing rime fog",
                51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
                61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
                80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
                95: "Thunderstorm"
            }
            
            weather_desc = weather_codes.get(current['weather_code'], "Unknown")
            
            return {
                'location': location_name,
                'temperature': round(current['temperature_2m']),
                'temperature_unit': 'F',
                'conditions': weather_desc,
                'wind_speed': round(current['wind_speed_10m']),
                'timestamp': current['time']
            }
            
        except Exception as e:
            print(f"Weather service error: {e}")
            # Return default if weather fails
            return {
                'location': location,
                'temperature': 70,
                'temperature_unit': 'F',
                'conditions': 'Mild',
                'wind_speed': 5,
                'error': str(e)
            }

