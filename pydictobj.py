import re

URL_REGEX = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

EMAIL_REGEX = re.compile(
    # dot-atom
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"
    # quoted-string
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-011\013\014\016'
    r'-\177])*"'
    # domain
    r')@(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$',
    re.IGNORECASE
)

class ValidationException(Exception):
    """The field did not pass validation.
    """
    def __init__(self, reason, field_name, field_value, *args, **kwargs):
        super(ShieldException, self).__init__(*args, **kwargs)
        self.reason = reason
        self.field_name = field_name
        self.field_value = field_value

    def __str__(self):
        return '%s - %s:%s' % (self.reason, self.field_name, self.field_value)

class BaseField(object):
    def __init__(self, default=None, required=False, field_name=None):
        self.default = default
        self.required = required
        self.field_name = field_name

    def __set__(self, instance, value):
        instance._data[self.field_name] = value

    def __get__(self, instance, owner):
        if instance is None:
            # Document class being used rather than a document object
            return self
        value = instance._data.get(self.field_name)

        if value is None:
            value = self.default
            # Allow callable default values
            if callable(value):
                value = value()

        return value

class StringField(BaseField):
    """A unicode string field.
    """

    def __init__(self, compiled_regex=None, max_length=None, min_length=None, **kwargs):
        self.compiled_regex = compiled_regex
        self.max_length = max_length
        self.min_length = min_length
        super(StringField, self).__init__(**kwargs)

    def _validate(self, value, is_required=False):
        if not isinstance(value, (str, unicode)):
            return False

        if not is_required and value is None:
            return True

        if self.max_length is not None and len(value) > self.max_length:
            return False
            raise ValidationException('String value is too long',
                                  self.field_name, value)

        if self.min_length is not None and len(value) < self.min_length:
            return False
            raise ValidationException('String value is too short',
                                  self.uniq_field, value)

        if self.compiled_regex is not None and self.compiled_regex.match(value) is None:
            return False
            message = 'String value did not match validation regex',
            raise ValidationException(message, self.uniq_field, value)

        return True

class IntegerField(BaseField):
    def _validate(self, value, is_required=False):
        if not is_required and value is None:
            return True
        if not isinstance(value, (int, long)):
            return False
        return True

class DocumentMetaClass(type):
    def __new__(cls, name, bases, attrs):
        fields = {}

        klass = type.__new__(cls, name, bases, attrs)
        for attr_name, attr_value in attrs.items():
            has_class = hasattr(attr_value, "__class__")
            if has_class and issubclass(attr_value.__class__, BaseField):
                fields[attr_name] = attr_value
                attr_value.field_name = attr_name
        klass._fields = fields
        klass.__slots__ = fields.keys()
        return klass


class Document(object):
    __metaclass__ = DocumentMetaClass

    def __init__(self, **values):
        self._data = {}
        self._changed_fields = []

        for key in values.keys():
            if key in self._fields:
                self._data[key] = values[key]

    public_fields = None
    owner_fields = None

    pre_save_hook = None
    post_save_hook = None
    pre_public_hook = None
    post_public_hook = None
    pre_owner_hook = None
    post_owner_hook = None

    def validate(self, required=True):
        for field_name in self._fields.keys():
            field = self._fields[field_name]
            value = self._data.get(field_name)
            if not field._validate(value, is_required=required):
                return False
        return True

    def validate_partial(self):
        return self.validate(required=False)



