import pydictobj
import unittest
import re
import datetime
import pydictobj.mongo
from bson.objectid import ObjectId
import random
from functools import partial

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

    def test_boolean_field(self):
        class User(pydictobj.Document):
            active = pydictobj.BooleanField()

        user = User()
        user.active = True
        self.assertTrue(user.validate())
        user.active = 1
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

        self.assertEqual(User.public_fields, ['name',])

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

        class User(pydictobj.Document):
            name = pydictobj.StringField()
            lastname = pydictobj.StringField()

            public_fields = ['name', 'lastname']

        user = User()
        user.name = 'Bob'

        self.assertIn('name', user.dict_for_public())
        # asked for but not set
        self.assertNotIn('firstname', user.dict_for_public())

        user.lastname = 'Spong'
        self.assertIn('lastname', user.dict_for_public())

    def test_modified_fields(self):
        class User(pydictobj.Document):
            name = pydictobj.StringField()
            id = pydictobj.IntegerField()

        user = User()
        self.assertEqual(user.modified_fields(), set())

        user.name = 'Bob'
        self.assertIn('name', user.modified_fields())

        modified_dict = user.dict_for_modified_fields()
        self.assertIn('name', modified_dict)
        self.assertEqual(modified_dict['name'], 'Bob')
        self.assertEqual(len(modified_dict.keys()), 1)

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

        user = User(id=44)
        self.assertEqual(user.id, 44)

    def test_not_required(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField()
            count = pydictobj.IntegerField(required=True)

        user = User()
        user.count = 2
        self.assertTrue(user.validate())

    def test_properties(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField()

            @property
            def age(self):
                return 42

            public_fields = ['age']

        user = User()
        self.assertEqual(user.age, 42)

        public_dict = user.dict_for_public()
        self.assertIn('age', public_dict)
        self.assertEqual(public_dict['age'], 42)

        class User(pydictobj.Document):
            id = pydictobj.IntegerField()

            public_fields = ['age']

        user = User()
        self.assertRaises(KeyError, user.dict_for_public)

    def test_datetime_field(self):
        class User(pydictobj.Document):
            creation_date = pydictobj.DateTimeField(default=datetime.datetime.utcnow)

        user = User()
        self.assertTrue(isinstance(user.creation_date, datetime.datetime))

        user.creation_date = datetime.datetime.utcnow()
        self.assertTrue(user.validate())
        user.creation_date = 3
        self.assertFalse(user.validate())

    def test_objectid_field(self):
        class User(pydictobj.Document):
            id = pydictobj.mongo.ObjectIdField(default=ObjectId)

        user = User()
        user.id = ObjectId('500535541aebce0dfc000000')
        self.assertTrue(user.validate())
        user.id = 4
        self.assertFalse(user.validate())

    def test_ensure_default_getter_equals(self):
        class User(pydictobj.Document):
            id = pydictobj.mongo.ObjectIdField(default=ObjectId)

        user = User()
        id = user.id
        self.assertEqual(id, user.dict_for_save()['id'])

    def test_url_field(self):
        class User(pydictobj.Document):
            blog_url = pydictobj.URLField(max_length=64)

        user = User()
        user.blog_url = 'http://www.yahoo.com/truc?par=23&machin=23'
        self.assertTrue(user.validate())
        user.blog_url = 'bob'
        self.assertFalse(user.validate())
        user.blog_url = 'http://www.yahoo.com/truc?par=23&machin=23&param=1234567890aabcdef'
        self.assertFalse(user.validate())

    def test_email_field(self):
        class User(pydictobj.Document):
            email = pydictobj.EmailField(max_length=32)

        user = User()
        user.email = 'bob@sponge.com'
        self.assertTrue(user.validate())

        user.email = 'sponge.com'
        self.assertFalse(user.validate())

        user.email = '123456789012345678901234567890@spong.com'
        self.assertFalse(user.validate())

    def test_alias(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField(aliases=['_id', 'aid'])

        user = User(_id=2)
        self.assertEqual(user.id, 2)

        user = User(aid=4)
        self.assertEqual(user.id, 4)

    def test_float_field(self):
        class User(pydictobj.Document):
            lat = pydictobj.FloatField()

        user = User()
        user.lat = 4.5
        self.assertTrue(user.validate())
        user.lat = 4
        self.assertTrue(user.validate())
        user.lat = 'b'
        self.assertFalse(user.validate())

    def test_attach_method(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField()

            def echo(self, value):
                return value

        user = User()
        user.id = 3
        self.assertTrue(user.validate())
        self.assertEqual(user.echo('hello'), 'hello')

    def test_ip_address(self):
        class User(pydictobj.Document):
            ip = pydictobj.IPAdressField()

        user = User()
        user.ip = '194.117.200.10'
        self.assertTrue(user.validate())
        user.ip = '::1'
        self.assertTrue(user.validate())
        user.ip = '2001:0db8:85a3:0042:0000:8a2e:0370:7334'
        self.assertTrue(user.validate())
        user.ip = 'bob'
        self.assertFalse(user.validate())

    def test_list_field(self):
        class User(pydictobj.Document):
            friends = pydictobj.ListField(pydictobj.IntegerField())

        user = User()
        user.friends = [1212, 34343, 422323]
        self.assertTrue(user.validate())

        user.friends = ['a', 34343, 422323]
        self.assertFalse(user.validate())

        user.friends = 444
        self.assertFalse(user.validate())

        user.friends = []
        self.assertTrue(user.validate())

        class User(pydictobj.Document):
            friends = pydictobj.ListField(pydictobj.IntegerField(), required=True)

        user = User()
        self.assertFalse(user.validate())

        user.friends = [1]
        self.assertTrue(user.validate())

        class User(pydictobj.Document):
            friends = pydictobj.ListField(pydictobj.IntegerField(), min_length=2, max_length=4)

        user = User()
        user.friends = [1,2,3,4,5]
        self.assertFalse(user.validate())
        user.friends = [1,2,3]
        self.assertTrue(user.validate())
        user.friends = [1]
        self.assertFalse(user.validate())

    def test_pre_save(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField()

            def rename_id_before_save(filter_dict):
                if 'id' in filter_dict:
                    filter_dict['_id'] = filter_dict['id']
                    del filter_dict['id']
                return filter_dict

            def add_name(filter_dict):
                filter_dict['name'] = 'Paule'
                return filter_dict

            pre_save_filter = [rename_id_before_save, add_name]

        user = User()
        user.id = 53

        self.assertIn('_id', user.dict_for_save())
        self.assertIn('name', user.dict_for_save())

    def test_pre_save_partial(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField()

            pre_save_filter = [partial(pydictobj.rename_field, 'id', '_id')]

        user = User()
        user.id = 53

        self.assertIn('_id', user.dict_for_save())

    def test_mongo_example_document(self):
        class MongoUser(pydictobj.Document):
            id = pydictobj.mongo.ObjectIdField(aliases=['_id'], required=True, default=ObjectId)
            name = pydictobj.StringField()

            pre_save_filter = [partial(pydictobj.rename_field, 'id', '_id')]
            public_fields = ['id', 'name']

        user = MongoUser()
        user.name = 'Bob'

        save_dict = user.dict_for_save()
        self.assertIn('_id', save_dict)

    def test_slots(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField()

        user = User()
        error = False
        try:
            user.truc = 2
        except AttributeError:
            error = True
        self.assertTrue(error)

    def test_inside_code(self):
        class User(pydictobj.Document):
            id = pydictobj.IntegerField()

        user = User()
        self.assertEqual({}, user._dict_for_fields())

if __name__ == "__main__":
    unittest.main()
