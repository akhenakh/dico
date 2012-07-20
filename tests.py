import dico
import unittest
import re
import datetime
import dico.mongo
from bson.objectid import ObjectId
import random
from functools import partial

class TestDico(unittest.TestCase):
    def setUp(self):
        pass

    def test_partial(self):
        class User(dico.Document):
            id = dico.IntegerField(required=True)
            count = dico.IntegerField()

        user = User()
        user.count = 2

        self.assertFalse(user.validate())

        self.assertTrue(user.validate_partial())

        user.count = 'a'
        self.assertFalse(user.validate_partial())

    def test_integer_field(self):
        class User(dico.Document):
            id = dico.IntegerField(required=True)

        user = User()
        self.assertFalse(user.validate())

        user.id = 4
        self.assertEqual(4, user.id)

        user.id = 'toto'
        self.assertFalse(user.validate())

    def test_boolean_field(self):
        class User(dico.Document):
            active = dico.BooleanField()

        user = User()
        user.active = True
        self.assertTrue(user.validate())
        user.active = 1
        self.assertFalse(user.validate())

    def test_default_value(self):
        class User(dico.Document):
            count = dico.IntegerField(default=1)

            public_fields = ['count']

        user = User()
        user_dict = user.dict_for_save()
        self.assertIn('count', user_dict)
        self.assertEqual(user.count, 1)

        user = User()
        public_dict = user.dict_for_public()
        self.assertIn('count', public_dict)

    def test_string_field(self):
        class User(dico.Document):
            name = dico.StringField(min_length=3, max_length=8)

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
        class RegUser(dico.Document):
            code = dico.StringField(compiled_regex=test_regexp)

        user = RegUser()
        user.code = 'nok'
        self.assertFalse(user.validate())

        user.code = 'okbaby'
        self.assertTrue(user.validate())

        user.code = ''
        self.assertTrue(user.validate())
        class RegUser(dico.Document):
            code = dico.StringField(compiled_regex=test_regexp, required=True)
        user = RegUser()
        user.code = ''
        self.assertFalse(user.validate())

    def test_create_from_dict(self):
        class User(dico.Document):
            name = dico.StringField()

        test_dict = {'bad_name':'toto', 'name':'Bob'}
        user = User(**test_dict)

        self.assertEqual(user.name, 'Bob')

        self.assertIsNone(getattr(user, 'bad_name', None))

    def test_dict_for_save(self):
        class User(dico.Document):
            name = dico.StringField()
            count = dico.IntegerField()

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

        self.assertRaises(dico.ValidationException, user.dict_for_save)

        user = User()
        user.name = 'Bob'
        # test for no raise as count is not required
        user.dict_for_save()

    def test_dict_visibility(self):
        class User(dico.Document):
            name = dico.StringField()

        user = User()
        user.name = 'Bob'

        public_dict = user.dict_for_public()
        owner_dict = user.dict_for_owner()
        self.assertDictEqual({}, public_dict)
        self.assertDictEqual({}, owner_dict)

        class User(dico.Document):
            name = dico.StringField()
            id = dico.IntegerField()
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
        self.assertRaises(dico.ValidationException, user.dict_for_public)
        self.assertRaises(dico.ValidationException, user.dict_for_owner)

        class User(dico.Document):
            name = dico.StringField()
            lastname = dico.StringField()

            public_fields = ['name', 'lastname']

        user = User()
        user.name = 'Bob'

        self.assertIn('name', user.dict_for_public())
        # asked for but not set
        self.assertNotIn('firstname', user.dict_for_public())

        user.lastname = 'Spong'
        self.assertIn('lastname', user.dict_for_public())

    def test_modified_fields(self):
        class User(dico.Document):
            name = dico.StringField()
            id = dico.IntegerField()

        user = User()
        self.assertEqual(user.modified_fields(), set())

        user.name = 'Bob'
        self.assertIn('name', user.modified_fields())

        modified_dict = user.dict_for_modified_fields()
        self.assertIn('name', modified_dict)
        self.assertEqual(modified_dict['name'], 'Bob')
        self.assertEqual(len(modified_dict.keys()), 1)

    def test_choices(self):
        class User(dico.Document):
            id = dico.IntegerField(choices=[2,3])

        user = User()
        user.id = 5
        self.assertFalse(user.validate())

        user.id = 3
        self.assertTrue(user.validate())

        class BadUser(dico.Document):
            id = dico.IntegerField(choices=['toto',3])
        user = BadUser()
        user.id = 'toto'
        self.assertFalse(user.validate())

    def test_return_field(self):
        class User(dico.Document):
            id = dico.IntegerField()

        self.assertTrue( isinstance(User.id, dico.IntegerField))

    def test_callable_default(self):
        def answer():
            return 42
        class User(dico.Document):
            id = dico.IntegerField(required=True, default=answer)

        user = User()
        save_dict = user.dict_for_save()
        self.assertEqual(save_dict['id'], 42)

        class User(dico.Document):
            id = dico.IntegerField(default=answer)

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
        class User(dico.Document):
            id = dico.IntegerField()
            count = dico.IntegerField(required=True)

        user = User()
        user.count = 2
        self.assertTrue(user.validate())

    def test_properties(self):
        class User(dico.Document):
            id = dico.IntegerField()

            @property
            def age(self):
                return 42

            public_fields = ['age']

        user = User()
        self.assertEqual(user.age, 42)

        public_dict = user.dict_for_public()
        self.assertIn('age', public_dict)
        self.assertEqual(public_dict['age'], 42)

        class User(dico.Document):
            id = dico.IntegerField()

            public_fields = ['age']

        user = User()
        self.assertRaises(KeyError, user.dict_for_public)

    def test_datetime_field(self):
        class User(dico.Document):
            creation_date = dico.DateTimeField(default=datetime.datetime.utcnow)

        user = User()
        self.assertTrue(isinstance(user.creation_date, datetime.datetime))

        user.creation_date = datetime.datetime.utcnow()
        self.assertTrue(user.validate())
        user.creation_date = 3
        self.assertFalse(user.validate())

    def test_objectid_field(self):
        class User(dico.Document):
            id = dico.mongo.ObjectIdField(default=ObjectId)

        user = User()
        user.id = ObjectId('500535541aebce0dfc000000')
        self.assertTrue(user.validate())
        user.id = 4
        self.assertFalse(user.validate())

    def test_ensure_default_getter_equals(self):
        class User(dico.Document):
            id = dico.mongo.ObjectIdField(default=ObjectId)

        user = User()
        id = user.id
        self.assertEqual(id, user.dict_for_save()['id'])

    def test_url_field(self):
        class User(dico.Document):
            blog_url = dico.URLField(max_length=64)

        user = User()
        user.blog_url = 'http://www.yahoo.com/truc?par=23&machin=23'
        self.assertTrue(user.validate())
        user.blog_url = 'bob'
        self.assertFalse(user.validate())
        user.blog_url = 'http://www.yahoo.com/truc?par=23&machin=23&param=1234567890aabcdef'
        self.assertFalse(user.validate())

    def test_email_field(self):
        class User(dico.Document):
            email = dico.EmailField(max_length=32)

        user = User()
        user.email = 'bob@sponge.com'
        self.assertTrue(user.validate())

        user.email = 'sponge.com'
        self.assertFalse(user.validate())

        user.email = '123456789012345678901234567890@spong.com'
        self.assertFalse(user.validate())

    def test_alias(self):
        class User(dico.Document):
            id = dico.IntegerField(aliases=['_id', 'aid'])

        user = User(_id=2)
        self.assertEqual(user.id, 2)

        user = User(aid=4)
        self.assertEqual(user.id, 4)

    def test_float_field(self):
        class User(dico.Document):
            lat = dico.FloatField()

        user = User()
        user.lat = 4.5
        self.assertTrue(user.validate())
        user.lat = 4
        self.assertTrue(user.validate())
        user.lat = 'b'
        self.assertFalse(user.validate())

    def test_attach_method(self):
        class User(dico.Document):
            id = dico.IntegerField()

            def echo(self, value):
                return value

        user = User()
        user.id = 3
        self.assertTrue(user.validate())
        self.assertEqual(user.echo('hello'), 'hello')

    def test_ip_address(self):
        class User(dico.Document):
            ip = dico.IPAddressField()

        user = User()
        user.ip = '194.117.200.10'
        self.assertTrue(user.validate())
        user = User()
        user.ip = u'127.0.0.1'
        self.assertTrue(user.validate())
        user.ip = '::1'
        self.assertTrue(user.validate())
        user.ip = '2001:0db8:85a3:0042:0000:8a2e:0370:7334'
        self.assertTrue(user.validate())
        user.ip = 'bob'
        self.assertFalse(user.validate())

    def test_list_field(self):
        class User(dico.Document):
            friends = dico.ListField(dico.IntegerField())

        user = User()
        user.friends = [1212, 34343, 422323]
        self.assertTrue(user.validate())

        user.friends = ['a', 34343, 422323]
        self.assertFalse(user.validate())

        user.friends = 444
        self.assertFalse(user.validate())

        user.friends = []
        self.assertTrue(user.validate())

        class User(dico.Document):
            friends = dico.ListField(dico.IntegerField(), required=True)

        user = User()
        self.assertFalse(user.validate())

        user.friends = [1]
        self.assertTrue(user.validate())

        class User(dico.Document):
            friends = dico.ListField(dico.IntegerField(), min_length=2, max_length=4)

        user = User()
        user.friends = [1,2,3,4,5]
        self.assertFalse(user.validate())
        user.friends = [1,2,3]
        self.assertTrue(user.validate())
        user.friends = [1]
        self.assertFalse(user.validate())
        user.friends.append(3)
        self.assertTrue(user.validate())

    def test_pre_save(self):
        class User(dico.Document):
            id = dico.IntegerField()

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

        def rename_id_before_save(filter_dict):
            if 'id' in filter_dict:
                filter_dict['_id'] = filter_dict['id']
                del filter_dict['id']
            return filter_dict

        class User(dico.Document):
            id = dico.IntegerField()

            pre_save_filter = rename_id_before_save

        user = User()
        user.id = 53
        #TODO: allow a direct callable
        #self.assertIn('_id', user.dict_for_save())

    def test_pre_save_partial(self):
        class User(dico.Document):
            id = dico.IntegerField()

            pre_save_filter = [partial(dico.rename_field, 'id', '_id')]

        user = User()
        user.id = 53

        self.assertIn('_id', user.dict_for_save())
        self.assertEqual(53, user.dict_for_save()['_id'])

    def test_mongo_example_document(self):
        class MongoUser(dico.Document):
            id = dico.mongo.ObjectIdField(aliases=['_id'], required=True, default=ObjectId)
            name = dico.StringField()

            pre_save_filter = [partial(dico.rename_field, 'id', '_id')]
            public_fields = ['id', 'name']

        user = MongoUser()
        user.name = 'Bob'

        save_dict = user.dict_for_save()
        self.assertIn('_id', save_dict)

    def test_slots(self):
        class User(dico.Document):
            id = dico.IntegerField()

        user = User()
        error = False
        try:
            user.truc = 2
        except AttributeError:
            error = True
        self.assertTrue(error)

    def test_inside_code(self):
        class User(dico.Document):
            id = dico.IntegerField()

        user = User()
        self.assertEqual({}, user._dict_for_fields('owner'))


    def test_creation_double_bug(self):
        class TestObj(dico.Document):
            id = dico.IntegerField()

        test = TestObj()
        test.id = 45
        test = TestObj()
        test = TestObj()
        self.assertNotEqual(test.id, 45)

    def test_in_place_modification_bug(self):
        class OAuthToken(dico.Document):
            consumer_secret = dico.StringField(required=True, max_length=32)
            active = dico.BooleanField(default=True)
            token_id = dico.mongo.ObjectIdField(required=True, default=ObjectId)

            owner_field = ['token_id', 'consumer_secret']

        class User(dico.Document):
            id = dico.IntegerField()
            tokens = dico.ListField(dico.EmbeddedDocumentField(OAuthToken))

            #public_fields = ['tokens']
            owner_fields = ['tokens']

        token = OAuthToken()
        token.consumer_secret = 'fac470fcd'

        user = User()
        user.tokens = [token]

        user.dict_for_save()
        self.assertIsInstance(user.tokens[0], OAuthToken)

    def test_list_embedded(self):
        class OAuthToken(dico.Document):
            consumer_secret = dico.StringField(required=True, max_length=32)
            active = dico.BooleanField(default=True)
            token_id = dico.mongo.ObjectIdField(required=True, default=ObjectId)

            owner_fields = ['token_id', 'consumer_secret']

        class User(dico.Document):
            id = dico.IntegerField()
            tokens = dico.ListField(dico.EmbeddedDocumentField(OAuthToken))

            public_fields = ['tokens']
            owner_fields = ['tokens']

        user = User()
        user.id = 2

        token = OAuthToken()
        token.consumer_secret = 'fac470fcd'
        token.token_id = ObjectId()

        user.tokens = [token, token]

        self.assertEqual(user.tokens[0].consumer_secret, 'fac470fcd')
        self.assertTrue(user.validate())

        user.tokens = [1]

        self.assertFalse(user.validate())

        user = User()
        user.tokens.append(token)
        self.assertEqual(len(user.tokens), 1)

        user = User()
        user.tokens = None
        user.tokens.append(token)
        token2 = OAuthToken()
        token2.consumer_secret = 'fac470fcd'
        user.tokens.append(token2)
        self.assertEqual(len(user.tokens), 2)
        user_dict = user.dict_for_save()
        self.assertEqual(len(user_dict['tokens']), 2)
        self.assertIn('consumer_secret', user_dict['tokens'][0])

        public_dict = user.dict_for_public()
        self.assertNotIn('consumer_secret', public_dict['tokens'][0])

        owner_dict = user.dict_for_owner()
        self.assertIn('consumer_secret', owner_dict['tokens'][0])
        self.assertIn('consumer_secret', owner_dict['tokens'][1])

        user_dict = {'id':4, 'tokens':[{'token_id':4, 'consumer_secret':'34dbcedf'}]}
        user = User(**user_dict)

        self.assertEqual(len(user.modified_fields()), 0)
        user.tokens = [ OAuthToken(token_id=5, consumer_secret='23fbda')]
        self.assertIn('tokens', user.modified_fields())
        user = User(**user_dict)
        user.tokens[0].token_id = 6
        self.assertIn('tokens', user.modified_fields())

        bad_user_dict = {'id':4, 'tokens':[3]}
        user = User(**bad_user_dict)
        self.assertEqual(len(user.tokens), 0)

        user = User(**user_dict)
        user.tokens.append(token)
        self.assertIn('tokens', user.modified_fields())

        user = User(**user_dict)
        user.tokens + [token]
        self.assertIn('tokens', user.modified_fields())

        user = User(**user_dict)
        # not that we will add the same object should not raise modification
        user.tokens[0] = token
        self.assertIn('tokens', user.modified_fields())

        user = User(**user_dict)
        user.tokens.insert(0, token)
        self.assertIn('tokens', user.modified_fields())
        user = User(**user_dict)
        user.tokens.pop(0)
        self.assertIn('tokens', user.modified_fields())
        user = User(**user_dict)
        user.tokens.pop()
        self.assertIn('tokens', user.modified_fields())

        #TODO: needs more tests for NotifyParentList subclass

    def test_embedded(self):
        class OAuthToken(dico.Document):
            consumer_secret = dico.StringField(required=True, max_length=32)
            active = dico.BooleanField(default=True)

        class User(dico.Document):
            id = dico.IntegerField()
            token = dico.EmbeddedDocumentField(OAuthToken)

            public_fields = ['token']

        user = User()
        user.token = 3

        self.assertFalse(user.validate())

        user.token = OAuthToken()
        self.assertFalse(user.validate())
        user.token = OAuthToken(consumer_secret='fac470fcd')
        self.assertTrue(user.validate())
        user.token = OAuthToken(consumer_secret='fac470fcd')
        user_dict = user.dict_for_save()
        self.assertIn('token', user_dict)
        self.assertIn('consumer_secret', user_dict['token'])

        # there is a bug in validate() that modify the content when embedded
        user.token = OAuthToken(consumer_secret='fac470fcd')
        user.validate()
        user_dict = user.dict_for_save()
        self.assertIn('token', user_dict)
        self.assertIn('consumer_secret', user_dict['token'])

        public_dict = user.dict_for_public()
        self.assertIn('token', public_dict)

        # ensure modified works for embedded

        class OAuthToken(dico.Document):
            consumer_secret = dico.StringField()
            id = dico.IntegerField()

        class User(dico.Document):
            id = dico.IntegerField()
            token = dico.EmbeddedDocumentField(OAuthToken)

        init_dict = {'id':1, 'token':{'consumer_secret':'3fbc81fa', 'id':453245}}
        user = User( **init_dict )
        user.token = OAuthToken(consumer_secret='sdf3223', id=3)
        self.assertIn('token', user.modified_fields())

        init_dict = {'id':1, 'token':{'consumer_secret':'3fbc81fa', 'id':453245}}
        user = User( **init_dict )
        user.token.id = 5
        self.assertIn('token', user.modified_fields())

        init_dict = {'user':{'id':1, 'token':{'consumer_secret':'3fbc81fa', 'id':453245}}}
        class Group(dico.Document):
            user = dico.EmbeddedDocumentField(User)

        group = Group(**init_dict)
        group.user.token.consumer_secret = 'toto'
        self.assertIn('user', group.modified_fields())

    def test_sublassing(self):
        class BaseDocument(dico.Document):
            id = dico.IntegerField()

        class User(BaseDocument):
            name = dico.StringField()

        user = User()
        user.id = 4
        user.name = 'Bob'

        self.assertTrue(user.validate())

        self.assertIn('name', user.dict_for_save())
        self.assertIn('id', user.dict_for_save())

    def test_cascade_creation(self):
        class Sub(dico.Document):
            id = dico.IntegerField()

        class User(dico.Document):
            name = dico.StringField()
            sub = dico.EmbeddedDocumentField(Sub)

        sub = Sub(id=4)
        user = User(name='Bob', sub=sub)
        self.assertTrue(user.validate())

        dic = {'name':'Bob', 'sub':{'id':4}}
        user = User(**dic)
        self.assertTrue(user.validate())

        dic = {'name':'Bob', 'sub':sub}
        user = User(**dic)
        self.assertIsInstance(user.sub, Sub)
        self.assertTrue(user.validate())

        class Sub(dico.Document):
            id = dico.IntegerField()

        class User(dico.Document):
            name = dico.StringField()
            sublist = dico.ListField(dico.EmbeddedDocumentField(Sub))


        sub1 = Sub(id=1)
        sub2 = Sub(id=2)
        user = User(name='Bob', sublist = [sub1, sub2])
        self.assertTrue(user.validate())

        dic = {'name':'Bob', 'sublist':[{'id':1},{'id':2}]}
        user = User(**dic)
        self.assertTrue(user.validate())
        self.assertEqual(len(user.sublist), 2)
        self.assertIsInstance(user.sublist[0], Sub)


        # maybe we should not insert a partial list here
        # and reject everything ?
        # this will create a one element list with sub2
        user = User(name='Bob', sublist = [1, sub2])
        self.assertEqual(len(user.sublist), 1)

    def test_meta_subclassing(self):
        class DocumentWrapper(dico.Document):
            __slots__ = "test"
            _meta = True

        class User(DocumentWrapper):
            id = dico.IntegerField()

        user = User()
        user.id = 1
        user.test = False

        self.assertNotIn('test', user.dict_for_save())

    def test_empty_set(self):
        class User(dico.Document):
            url = dico.URLField()

        user = User()
        user.url = ''
        self.assertTrue(user.validate())

if __name__ == "__main__":
    unittest.main()
