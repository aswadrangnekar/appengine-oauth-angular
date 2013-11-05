from helpers import Jsonifiable
from google.appengine.ext import db
from oauth2client.appengine import CredentialsProperty

class User(db.Model, Jsonifiable):
    jsonkind = 'portal#user'
    email = db.EmailProperty()
    google_user_id = db.StringProperty()
    google_display_name = db.StringProperty()
    google_public_profile_url = db.StringProperty()
    google_public_profile_photo_url = db.LinkProperty()
    google_credentials = CredentialsProperty()

    def json_properties(self):
        properties = Jsonifiable.json_properties(self)
        properties.remove('google_credentials')
        return properties