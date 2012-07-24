try:
    import bson.objectid
except ImportError:
    raise ImportError(
        'Using the ObjectIdField requires Pymongo. '
    )

from . import BaseField, Document, rename_field
from functools import partial


class ObjectIdField(BaseField):
    def _validate(self, value):
        if not isinstance(value, (bson.objectid.ObjectId)):
            return False
        return True
