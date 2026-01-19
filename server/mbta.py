from datetime import datetime
from dateutil.parser import parse
from json.decoder import JSONDecodeError
from logging import info, warning
from PIL import Image
from PIL.ImageDraw import Draw
from requests import get
from requests import RequestException

from config import get_api_key, get_content_config
from content import ContentError
from content import ImageContent
from database import DataError
from graphics import draw_text
from graphics import SUBVARIO_CONDENSED_MEDIUM

# MBTA API v3 endpoint
MBTA_API_URL = 'https://api-v3.mbta.com'

# Colors
BACKGROUND_COLOR = (255, 255, 255)
TEXT_COLOR = (0, 0, 0)
ALERT_COLOR = (255, 0, 0)
RED_LINE_COLOR = (218, 41, 28)

# Layout constants
TITLE_Y = 60
STATUS_Y = 120
PREDICTION_START_Y = 180
PREDICTION_SPACING = 50


class MBTA(ImageContent):
    """MBTA Red Line status and predictions display."""

    def __init__(self):
        self._api_key = get_api_key('mbta')
        self._config = get_content_config('mbta')

    def _make_request(self, endpoint, params=None):
        """Make a request to the MBTA API."""
        url = f'{MBTA_API_URL}{endpoint}'
        headers = {}
        if self._api_key:
            headers['x-api-key'] = self._api_key

        try:
            response = get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except (RequestException, JSONDecodeError) as e:
            raise DataError(f'MBTA API error: {e}')

    def _get_alerts(self, route_id):
        """Get active alerts for a route."""
        try:
            data = self._make_request('/alerts', {
                'filter[route]': route_id,
                'filter[activity]': 'BOARD,EXIT,RIDE'
            })
            alerts = data.get('data', [])
            # Filter to current alerts
            active_alerts = []
            now = datetime.now()
            for alert in alerts:
                attrs = alert.get('attributes', {})
                # Check if alert is currently active
                active_periods = attrs.get('active_period', [])
                for period in active_periods:
                    start = period.get('start')
                    end = period.get('end')
                    if start:
                        start_dt = parse(start).replace(tzinfo=None)
                        if start_dt > now:
                            continue
                    if end:
                        end_dt = parse(end).replace(tzinfo=None)
                        if end_dt < now:
                            continue
                    active_alerts.append(attrs.get('header', 'Alert'))
                    break
            return active_alerts
        except DataError as e:
            warning(f'Failed to get alerts: {e}')
            return []

    def _get_predictions(self, route_id, stop_id):
        """Get upcoming arrival predictions for a stop."""
        try:
            data = self._make_request('/predictions', {
                'filter[route]': route_id,
                'filter[stop]': stop_id,
                'sort': 'arrival_time',
                'page[limit]': 6
            })
            predictions = []
            now = datetime.now()
            for pred in data.get('data', []):
                attrs = pred.get('attributes', {})
                arrival_time = attrs.get('arrival_time') or attrs.get('departure_time')
                if arrival_time:
                    arrival_dt = parse(arrival_time).replace(tzinfo=None)
                    minutes = int((arrival_dt - now).total_seconds() / 60)
                    if minutes >= 0:
                        direction = attrs.get('direction_id', 0)
                        direction_name = 'Alewife' if direction == 1 else 'Ashmont/Braintree'
                        predictions.append({
                            'minutes': minutes,
                            'direction': direction_name
                        })
            return predictions[:4]  # Return top 4 predictions
        except DataError as e:
            warning(f'Failed to get predictions: {e}')
            return []

    def _get_route_name(self, route_id):
        """Get the display name for a route."""
        route_names = {
            'Red': 'Red Line',
            'Orange': 'Orange Line',
            'Blue': 'Blue Line',
            'Green-B': 'Green Line B',
            'Green-C': 'Green Line C',
            'Green-D': 'Green Line D',
            'Green-E': 'Green Line E',
        }
        return route_names.get(route_id, route_id)

    def image(self, user, width, height, variant):
        """Generate the MBTA status image."""
        route_id = self._config.get('route_id', 'Red')
        stop_id = self._config.get('stop_id', 'place-harsq')

        # Get data from API
        alerts = self._get_alerts(route_id)
        predictions = self._get_predictions(route_id, stop_id)

        # Create image
        image = Image.new(mode='RGB', size=(width, height), color=BACKGROUND_COLOR)
        draw = Draw(image)

        # Draw title
        route_name = self._get_route_name(route_id)
        draw_text(route_name, SUBVARIO_CONDENSED_MEDIUM, RED_LINE_COLOR,
                  xy=(width // 2, TITLE_Y), image=image, draw=draw)

        # Draw status
        if alerts:
            # Show first alert
            alert_text = alerts[0][:50]  # Truncate if too long
            draw_text(alert_text, SUBVARIO_CONDENSED_MEDIUM, ALERT_COLOR,
                      xy=(width // 2, STATUS_Y), image=image, draw=draw)
        else:
            draw_text('Normal Service', SUBVARIO_CONDENSED_MEDIUM, TEXT_COLOR,
                      xy=(width // 2, STATUS_Y), image=image, draw=draw)

        # Draw predictions
        y = PREDICTION_START_Y
        if predictions:
            for pred in predictions:
                minutes = pred['minutes']
                direction = pred['direction']
                if minutes == 0:
                    time_text = 'Now'
                elif minutes == 1:
                    time_text = '1 min'
                else:
                    time_text = f'{minutes} min'
                text = f'{direction}: {time_text}'
                draw_text(text, SUBVARIO_CONDENSED_MEDIUM, TEXT_COLOR,
                          xy=(width // 2, y), image=image, draw=draw)
                y += PREDICTION_SPACING
        else:
            draw_text('No predictions available', SUBVARIO_CONDENSED_MEDIUM, TEXT_COLOR,
                      xy=(width // 2, y), image=image, draw=draw)

        # Convert to palette mode
        image = image.convert('P', dither=None, palette=Image.ADAPTIVE)
        return image
