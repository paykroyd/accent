from astral import AstralError
from cachetools import cached
from cachetools import TTLCache
from json.decoder import JSONDecodeError
from logging import info, warning
from requests import post
from requests import RequestException

from config import get_api_key
from database import DataError

# Google Weather API endpoint
# Docs: https://developers.google.com/maps/documentation/weather/current-conditions
GOOGLE_WEATHER_URL = 'https://weather.googleapis.com/v1/currentConditions:lookup'

# The maximum number of weather conditions kept in the cache.
MAX_CACHE_SIZE = 100

# The time to live in seconds for cached weather conditions.
CACHE_TTL_S = 60 * 60  # 1 hour

# Google Weather API condition codes mapped to weather types
# See: https://developers.google.com/maps/documentation/weather/conditions
CLEAR_CONDITIONS = {'CLEAR', 'MOSTLY_CLEAR'}
PARTLY_CLOUDY_CONDITIONS = {'PARTLY_CLOUDY'}
CLOUDY_CONDITIONS = {'MOSTLY_CLOUDY', 'CLOUDY', 'OVERCAST'}
RAINY_CONDITIONS = {'DRIZZLE', 'RAIN', 'LIGHT_RAIN', 'MODERATE_RAIN',
                    'HEAVY_RAIN', 'SHOWERS', 'THUNDERSTORM', 'THUNDERSTORMS'}
SNOWY_CONDITIONS = {'SNOW', 'LIGHT_SNOW', 'MODERATE_SNOW', 'HEAVY_SNOW',
                    'FLURRIES', 'SLEET', 'ICE_PELLETS', 'FREEZING_RAIN',
                    'FREEZING_DRIZZLE', 'WINTRY_MIX'}
FOGGY_CONDITIONS = {'FOG', 'HAZE', 'MIST', 'SMOKE', 'DUST', 'SAND'}


class Weather(object):
    """A wrapper around the Google Weather API with a cache."""

    def __init__(self, geocoder):
        self._api_key = get_api_key('google_maps')
        self._geocoder = geocoder

    def _condition(self, user):
        """Gets the current weather condition for the user's home address."""
        location = self._home_location(user)
        return self._request_condition(location)

    def _home_location(self, user):
        """Gets the location of the user's home address."""
        try:
            home = user.get('home')
            return self._geocoder[home]
        except (AstralError, KeyError) as e:
            raise DataError(e)

    @cached(cache=TTLCache(maxsize=MAX_CACHE_SIZE, ttl=CACHE_TTL_S))
    def _request_condition(self, location):
        """Requests the current weather condition from the Google Weather API."""
        try:
            response = post(
                f'{GOOGLE_WEATHER_URL}?key={self._api_key}',
                json={
                    'location': {
                        'latitude': location.latitude,
                        'longitude': location.longitude
                    }
                },
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            data = response.json()

            # Extract the weather condition type
            condition = data.get('currentConditions', {}).get('weatherCondition', {}).get('type', 'UNKNOWN')
            info('Weather condition: %s' % condition)
            return condition

        except (RequestException, JSONDecodeError, KeyError) as e:
            warning('Weather API error: %s' % e)
            raise DataError(e)

    def is_clear(self, user):
        """Checks if the current weather is clear."""
        return self._condition(user) in CLEAR_CONDITIONS

    def is_partly_cloudy(self, user):
        """Checks if the current weather is partly cloudy."""
        return self._condition(user) in PARTLY_CLOUDY_CONDITIONS

    def is_cloudy(self, user):
        """Checks if the current weather is cloudy."""
        return self._condition(user) in CLOUDY_CONDITIONS

    def is_rainy(self, user):
        """Checks if the current weather is rainy."""
        return self._condition(user) in RAINY_CONDITIONS

    def is_snowy(self, user):
        """Checks if the current weather is snowy."""
        return self._condition(user) in SNOWY_CONDITIONS

    def is_foggy(self, user):
        """Checks if the current weather is foggy."""
        return self._condition(user) in FOGGY_CONDITIONS
