import httplib2
import logging
import json
import os
import webapp2
import jinja2
import re

from models.user import User
from utils import JsonRestHandler
from apiclient.discovery import build
from google.appengine.api import urlfetch

import oauth2client
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from webapp2_extras import sessions

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__))
)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

SCOPES = [
    'https://www.googleapis.com/auth/plus.login'
]

VISIBLE_ACTIONS = [
    'http://schemas.google.com/AddActivity',
    'http://schemas.google.com/ReviewActivity'
]

TOKEN_INFO_ENDPOINT = ('https://www.googleapis.com/oauth2/v1/tokeninfo' +
                       '?access_token=%s')
TOKEN_REVOKE_ENDPOINT = 'https://accounts.google.com/o/oauth2/revoke?token=%s'

"""
EXCEPTION CLASSES
"""


class RevokeException(Exception):
    msg = 'Failed to revoke token for user'


class UserNotAuthorizedException(Exception):
    msg = "Unauthorized Request"


class NotFoundException(Exception):
    msg = "Resource not found"


"""
AUTH CLASSES
"""


class SessionEnabledHandler(webapp2.RequestHandler):
    CURRENT_USER_SESSION_KEY = 'me'

    def dispatch(self):
        self.session_store = sessions.get_store(request=self.request)
        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        return self.session_store.get_session()

    def get_user_from_session(self):
        google_user_id = self.session.get(self.CURRENT_USER_SESSION_KEY)
        if google_user_id is None:
            raise UserNotAuthorizedException('Session did not contain user id.')
        user = User.all().filter('google_user_id =', google_user_id).get()
        if not user:
            raise UserNotAuthorizedException('Session user ID not in datastore')
        return user


class ConnectHandler(JsonRestHandler, SessionEnabledHandler):
    @staticmethod
    def exchange_code(code):
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope=' '.join(SCOPES))
        oauth_flow.request_visible_actions = ' '.join(VISIBLE_ACTIONS)
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
        return credentials

    @staticmethod
    def get_token_info(credentials):
        url = (TOKEN_INFO_ENDPOINT % credentials.access_token)
        return urlfetch.fetch(url)

    @staticmethod
    def get_user_profile(credentials):
        http = httplib2.Http()
        plus = build('plus', 'v1', http=http)
        credentials.authorize(http)
        return plus.people().get(userId='me').execute()

    @staticmethod
    def save_token_for_user(google_user_id, credentials):
        user = User.all().filter('google_user_id=', google_user_id).get()
        if user is None:
            profile = ConnectHandler.get_user_profile(credentials)
            user = User()
            user.google_user_id = profile.get('id')
            user.google_display_name = profile.get('displayName')
            user.google_public_profile_url = profile.get('url')
            image = profile.get('image')
            if image is not None:
                user.google_public_profile_photo_url = image.get('url')
        user.google_credentials = credentials
        user.put()
        return user

    @staticmethod
    def create_credentials(connect_credentials):
        refresh_token = ''
        _, client_info = oauth2client.clientsecrets.loadfile(
            'client_secrets.json', None)
        web_flow = flow_from_clientsecrets(
            'client_secrets.json', scope=' '.join(SCOPES))
        web_flow.request_visible_actions = ' '.join(VISIBLE_ACTIONS)
        web_flow.redirect_uri = 'postmessage'
        credentials = oauth2client.client.OAuth2Credentials(
            access_token=connect_credentials.get('access_token'),
            client_id=client_info.get('client_id'),
            client_secret=client_info['client_secret'],
            refresh_token=refresh_token,
            token_expiry=connect_credentials.get('expires_at'),
            token_uri=web_flow.token_uri,
            user_agent=web_flow.user_agent,
            id_token=connect_credentials.get('id_token'))
        return credentials

    def post(self):
        if self.session.get(self.CURRENT_USER_SESSION_KEY) is not None:
            user = self.get_user_from_session()
            self.send_success(user)
            return

        credentials = None
        try:
            connect_credentials = json.loads(self.request.body)
            if 'error' in connect_credentials:
                self.send_error(401, connect_credentials.error)
                return
            if connect_credentials.get('code'):
                credentials = ConnectHandler.exchange_code(connect_credentials.get('code'))
            elif connect_credentials.get('access_token'):
                credentials = ConnectHandler.create_credentials(connect_credentials)
        except FlowExchangeError:
            self.send_error(401, 'Failed to exchange authorization code.')
            return

        token_info = ConnectHandler.get_token_info(credentials)
        if token_info.status_code != 200:
            self.send_error(401, 'Failed to validate access token.')
            return
        token_info = json.loads(token_info.content)
        if token_info.get('error') is not None:
            self.send_error(401, token_info.get('error'))
            return
        expr = re.compile("(\d*)(.*).apps.googleusercontent.com")
        issued_to_match = expr.match(token_info.get('issued_to'))
        local_id_match = expr.match(CLIENT_ID)
        if not issued_to_match or not local_id_match or issued_to_match.group(1) != local_id_match.group(1):
            self.send_error(401, "Token's client ID does not match app ID")
            return

        user = ConnectHandler.save_token_for_user(token_info.get('user_id'), credentials)
        self.session[self.CURRENT_USER_SESSION_KEY] = token_info.get('user_id')
        self.send_success(user)


class DisconnectHandler(JsonRestHandler, SessionEnabledHandler):
    @staticmethod
    def revoke_token(credentials):
        url = TOKEN_REVOKE_ENDPOINT % credentials.access_token
        http = httplib2.Http()
        credentials.authorize(http)
        result = http.request(url, 'GET')[0]

        if result['status'] != '200':
            raise RevokeException

    def post(self):
        try:
            user = self.get_user_from_session()
            credentials = user.google_credentials

            del (self.session[self.CURRENT_USER_SESSION_KEY])
            # TODO: add cleanup code for DB here
            DisconnectHandler.revoke_token(credentials)
            self.send_success('Successfully disconnected')
            return
        except UserNotAuthorizedException as e:
            self.send_error(401, e.msg)
            return
        except RevokeException as e:
            self.send_error(500, e.msg)
            return


routes = [
    ('/auth/connect', ConnectHandler),
    ('/auth/disconnect', DisconnectHandler)
]
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'YOUR_SESSION_SECRET'
}
app = webapp2.WSGIApplication(routes, config=config, debug=True)