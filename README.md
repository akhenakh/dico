# Dico

After using [DictShield](https://github.com/j2labs/dictshield), a "database-agnostic modeling system", I've found the idea very usefull when dealing with NoSQL database, but want to choose another direction.
Dico is an attempt to solve my needs, heavily inspired by DictShield.

Most of the time you're manipulating data from a database server, modify it and save, especially in web development.

Here are the usual patterns with Dico:

### Create an object from scratch and validate fields

    class BlogPost(Document):
       id = IntegerField()
       title = StringField(required=True, max_length=40)
       body = StringField(max_length=4096)
       creation_date = DateField(required=True, default=datetime.datetime.utcnow)

	>>> post = BlogPost() 
    >>> post.body = 'I'm a new post'
    >>> post.validate()
    False

    >>> post.title = 'New post'
    >>> post.validate()
    True

	>>> post2 = BlogPost(title='Hop hop', body='thebody')

### Store it/Serialize it

    >>> post.dict_for_save()
    {'id': 45, 'title': 'New post', 'body': "I'm a new post"}

If dict_for_save is called on **not valid data** it will raise a **ValidationException**.

### Validate an object populate from existing data and modify it

    >>> dict_from_db = {'id': '50000685467ffd11d1000001', 'title': 'A post', 'body': "I'm a post"}
    >>> post = BlogPost(**dict_from_db)
    >>> post.title
    "I'm a title from the DB"
	
	>>> post.title = 'New title from cli'
    >>> post.validate()
    True
    
### See modified fields since creation

    >>> post.modified_fields()
    ['title']

	# Usefull for Mongo update
    >>> post.dict_for_changes()
    {'title': 'New title from cli'}

Note that dict_for_changes does not contains fields modifier by default=.

### Create an object with partial data
When working with real data, you will not fetch **every** fields from your DB, but still wants validation.

	>>> dict_from_db = {'body': "I'm a post"}
    >>> post = BlogPost(**dict_from_db)
	>>> post.validate()
	False
	
	>>> post.validate_partial()
	True
	
	>>> post2.BlogPost()
	>>> post2.title = 3
	>>> post2.validate_partial()
	False
	>>> post2.title = 'New title'
	>>> post2.validate_partial()
	True

### ListField
A list can contains n elements of a field's type.

    class User(dico.Document):
        friends = dico.ListField(dico.IntegerField(), min_length=2, max_length=4)

### Field types

* BooleanField
* StringField
* IPAddressField
* URLField
* EmailField
* IntegerField
* FloatField
* DateTimeField
* ListField
* EmbeddedDocumentField

### Prepare object for export and adjust visibility of fields

    class User(Document):
        id = IntegerField(required=True)
        firstname = StringField(required=True, max_length=40)
        email = EmailField()
    
		owner_fields = ['firstname', 'email']
		public_fields = ['firstname']
		
	>>> user = User(**dict_from_db)
	>>> user.dict_for_owner()
	{'firstname': 'Paul', 'email':'paul_sponge@yahoo.com'}
	>>> user.dict_for_public()
	{'firstname': 'Paul'}
	>> user.dict_for_save()
	{'firstname': 'Paul', 'email':'paul_sponge@yahoo.com', 'id': 56}

### Aliases for field input
In mongo the id is called _id so we need a way to make the Document accept it is as id.

    class User(Document):
	    id = ObjectIdField(required=True, aliases=['_id'])
		
	>>> user = User(_id=ObjectId('50000685467ffd11d1000001'))
	>>> user.id
	'50000685467ffd11d1000001'
	
### Hooks filters
There are 3 hooks filter to manipulate data before and after exports, it should be a list of callable to filter

* pre\_save_filter
* pre\_owner_filter
* pre\_public_filter

Here we are renaming firstname field to first_name

    class User(Document):
        firstname = StringField(required=True, max_length=40)
		def save_filter(dict):
			dict['first_name] = dict['firstname']
			del dict['id']
			return dict	
		
		public_fields = ['firstname']
		pre_save_filter = [save_filter]
		
	>>> user = User(firstname='Bob')
	>>> user.dict_for_save()
	{'first_name':'Bob'}
	>>> user.dict_for_public()
	{'firstname':'Bob'}

You can use partial to call function with arguments

    from functools import partial

    class User(dico.Document):
        id = dico.IntegerField()
        def rename_field(old_field, new_field, filter_dict):
        	if old_field in filter_dict:
        	    filter_dict[new_field] = filter_dict[old_field]
        	    del filter_dict[old_field]
        	return filter_dict

        pre_save_filter = [partial(rename_field, 'id', '_id')]
        public_fields = ['id', 'name']

	
### @properties visibility
Properties are suitable for serialization

    class User(Document):
		firstname = StringField(required=True, max_length=40)
		name = StringField(required=True, max_length=40)
		
		@properties
		def full_name(self):
			return firstname + ' ' + name
			
		public_fields = ['full_name']
		
		>>> user.dict_for_public()
		{'full_name': 'Sponge Bob'}

### Embedded fields
You may embed document in document, directly or within a list

    class OAuthToken(dico.Document):
        consumer_secret = dico.StringField(required=True, max_length=32)
        active = dico.BooleanField(default=True)
        token_id = dico.mongo.ObjectIdField(required=True, default=ObjectId)

    class User(dico.Document):
        id = dico.IntegerField()
        token = dico.EmbeddedDocumentField(OAuthToken)

    >>> user = User()
    >>> user.token = 3
    >>> user.validate()
    False

    >>> user.token = OAuthToken()
    >>> user.validate()
    False
    >>> user.token = OAuthToken(consumer_secret='fac470fcd')
    >>> user.validate()
    False

    class OAuthToken(dico.Document):
        consumer_secret = dico.StringField(required=True, max_length=32)
        active = dico.BooleanField(default=True)
        token_id = dico.mongo.ObjectIdField(required=True, default=ObjectId)

    class User(dico.Document):
        id = dico.IntegerField()
        tokens = dico.ListField(dico.EmbeddedDocumentField(OAuthToken))

    >>> user = User()
    >>> user.id = 2

    >>> token = OAuthToken()
    >>> token.consumer_secret = 'fac470fcd'
    >>> token2 = OAuthToken()
    >>> token2.consumer_secret = 'fac470fcd'
    >>> user.tokens = [token, token2]

    # cascade recreate obj

    class OAuthToken(dico.Document):
        consumer_secret = dico.StringField()
        id = dico.IntegerField()

    class User(dico.Document):
        id = dico.IntegerField()
        tokens = dico.ListField(dico.EmbeddedDocumentField(OAuthToken))

    >>> user_dict = {'id':1, 'tokens':[
            {'consumer_secret':'3fbc81fa', 'id':453245},
            {'consumer_secret':'bcd821s', 'id':98837}
        ] }

    >>> user = User(**user_dict)

    >>> user.tokens
    [<__main__.OAuthToken object at 0x109b3b390>, <__main__.OAuthToken object at 0x109b3b2c0>]
    
### Example usage with mongo
We know we want to update only some fields firstname and email, so we fetch the object with no field, update our fields then update, later we create a new user and save it.
Not the rename_field function which is provided in Dico as shortcut.

    class User(Document):
		id = ObjectIdField(default=ObjectId(), required=True, aliases=['_id'])
		firstname = StringField(required=True, max_length=40)
        email = EmailField()

        pre_save_filter = [partial(dico.rename_field, 'id', '_id')]
        owner_fields = ['firstname', 'id', 'email']
	    public_fields = ['firstname', 'id']
		
	>>> user_dict = db.user.find_one({'email':'bob@sponge.com'}, [])
	>>> user = User(**user_dict)
	>>> user.firstname = 'Bob'
	>>> user.email = 'bob@yahoo.com'
	>>> user.validate_partial()
	True
	>>> db.user.update({'_id': user.id}, user.dict_for_modified_fields())
	
	>>> user = User()
	>>> user.email = 'sponge@bob.com'
	>>> user.validate()
	True
	>>> db.user.save(user.dict_for_save())
	
	# note this trick here we are reusing the public fields list from the user object to query only
	# this specific fields and make queries faster
	>>> user_dict = db.user.find_one({'email':'bob@yahoo.com', User.public_fields)
	>>> user = User(**user_dict)
	>>> user.dict_for_public()
	{'id':'50000685467ffd11d1000001', 'firstname':'Bob'}
        
## Features

* required fields are checked for full object validation, but individual fields can be tested with validate_partial
* To dict for owner (eg user object, the owner can see the fields email)
* To dict for public (eg user object, public can't see the fields email)
* To dict for mongo db or sql saving
* Transform field rename field before exporting, example: remove microseconds before public serialization on a datefield (as JSON cls hooks) or to transform id to \_id before serialize
* multiple filters, pre save filter, pre owner filter, pre public filter
* Track modified fields, for example to use update only changed fields with mongo
* Can serialize properties to owner and public dict
* partial = not all fields, can create an object with only some fields you want to export (to avoid select * )
* Regexp compiled only one time
* use \_\_slots\_\_ for memory optimization and to get on AttributeError on typo
* cascade creation of embedded oject

## Ideas
* Convert all fields to json acceptable type, (for use with ujson directly), a param in dict\_for\_public(json_convert=True) ?
* Use it as form validation? (I'm not sure I need this: my REST views are not exactly mapped to my objects)
* Can external user modify this field? Eg id
* Returns a representation of this Dico class as a JSON schema. (nizox)
* Post save commit() reset modified fields

## TODO
* Implements json_compliant
* errors explanation
* the continue in _validate_fields does not show up in coverage
* in _apply_filters if call directly a callable not in a list arg error
* update management for mongo ? (it will become a real ORM)
* how to deal with filters while subclassing ?

## Differences with dictshield
* dictshield raise ValueError while setting a property on a document if the data does not match the field, makes validate() useless
* dictshield allows unknown properties to be set
* dictshield does not use __slots__
* dictshield is more complete but complexe
* dictshield has separates files in packages, makes import boring


## Installing

Dico is available via [pypi](http://pypi.python.org).

    pip install dico


## Change log
* 0.2 cascade creation, notify parent's document for modified fields, regexp stringfield now validate with '' (empty string)
* 0.1.1 fix important bugs, usable in production
* 0.1 initial release does not use in production

## Known bugs

## Contributors

* [Fabrice aneche](https://github.com/akhenakh)
* [Nicolas Vivet](https://github.com/nizox)
* [James Dennis](https://github.com/j2labs) for inspiration

## License

    * Copyright (c) 1998, Regents of the University of California
    * All rights reserved.
    * Redistribution and use in source and binary forms, with or without
    * modification, are permitted provided that the following conditions are met:
    *
    *     * Redistributions of source code must retain the above copyright
    *       notice, this list of conditions and the following disclaimer.
    *     * Redistributions in binary form must reproduce the above copyright
    *       notice, this list of conditions and the following disclaimer in the
    *       documentation and/or other materials provided with the distribution.
    *     * Neither the name of the University of California, Berkeley nor the
    *       names of its contributors may be used to endorse or promote products
    *       derived from this software without specific prior written permission.
    *
    * THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
    * EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    * DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
    * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.