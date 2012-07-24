import re
import datetime
import socket

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

    def _register_document(self, document, field_name):
        self.field_name = field_name
        # test for aliases
        if self.aliases is not None:
            for alias in self.aliases:
                document._aliases.append((alias, field_name))

    def _changed(self, instance):
        """ notify parent's document for changes """
        instance._modified_fields.add(self.field_name)
        instance._is_valid = False
        # called recursively
        if instance._parent:
            field = instance._parent_field
            field._changed(instance._parent)


class EmbeddedDocumentField(BaseField):
    def __init__(self, field_type, **kwargs):
        self.field_type = field_type

        if not isinstance(field_type, DocumentMetaClass):
            raise AttributeError('EmbeddedDocumentField only accepts Document subclass')

        super(EmbeddedDocumentField, self).__init__(**kwargs)

    def _prepare(self, instance, value):
        """ we instantiate the dict to an object if needed
            and set the parent
        """
        if isinstance(value, dict):
            value = self.field_type(parent=instance, parent_field=self, **value)
        if isinstance(value, self.field_type):
            value._parent_field = self
        return value

    def _validate(self, value):
        if not isinstance(value, self.field_type):
            return False

        return value.validate()


class NotifyParentList(list):
    """
        A minimal list subclass that will notify for modification to the parent
        for special case like parent.obj.append
    """
    def __init__(self, seq=(), parent=None, field=None):
        self._parent = parent
        self._field = field
        super(NotifyParentList, self).__init__(seq)

    def _tag_obj_for_parent_name(self, obj):
        """ check if the obj is a document and set his parent_name
        """
        if isinstance(obj, Document):
            obj._parent = self._parent
            obj._parent_field = self._field
            return
        try:
            iter(obj)
        except TypeError:
            return
        for entry in obj:
            if isinstance(entry, Document):
                entry._parent = self._parent
                entry._parent_field = self._field

    def _notify_parents(self):
        self._field._changed(self._parent)

    def __add__(self, other):
        self._tag_obj_for_parent_name(other)
        self._notify_parents()
        return super(NotifyParentList, self).__add__(other)

    def __setslice__(self, i, j, seq):
        self._tag_obj_for_parent_name(seq)
        self._notify_parents()
        return super(NotifyParentList, self).__setslice__(i, j, seq)

    def __delslice__(self, i, j):
        self._notify_parents()
        return super(NotifyParentList, self).__delslice__(i, j)

    def __setitem__(self, key, value):
        self._tag_obj_for_parent_name(value)
        self._notify_parents()
        return super(NotifyParentList, self).__setitem__(key, value)

    def __delitem__(self, key):
        self._notify_parents()
        return super(NotifyParentList, self).__delitem__(key)

    def append(self, p_object):
        self._tag_obj_for_parent_name(p_object)
        self._notify_parents()
        return super(NotifyParentList, self).append(p_object)

    def remove(self, value):
        self._notify_parents()
        return super(NotifyParentList, self).remove(value)

    def insert(self, index, p_object):
        self._tag_obj_for_parent_name(p_object)
        self._notify_parents()
        return super(NotifyParentList, self).insert(index, p_object)

    def extend(self, iterable):
        self._tag_obj_for_parent_name(iterable)
        self._notify_parents()
        return super(NotifyParentList, self).extend(iterable)

    def pop(self, index=None):
        if index is None:
            if super(NotifyParentList, self).pop():
                self._notify_parents()
        else:
            if super(NotifyParentList, self).pop(index):
                self._notify_parents()


class ListField(BaseField):
    def __init__(self, subfield, max_length=0, min_length=0, **kwargs):
        self.subfield = subfield
        self.max_length = max_length
        self.min_length = min_length
        if "default" not in kwargs:
            kwargs["default"] = []

        if not isinstance(subfield, (BaseField)):
            raise AttributeError('ListField only accepts BaseField subclass')

        super(ListField, self).__init__(**kwargs)

    def _register_document(self, document, field_name):
        self.subfield._register_document(document, field_name)
        BaseField._register_document(self, document, field_name)

    def _validate(self, value):
        if not isinstance(value, list):
            return False
        if self.max_length != 0:
            if len(value) > self.max_length:
                return False
        if self.min_length != 0:
            if len(value) < self.min_length:
                return False
        for entry in value:
            if not self.subfield._validate(entry):
                return False
        return True

    def _prepare(self, instance, value):
        """ we set the parent for each element
            and set a NotifyParentList in place of a list
        """
        try:
            iter(value)
        except TypeError:
            pass
        else:
            if hasattr(self.subfield, "_prepare"):
                obj_list = []
                for obj in value:
                    obj = self.subfield._prepare(instance, obj)
                    if obj:
                        obj_list.append(obj)
                value = obj_list
            if not isinstance(value, NotifyParentList):
                value = NotifyParentList(value, parent=instance, field=self)
        return value


