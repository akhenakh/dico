import pydictobj
import unittest
import re

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
            name = pydictobj.StringField(min_length=3, max_length=8)

        user = User()
        user.name = 4
        self.assertFalse(user.validate())

        user.name = 'Bob'
        self.assertTrue(user.validate())

        user.name = 'a'
        self.assertFalse(user.validate())

        user.name = 'abcdefghit'
        self.assertFalse(user.validate())

        test_regexp = re.compile(r"^ok")
        class RegUser(pydictobj.Document):
            code = pydictobj.StringField(compiled_regex=test_regexp)

        user = RegUser()
        user.code = 'nok'
        self.assertFalse(user.validate())

        user.code = 'okbaby'
        self.assertTrue(user.validate())

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

        # test caching result for validate
        user.validate()
        user.validate()
        result_dict = user.dict_for_save()
        result_dict = user.dict_for_save()


        self.assertIn('name', result_dict)
        self.assertIn('count', result_dict)
        self.assertEqual(result_dict['name'], 'Bob')
        self.assertEqual(result_dict['count'], 5)

        user = User()
        user.name = 5

        self.assertRaises(pydictobj.ValidationException, user.dict_for_save)

        user = User()
        user.name = 'Bob'
        # test for no raise as count is not required
        user.dict_for_save()

    def test_dict_visibility(self):
        class User(pydictobj.Document):
            name = pydictobj.StringField()

        user = User()
        user.name = 'Bob'

        public_dict = user.dict_for_public()
        owner_dict = user.dict_for_owner()
        self.assertDictEqual({}, public_dict)
        self.assertDictEqual({}, owner_dict)

        class User(pydictobj.Document):
            name = pydictobj.StringField()
            id = pydictobj.IntegerField()
            public_fields = ['name']
            owner_fields = ['name', 'id']

        user = User()
        user.name = 'Bob'
        user.id = 3
        public_dict = user.dict_for_public()
        self.assertIn('name', public_dict)
        owner_dict = user.dict_for_owner()
        self.assertIn('name', owner_dict)
        self.assertIn('id', owner_dict)

        user = User()
        user.name = 4
        self.assertRaises(pydictobj.ValidationException, user.dict_for_public)
        self.assertRaises(pydictobj.ValidationException, user.dict_for_owner)

    def test_modified_fields(self):
        class User(pydictobj.Document):
            name = pydictobj.StringField()

        user = User()
        self.assertEqual(user.modified_fields(), set())

        user.name = 'Bob'
        self.assertIn('name', user.modified_fields())

    def test_choices(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField(choices=[2,3])

        user = User()
        user.id = 5
        self.assertFalse(user.validate())

        user.id = 3
        self.assertTrue(user.validate())

        class BadUser(pydictobj.Document):
            id = pydictobj.IntegerField(choices=['toto',3])
        user = BadUser()
        user.id = 'toto'
        self.assertFalse(user.validate())

    def test_return_field(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField()

        self.assertTrue( isinstance(User.id, pydictobj.IntegerField))

    def test_callable_default(self):
        def answer():
            return 42
        class User(pydictobj.Document):
            id = pydictobj.IntegerField(required=True, default=answer)

        user = User()
        save_dict = user.dict_for_save()
        self.assertEqual(save_dict['id'], 42)

        class User(pydictobj.Document):
            id = pydictobj.IntegerField(default=answer)

        user = User()
        save_dict = user.dict_for_save()
        # it should be there
        # but not on validate_partial
        self.assertIn('id', save_dict)
        self.assertIsNotNone(user.id)

        user = User()
        self.assertTrue(user.validate_partial())

    def test_not_required(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField()
            count = pydictobj.IntegerField(required=True)

        user = User()
        user.count = 2
        self.assertTrue(user.validate())

if __name__ == "__main__":
    unittest.main()
