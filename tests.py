import pydictobj
import unittest

class TestAPIShareCan(unittest.TestCase):
    def setUp(self):
        pass

    def test_integer_field(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField(required=True)
            count = pydictobj.IntegerField(default=1)

        user = User()
        self.assertFalse(user.validate())

        user.id = 4
        self.assertEqual(4, user.id)

        user.id = 'toto'
        self.assertFalse(user.validate())

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


    if __name__ == "__main__":
        unittest.main()