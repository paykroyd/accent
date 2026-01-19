from datetime import datetime, timedelta
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

# Football-data.org API endpoint
FOOTBALL_API_URL = 'https://api.football-data.org/v4'

# Colors
BACKGROUND_COLOR = (255, 255, 255)
TEXT_COLOR = (0, 0, 0)
ARSENAL_RED = (239, 1, 7)
HIGHLIGHT_COLOR = (255, 0, 0)

# Layout constants
TITLE_Y = 50
COMPETITION_Y = 100
TEAMS_Y = 160
SCORE_Y = 220
TIME_Y = 280
STATUS_Y = 340


class Arsenal(ImageContent):
    """Arsenal FC match display - next match, live score, or recent result."""

    def __init__(self):
        self._api_key = get_api_key('football')
        self._config = get_content_config('arsenal')

    def _make_request(self, endpoint):
        """Make a request to the football-data.org API."""
        url = f'{FOOTBALL_API_URL}{endpoint}'
        headers = {
            'X-Auth-Token': self._api_key
        }

        try:
            response = get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except (RequestException, JSONDecodeError) as e:
            raise DataError(f'Football API error: {e}')

    def _get_matches(self, team_id):
        """Get upcoming and recent matches for a team."""
        try:
            data = self._make_request(f'/teams/{team_id}/matches/')
            return data.get('matches', [])
        except DataError as e:
            warning(f'Failed to get matches: {e}')
            return []

    def _find_relevant_match(self, matches):
        """Find the most relevant match to display.
        Priority: Live match > upcoming match > recent result
        """
        now = datetime.now()
        live_match = None
        upcoming_match = None
        recent_match = None

        for match in matches:
            status = match.get('status', '')
            utc_date = match.get('utcDate', '')

            if utc_date:
                match_time = parse(utc_date).replace(tzinfo=None)

                # Live match (IN_PLAY, PAUSED, HALFTIME)
                if status in ['IN_PLAY', 'PAUSED', 'HALFTIME', 'LIVE']:
                    live_match = match
                    break  # Live match has highest priority

                # Upcoming match (within next 7 days)
                elif status in ['SCHEDULED', 'TIMED'] and match_time > now:
                    if not upcoming_match:
                        upcoming_match = match

                # Recent result (within last 3 days)
                elif status == 'FINISHED' and match_time > (now - timedelta(days=3)):
                    if not recent_match or match_time > parse(recent_match.get('utcDate', '')).replace(tzinfo=None):
                        recent_match = match

        return live_match or upcoming_match or recent_match

    def _format_match_time(self, utc_date_str, user):
        """Format match time for display."""
        try:
            match_time = parse(utc_date_str).replace(tzinfo=None)
            # Format: "Sat Jan 20 3:00 PM"
            return match_time.strftime('%a %b %d %-I:%M %p')
        except Exception:
            return ''

    def _get_competition_name(self, competition):
        """Get shortened competition name."""
        name = competition.get('name', '')
        code = competition.get('code', '')
        short_names = {
            'PL': 'Premier League',
            'CL': 'Champions League',
            'EL': 'Europa League',
            'FAC': 'FA Cup',
            'EFL': 'League Cup',
            'CS': 'Community Shield',
        }
        return short_names.get(code, name[:20])

    def image(self, user, width, height, variant):
        """Generate the Arsenal match image."""
        team_id = self._config.get('team_id', 57)  # 57 is Arsenal

        # Get matches
        matches = self._get_matches(team_id)
        match = self._find_relevant_match(matches)

        # Create image
        image = Image.new(mode='RGB', size=(width, height), color=BACKGROUND_COLOR)
        draw = Draw(image)

        # Draw title
        draw_text('Arsenal FC', SUBVARIO_CONDENSED_MEDIUM, ARSENAL_RED,
                  xy=(width // 2, TITLE_Y), image=image, draw=draw)

        if not match:
            draw_text('No upcoming matches', SUBVARIO_CONDENSED_MEDIUM, TEXT_COLOR,
                      xy=(width // 2, height // 2), image=image, draw=draw)
        else:
            status = match.get('status', '')
            home_team = match.get('homeTeam', {}).get('shortName', 'Home')
            away_team = match.get('awayTeam', {}).get('shortName', 'Away')
            competition = match.get('competition', {})
            score = match.get('score', {})
            utc_date = match.get('utcDate', '')

            # Draw competition name
            comp_name = self._get_competition_name(competition)
            draw_text(comp_name, SUBVARIO_CONDENSED_MEDIUM, TEXT_COLOR,
                      xy=(width // 2, COMPETITION_Y), image=image, draw=draw)

            # Draw teams
            teams_text = f'{home_team} vs {away_team}'
            draw_text(teams_text, SUBVARIO_CONDENSED_MEDIUM, TEXT_COLOR,
                      xy=(width // 2, TEAMS_Y), image=image, draw=draw)

            # Draw score or kickoff time
            if status == 'FINISHED':
                home_score = score.get('fullTime', {}).get('home', 0)
                away_score = score.get('fullTime', {}).get('away', 0)
                score_text = f'{home_score} - {away_score}'
                draw_text(score_text, SUBVARIO_CONDENSED_MEDIUM, TEXT_COLOR,
                          xy=(width // 2, SCORE_Y), image=image, draw=draw)
                draw_text('Full Time', SUBVARIO_CONDENSED_MEDIUM, TEXT_COLOR,
                          xy=(width // 2, STATUS_Y), image=image, draw=draw)

            elif status in ['IN_PLAY', 'PAUSED', 'HALFTIME', 'LIVE']:
                home_score = score.get('fullTime', {}).get('home') or score.get('halfTime', {}).get('home', 0)
                away_score = score.get('fullTime', {}).get('away') or score.get('halfTime', {}).get('away', 0)
                score_text = f'{home_score} - {away_score}'
                draw_text(score_text, SUBVARIO_CONDENSED_MEDIUM, HIGHLIGHT_COLOR,
                          xy=(width // 2, SCORE_Y), image=image, draw=draw)

                status_text = 'LIVE' if status == 'IN_PLAY' else status.replace('_', ' ')
                draw_text(status_text, SUBVARIO_CONDENSED_MEDIUM, HIGHLIGHT_COLOR,
                          xy=(width // 2, STATUS_Y), image=image, draw=draw)

            else:
                # Upcoming match - show kickoff time
                kickoff = self._format_match_time(utc_date, user)
                draw_text(kickoff, SUBVARIO_CONDENSED_MEDIUM, TEXT_COLOR,
                          xy=(width // 2, SCORE_Y), image=image, draw=draw)
                draw_text('Kickoff', SUBVARIO_CONDENSED_MEDIUM, TEXT_COLOR,
                          xy=(width // 2, STATUS_Y), image=image, draw=draw)

        # Convert to palette mode
        image = image.convert('P', dither=None, palette=Image.ADAPTIVE)
        return image
