try:
    from bson.objectid import ObjectId
except ImportError:
    raise ImportError(
        'Using the ObjectIdField requires Pymongo. '
    )
import bson.objectid

from . import BaseField

class ObjectIdField(BaseField):
    def _validate(self, value):
        if not isinstance(value, (bson.objectid.ObjectId)):
            return False
        return True