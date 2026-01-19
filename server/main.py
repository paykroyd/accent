from functools import wraps
from flask import Flask
from flask import redirect
from flask import request
from flask import url_for
from googleapiclient.http import build_http
from logging import error, exception
from oauth2client.client import HttpAccessTokenRefreshError
from oauth2client.client import OAuth2WebServerFlow
from time import time

from arsenal import Arsenal
from artwork import Artwork
from city import City
from config import get_user, get_google_calendar_secrets, load_config
from content import ContentError
from database import GoogleCalendarStorage
from epd import DEFAULT_DISPLAY_VARIANT
from geocoder import Geocoder
from google_calendar import GoogleCalendar
from mbta import MBTA
from response import content_response
from response import display_metadata
from response import epd_response
from response import gif_response
from response import text_response
from schedule import Schedule

# Load configuration on startup
load_config()

# The scope to request for the Google Calendar API.
GOOGLE_CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.readonly'

# The time in milliseconds to return in an unauthorized next request.
NEXT_RETRY_DELAY_MILLIS = 5 * 60 * 1000  # 5 minutes

# A geocoder instance with a shared cache.
geocoder = Geocoder()

# Helper library instances.
artwork = Artwork()
arsenal = Arsenal()
calendar = GoogleCalendar(geocoder)
city = City(geocoder)
mbta = MBTA()
schedule = Schedule(geocoder)

# The Flask app handling requests.
app = Flask(__name__)


def get_current_user():
    """Get the current user from config."""
    return get_user()


def user_auth(image_response=None, bad_response=None):
    """Simplified user_auth decorator for single-user setup."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            kwargs['key'] = 'default'
            kwargs['user'] = user
            return func(*args, **kwargs)
        return wrapper
    return decorator


def next_retry_response():
    """Creates a response for a next request with a fixed retry time."""
    return text_response(str(NEXT_RETRY_DELAY_MILLIS))


@app.route('/artwork')
@user_auth(image_response=gif_response)
def artwork_gif(key=None, user=None):
    """Responds with a GIF version of the artwork image."""
    width, height, variant = display_metadata(request)
    return content_response(artwork, gif_response, user, width, height, variant)


@app.route('/city')
@user_auth(image_response=gif_response)
def city_gif(key=None, user=None):
    """Responds with a GIF version of the city image."""
    width, height, variant = display_metadata(request)
    return content_response(city, gif_response, user, width, height, variant)


@app.route('/calendar')
@user_auth(image_response=gif_response)
def calendar_gif(key=None, user=None):
    """Responds with a GIF version of the calendar image."""
    width, height, variant = display_metadata(request)
    return content_response(calendar, gif_response, user, width, height, variant)


@app.route('/mbta')
@user_auth(image_response=gif_response)
def mbta_gif(key=None, user=None):
    """Responds with a GIF version of the MBTA image."""
    width, height, variant = display_metadata(request)
    return content_response(mbta, gif_response, user, width, height, variant)


@app.route('/arsenal')
@user_auth(image_response=gif_response)
def arsenal_gif(key=None, user=None):
    """Responds with a GIF version of the Arsenal image."""
    width, height, variant = display_metadata(request)
    return content_response(arsenal, gif_response, user, width, height, variant)


@app.route('/gif')
@user_auth(image_response=gif_response)
def gif(key=None, user=None):
    """Responds with a GIF version of the scheduled image."""
    width, height, variant = display_metadata(request)
    return content_response(schedule, gif_response, user, width, height, variant)


@app.route('/epd')
@user_auth(image_response=epd_response)
def epd(key=None, user=None):
    """Responds with an e-paper display version of the scheduled image."""
    width, height, variant = display_metadata(request)
    return content_response(schedule, epd_response, user, width, height, variant)


@app.route('/next')
@user_auth(bad_response=next_retry_response)
def next(key=None, user=None):
    """Responds with the milliseconds until the next image."""
    try:
        milliseconds = schedule.delay(user)
        return text_response(str(milliseconds))
    except ContentError as e:
        exception('Failed to create next content: %s' % e)
        return next_retry_response()


@app.route('/')
def index():
    """Simple status page."""
    return 'Accent Server Running'


def _empty_timeline_response():
    """Responds with an empty schedule timeline image."""
    image = schedule.empty_timeline()
    return gif_response(image, 'bwr')


@app.route('/timeline')
@user_auth()
def timeline(key=None, user=None):
    """Responds with a schedule timeline image."""
    image = schedule.timeline(user)
    return gif_response(image, 'bwr')


# Google Calendar OAuth routes
def _oauth_url():
    """Creates the URL handling OAuth redirects."""
    return url_for('oauth', _external=True)


def _google_calendar_flow():
    """Creates the OAuth flow."""
    secrets = get_google_calendar_secrets()
    return OAuth2WebServerFlow(
        client_id=secrets.get('client_id', ''),
        client_secret=secrets.get('client_secret', ''),
        scope=GOOGLE_CALENDAR_SCOPE,
        redirect_uri=_oauth_url()
    )


@app.route('/calendar/connect')
def calendar_connect():
    """Starts the Google Calendar OAuth flow."""
    flow = _google_calendar_flow()
    return redirect(flow.step1_get_authorize_url())


@app.route('/oauth')
def oauth():
    """Handles OAuth flow redirects."""
    # Handle any errors
    oauth_error = request.args.get('error')
    if oauth_error:
        error('OAuth error: %s' % oauth_error)
        return 'OAuth error: %s' % oauth_error, 400

    # Complete the flow
    code = request.args.get('code')
    if code:
        flow = _google_calendar_flow()
        credentials = flow.step2_exchange(code=code)
        storage = GoogleCalendarStorage('default')
        credentials.set_store(storage)
        try:
            credentials.refresh(build_http())
            return 'Google Calendar connected successfully!'
        except HttpAccessTokenRefreshError as e:
            storage.delete()
            error('Token refresh error: %s' % e)
            return 'Token refresh error', 500

    return 'Missing OAuth code', 400


@app.route('/calendar/status')
def calendar_status():
    """Check Google Calendar connection status."""
    storage = GoogleCalendarStorage('default')
    credentials = storage.get()
    if credentials and not credentials.invalid:
        return 'Google Calendar: Connected'
    return 'Google Calendar: Not connected. Visit /calendar/connect to connect.'


@app.errorhandler(500)
def server_error(e):
    """Logs the stack trace for server errors."""
    timestamp = int(time())
    message = 'Internal Server Error @ %d' % timestamp
    exception(message)
    return message, 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
