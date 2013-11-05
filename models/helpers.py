import json
import re
import datetime
import types

from google.appengine.ext import db

class JsonifiableEncoder(json.JSONEncoder):
  """JSON encoder which provides a convenient extension point for custom JSON
  encoding of Jsonifiable subclasses.
  """
  def default(self, obj):
    if isinstance(obj, Jsonifiable):
      result = json.loads(obj.to_json())
      return result
    return json.JSONEncoder.default(self, obj)

class Jsonifiable:
  """Base class providing convenient JSON serialization and deserialization
  methods.
  """
  jsonkind = 'portal#jsonifiable'

  @staticmethod
  def lower_first(key):
    """Make the first letter of a string lower case."""
    return key[:1].lower() + key[1:] if key else ''

  @staticmethod
  def transform_to_camelcase(key):
    """Transform a string underscore separated words to concatenated camel case.
    """
    return Jsonifiable.lower_first(
        ''.join(c.capitalize() or '_' for c in key.split('_')))

  @staticmethod
  def transform_from_camelcase(key):
    """Tranform a string from concatenated camel case to underscore separated
    words.
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', key)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

  def to_dict(self):
    """Returns a dictionary containing property values for the current object
    stored under the property name in camel case form.
    """
    result = {}
    for p in self.json_properties():
      value = getattr(self, p)
      if isinstance(value, datetime.datetime):
        value = value.strftime('%s%f')[:-3]
      result[Jsonifiable.transform_to_camelcase(p)] = value
    return result

  def to_json(self):
    """Returns a JSON string of the properties of this object."""
    properties = self.to_dict()
    if isinstance(self, db.Model):
      properties['id'] = unicode(self.key().id())
    return json.dumps(properties)

  def json_properties(self):
    """Returns a default list properties for this object that should be
    included when serializing this object to, or deserializing it from, JSON.

    Subclasses can customize the properties by overriding this method.
    """
    attributes = []
    all = vars(self)
    for var in all:
      if var[:1] != '_':
        attributes.append(var)
    if isinstance(self, db.Model):
      properties = self.properties().keys()
      for property in properties:
        if property[:1] != '_':
          attributes.append(property)
    return attributes

  def from_json(self, json_string):
    """Sets properties on this object based on the JSON string supplied."""
    o = json.loads(json_string)
    properties = {}
    if isinstance(self, db.Model):
      properties = self.properties()
    for key, value in o.iteritems():
      property_value = value
      property_key = Jsonifiable.transform_from_camelcase(key)
      if property_key in properties.keys():
        if properties[property_key].data_type == types.IntType:
          property_value = int(value)
      self.__setattr__(property_key, property_value)