class BooleanField(BaseField):
    def _validate(self, value):
        if not isinstance(value, (bool)):
            return False
        return True


class StringField(BaseField):
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
            if value == '' and not self.is_required:
                return True
            return False

        return True


class IPAddressField(StringField):
    """ validate ipv4 and ipv6
    """
    def _validate(self, value):
        try:
            socket.inet_pton(socket.AF_INET, value)
        except socket.error:
            try:
                socket.inet_pton(socket.AF_INET6, value)
            except socket.error:
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


class FloatField(BaseField):
    def _validate(self, value):
        if not isinstance(value, (float, int)):
            return False
        return True


class DateTimeField(BaseField):
    def _validate(self, value):
        if not isinstance(value, (datetime.datetime)):
            return False
        return True


class DocumentMetaClass(type):
    def __new__(cls, name, bases, attrs):
        meta = attrs.get("_meta", False)
        if not meta:
            fields = {}
            newattrs = {}
            for attr_name, attr_value in attrs.items():
                if isinstance(attr_value, BaseField):
                    fields[attr_name] = attr_value
                else:
                    newattrs[attr_name] = attr_value
            newattrs["__slots__"] = tuple(fields.keys())
            newattrs["_fields"] = fields
        else:
            newattrs = attrs
        newattrs["_meta"] = meta

        klass = type.__new__(cls, name, bases, newattrs)

        if not meta:
            klass._aliases = []
            for field_name, field in klass._fields.items():
                field._register_document(klass, field_name)

            for base in bases:
                if not getattr(base, "_meta", True):
                    base_fields = base._fields.copy()
                    base_fields.update(klass._fields)
                    klass._fields = base_fields
                    klass._aliases += base._aliases
        return klass


