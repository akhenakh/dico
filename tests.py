import pydictobj
import unittest

class TestAPIShareCan(unittest.TestCase):
    def setUp(self):
        pass

    def test_integer_field(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField(required=True)

        user = User()
        self.assertFalse(user.validate())
        self.assertTrue(user.validate_partial())
        user.id = 4
        self.assertTrue(user.validate())
        user.id = 'toto'
        self.assertFalse(user.validate())

    if __name__ == "__main__":
        unittest.main()