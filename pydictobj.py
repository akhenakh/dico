
class BaseField(object):
    def __init__(self, default=None, required=False):
        self.default_method = default
        self.required = required
        self.data = None

    def __set__(self, instance, value):
        self.data = value

class DocumentMetaClass(type):
    def __new__(cls, name, bases, attrs):
        fields_name = []

        ### Gen a class instance
        klass = type.__new__(cls, name, bases, attrs)
        for attr_name, attr_value in attrs.items():
            has_class = hasattr(attr_value, "__class__")
            if has_class and issubclass(attr_value.__class__, BaseField):
                attr_value.field_name = attr_name
                fields_name.append(attr_name)
        klass.fields_name = fields_name
        return klass


class Document(object):
    __metaclass__ = DocumentMetaClass

    def __init__(self, **values):
        _changed_fields = []
        pass

    public_fields = None
    owner_fields = None

    pre_save_hook = None
    post_save_hook = None
    pre_public_hook = None
    post_public_hook = None
    pre_owner_hook = None
    post_owner_hook = None

#    def __setitem__(self, name, value):
#        if name not in self.field_name:
#            raise KeyError(name)
#        field = getattr(self, field_name)
#        field.data = value

    def validate(self, required=True):
        for field_name in self.fields_name:
            field = getattr(self, field_name)
            if not field._validate(is_required=required):
                return False
        return True

    def validate_partial(self):
        return self.validate(required=False)

class IntegerField(BaseField):
    def _validate(self, is_required=False):
        if not is_required and self.data is None:
            return True
        if not isinstance(self.data, (int, long)):
            return False
        return True

    def _execute_default(self):
        if self.default_method is not None:
            self.data = self.default_method()






