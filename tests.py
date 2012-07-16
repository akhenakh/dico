import pydictobj
import unittest

class TestAPIShareCan(unittest.TestCase):
    def setUp(self):
        pass

    def test_partial(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField(required=True)
            count = pydictobj.IntegerField()

        user = User()
        user.count = 2

        self.assertFalse(user.validate())

        self.assertTrue(user.validate_partial())

        user.count = 'a'
        self.assertFalse(user.validate_partial())

    def test_integer_field(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField(required=True)

        user = User()
        self.assertFalse(user.validate())

        user.id = 4
        self.assertEqual(4, user.id)

        user.id = 'toto'
        self.assertFalse(user.validate())

    def test_default_value(self):
        class User(pydictobj.Document):
            count = pydictobj.IntegerField(default=1)

        user = User()
        self.assertEqual(user.count, 1)

    def test_string_field(self):
        class User(pydictobj.Document):
            name = pydictobj.StringField(min_length=3)

        user = User()
        user.name = 4
        self.assertFalse(user.validate())

        user.name = 'Bob'
        self.assertTrue(user.validate())

        user.name = 'a'
        self.assertFalse(user.validate())


    def test_create_from_dict(self):
        class User(pydictobj.Document):
            name = pydictobj.StringField()

        test_dict = {'bad_name':'toto', 'name':'Bob'}
        user = User(**test_dict)

        self.assertEqual(user.name, 'Bob')

        self.assertIsNone(getattr(user, 'bad_name', None))

    def test_dict_for_save(self):
        class User(pydictobj.Document):
            name = pydictobj.StringField()
            count = pydictobj.IntegerField()

        user = User()
        user.name = 'Bob'
        user.count = 5
        result_dict = user.dict_for_save()

        self.assertIn('name', result_dict)
        self.assertIn('count', result_dict)
        self.assertEqual(result_dict['name'], 'Bob')
        self.assertEqual(result_dict['count'], 5)

    def test_dict_visibility(self):
        class User(pydictobj.Document):
            name = pydictobj.StringField()

        user = User()
        user.name = 'Bob'

        public_dict = user.dict_for_public()

        self.assertDictEqual({}, public_dict)

        class User(pydictobj.Document):
            name = pydictobj.StringField()
            public_fields = ['name']

        user = User()
        user.name = 'Bob'
        public_dict = user.dict_for_public()
        self.assertIn('name', public_dict)

    if __name__ == "__main__":
        unittest.main()
