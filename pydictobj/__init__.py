import re
import datetime

URL_REGEX_COMPILED = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

EMAIL_REGEX_COMPILED = re.compile(
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
    pass


class BaseField(object):
    def __init__(self, default=None, required=False, choices=None, aliases=None):
        """ the BaseField class for all Document's field
        """
        self.default = default
        self.is_required = required
        self.choices = choices
        self.aliases = aliases
        # Set by the metaclass
        #self.field_name

    def __set__(self, instance, value):
        instance._data[self.field_name] = value
        instance._modified_fields.add(self.field_name)
        instance._is_valid = False

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
            if value is not None:
                instance._data[self.field_name] = value
        return value


class BooleanField(BaseField):
    def _validate(self, value):
        if not isinstance(value, (bool)):
            return False
        return True


class StringField(BaseField):
    """A unicode string field.
    """
    def __init__(self, compiled_regex=None, max_length=None, min_length=None, **kwargs):
        self.compiled_regex = compiled_regex
        self.max_length = max_length
        self.min_length = min_length
        super(StringField, self).__init__(**kwargs)

    def _validate(self, value):
        if not isinstance(value, (str, unicode)):
            return False

        if self.max_length is not None and len(value) > self.max_length:
            return False

        if self.min_length is not None and len(value) < self.min_length:
            return False

        if self.compiled_regex is not None and self.compiled_regex.match(value) is None:
            return False

        return True


class URLField(StringField):
    def __init__(self, **kwargs):
        super(URLField, self).__init__(compiled_regex=URL_REGEX_COMPILED, **kwargs)


class EmailField(StringField):
    def __init__(self, **kwargs):
        super(EmailField, self).__init__(compiled_regex=EMAIL_REGEX_COMPILED, **kwargs)


class IntegerField(BaseField):
    def _validate(self, value):
        if not isinstance(value, (int, long)):
            return False
        return True


class DateTimeField(BaseField):
    def _validate(self, value):
        if not isinstance(value, (datetime.datetime)):
            return False
        return True


class ListField(BaseField):
    pass


class DocumentMetaClass(type):
    def __new__(cls, name, bases, attrs):
        fields = {}

        klass = type.__new__(cls, name, bases, attrs)
        klass._aliases_dict = {}
        for attr_name, attr_value in attrs.items():
            has_class = hasattr(attr_value, "__class__")
            if has_class and issubclass(attr_value.__class__, BaseField):
                fields[attr_name] = attr_value
                attr_value.field_name = attr_name

                # test for aliases
                if fields[attr_name].aliases is not None:
                    for alias in fields[attr_name].aliases:
                        klass._aliases_dict[alias] = attr_name

        klass._fields = fields
        klass.__slots__ = fields.keys()
        return klass


class Document(object):
    __metaclass__ = DocumentMetaClass

    def __init__(self, **values):
        self._data = {}
        self._modified_fields = set()
        # optimization to avoid double validate() if nothing has changed
        self._is_valid = False
        # initialized by metaclass
        #self._fields
        #self._aliases_dict

        for key in values.keys():
            if key in self._fields:
                self._data[key] = values[key]
                continue
            if key in self._aliases_dict:
                real_key = self._aliases_dict[key]
                self._data[real_key] = values[key]

    public_fields = None
    owner_fields = None

    pre_save_filter = None
    post_save_filter = None
    pre_public_filter = None
    post_public_filter = None
    pre_owner_filter = None
    post_owner_filter = None

    def _validate_fields(self, fields_list, stop_on_required=True):
        """ take a list of fields name and validate them
            return True if all fields in fields_list required are valid and set
            return True if fields in fields_list are valid
            and set if stop_on_required=False
        """
        for field_name in fields_list:
            # if field name is not in the field list but a property
            if field_name not in self._fields.keys():

                if hasattr(self, field_name):
                    continue
                else:
                    raise KeyError

            field = self._fields[field_name]
            value = self._data.get(field_name)

            # if we have a default to call
            if value is None and field.default is not None:
                self._data[field_name] = getattr(self, field_name)
                value = self._data[field_name]

            if value is None:
                if stop_on_required and field.is_required:
                    return False
                continue

            # validate possible choices first
            if field.choices is not None:
                if value not in field.choices:
                    return False

            if not field._validate(value):
                return False

        return True

    def validate(self, stop_on_required=True):
        """ return True if all required are valid and set
            return True if fields are valid and set if required=False
            see validate_partial
        """
        if stop_on_required and self._is_valid:
            return True

        is_valid = self._validate_fields(self._fields.keys(),
            stop_on_required=stop_on_required)

        if stop_on_required and is_valid:
            self._is_valid = True

        return is_valid

    def validate_partial(self):
        """ validate only the format of each field regardless of stop_on_required option
            usefull to validate some parts of a document
        """
        return self.validate(stop_on_required=False)

    def dict_for_save(self, json_compliant=False):
        """ return a dict with field_name:value
            raise ValidationError if not valid
        """
        if self._is_valid:
            return self._data
        if not self.validate():
            raise ValidationException()
        return self._data

    def dict_for_fields(self, fields_list=None, json_compliant=False):
        """ return a dict with keys specified in fields with in _data or self.property
            or return empty dict
        """
        if fields_list is None:
            return {}
        if not self._is_valid:
            if not self._validate_fields(fields_list, stop_on_required=True):
                raise ValidationException()

        # find all the keys in fields_list that are fields and form a dict with the value in _data
        public_dict = {good_key: self._data[good_key] for good_key in fields_list
                       if good_key in self._fields.keys()}

        # find all the keys in public_fields that are NOT fields
        # return a dict with getattr on the obj
        property_dict =  {key_not_real_field: getattr(self, key_not_real_field)
                          for key_not_real_field in fields_list
                          if key_not_real_field not in self._fields.keys()}

        return dict(public_dict.items() + property_dict.items())

    def dict_for_public(self, json_compliant=False):
        """ return a dict with keys specified in public_fields
            with value from _data or self.property
            or return empty dict
        """
        return self.dict_for_fields(self.public_fields)

    def dict_for_owner(self, json_compliant=False):
        """ return a dict with keys specified in owner_fields or return empty dict
        """
        return self.dict_for_fields(self.owner_fields)

    def modified_fields(self):
        """ return a set of fields modified via setters
        """
        return self._modified_fields