class Document(object):

    __metaclass__ = DocumentMetaClass
    __slots__ = ('_modified_fields', '_is_valid', '_parent', '_parent_field')

    _meta = True

    def __init__(self, parent=None, parent_field=None, **values):
        self._modified_fields = set()
        # optimization to avoid double validate() if nothing has changed
        self._is_valid = False
        self._parent = parent
        self._parent_field = parent_field

        # TODO: this check should be done during __new__
        for alias, key in self._aliases:
            if alias in values:
                if key in values:
                    raise ValueError("The field %s overrides this alias %s" %
                        (key, alias))
                values[key] = values[alias]
                del values[alias]

        for key, field in self._fields.items():
            value = values.get(key, None)

            if value is not None:
                if hasattr(field, "_prepare"):
                    value = field._prepare(self, value)
                object.__setattr__(self, key, value)

    def __getattr__(self, name):
        field = self._fields.get(name, None)
        if field:
            value = field.default
            if callable(value):
                value = value()
            if value is not None:
                if hasattr(field, "_prepare"):
                    value = field._prepare(self, value)
                object.__setattr__(self, name, value)
            return value
        raise AttributeError

    def __setattr__(self, name, value):
        field = self._fields.get(name, None)
        if field is not None:
            if hasattr(field, "_prepare"):
                value = field._prepare(self, value)
            field._changed(self)
        return object.__setattr__(self, name, value)

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
            value = getattr(self, field_name)

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

    def _apply_filters(self, filters_list_or_callable, to_filter):
        """ apply all filters function (one arg the dict to filter)
        """
        try:
            iter(filters_list_or_callable)
        except TypeError:
            if callable(filters_list_or_callable):
                return filters_list_or_callable(to_filter)
            else:
                return to_filter

        for filter in filters_list_or_callable:
            if callable(filter):
                to_filter = filter(to_filter)

        return to_filter

    def _call_for_visibility_on_child(self, data_dict, fields_list,
                                      visibility, json_compliant=False):
        """ this will call dict_for_%s() visibility on EmbeddedDocument
            and ListField and return a dict
            containing data_dict with key replaced by the result (in place)
        """
        for field in fields_list:
            if isinstance(self._fields[field], EmbeddedDocumentField):
                if field in data_dict and data_dict[field] is not None:
                    call_method = getattr(data_dict[field], 'dict_for_%s' % visibility)
                    data_dict[field] = call_method(json_compliant)

            if isinstance(self._fields[field], ListField):
                if isinstance(self._fields[field].subfield, EmbeddedDocumentField):
                    current_field = []
                    for doc in data_dict[field]:
                        call_method = getattr(doc, 'dict_for_%s' % visibility)
                        current_field.append(call_method(json_compliant))
                    data_dict[field] = current_field
        return data_dict

    def dict_for_save(self, json_compliant=False):
        """ return a copy dict with field_name:value
            raise ValidationError if not valid
        """
        # TODO: put back a cache here if validate has been called earlier
        if not self.validate():
            raise ValidationException()

        save_dict = {}
        for key in self._fields.keys():
            value = getattr(self, key)
            if value is not None:
                save_dict[key] = value

        # we have to call dict_for_save() on embedded document
        save_dict = self._call_for_visibility_on_child(save_dict,
            self._fields, 'save', json_compliant)

        has_filter = getattr(self, 'pre_save_filter', None)

        return save_dict if has_filter is None else \
            self._apply_filters(self.pre_save_filter, save_dict)

    def dict_for_public(self, json_compliant=False):
        """ return a copy dict with keys specified in public_fields
            with value from _data or self.property
            or return empty dict
            raise ValidationError if not valid
        """
        public_fields = getattr(self, 'public_fields', [])
        public_dict = self._dict_for_fields('public', public_fields, json_compliant)
        has_filter = getattr(self, 'pre_public_filter', None)
        return public_dict if has_filter is None else\
            self._apply_filters(self.pre_public_filter, public_dict)

    def dict_for_owner(self, json_compliant=False):
        """ return a copy dict with keys specified in owner_fields
            with value from _data or self.property
            or return empty dict
            raise ValidationError if not valid
        """
        owner_fields = getattr(self, 'owner_fields', [])
        owner_dict = self._dict_for_fields('owner', owner_fields, json_compliant)
        has_filter = getattr(self, 'pre_owner_filter', None)
        return owner_dict if has_filter is None else\
            self._apply_filters(self.pre_owner_filter, owner_dict)

    def _dict_for_fields(self, visibility, fields_list=None, json_compliant=False):
        """ return a dict with keys specified in fields_list from _data
            or self.property
            or return empty dict
            call embedded fields if needed
            raise ValidationError if not valid
        """
        if fields_list is None:
            return {}
        if not self._is_valid:
            if not self._validate_fields(fields_list, stop_on_required=True):
                raise ValidationException()

        # find all the keys in fields_list that are fields
        # and form a dict with the value in _data
        field_dict = {good_key: getattr(self, good_key) for good_key in fields_list
            if good_key in self._fields.keys() and getattr(self, good_key) is not None}

        # call sub dict_for_method
        subok_dict = self._call_for_visibility_on_child(field_dict, field_dict.keys(),
            visibility=visibility, json_compliant=json_compliant)

        # find all the keys in public_fields that are NOT fields
        # return a dict with getattr on the obj
        property_dict =  {key_not_real_field: getattr(self, key_not_real_field)
                            for key_not_real_field in fields_list
                            if key_not_real_field not in self._fields.keys()}

        return dict(subok_dict.items() + property_dict.items())

    def modified_fields(self):
        """ return a set of fields modified via setters
        """
        return self._modified_fields

    def dict_for_modified_fields(self, validate=True):
        """ return a dict of fields modified via setters as key with value
            will raise ValidationError if partial modified data not valid
            you can force no validation with validate=False
        """
        if validate and not self.validate_partial():
            raise ValidationException()

        return {good_key: getattr(self, good_key) for good_key in self._modified_fields}


# Filters
def rename_field(old_name, new_name, dict_to_filter):
    if old_name in dict_to_filter:
        dict_to_filter[new_name] = dict_to_filter[old_name]
        del dict_to_filter[old_name]
    return dict_to_filter
