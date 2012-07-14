#pydictobj

## Features I want

* can transform id to \_id before serialize (use a transform pattern applicable everywhere ?)
* required is checked for full object validate, but individual fields can be tested see partial
* Transform field rename field before exporting, example: remove microseconds before public serialization on a datefield (as JSON cls hooks)
* To dict for owner (eg user object, the owner can see the fields email)
* To dict for public (eg user object, public can't see the fields email)
* To dict for mongo db or sql saving
* pre save and post save hook
* Track changed field to use update only changed fields with mongo
* Can serialize properties
* partial = not all fields, can create an object with only some fields you want to export (to avoid select * ) 
* Post save commit() reset changed fields
* Regexp compiled only one time

## Ideas
* Convert all fields to json acceptable type, (for use with ujson directly), a param in dict\_for\_public(json_convert=True) ?
* Use it as form validation? (I'm not sure I need this: my REST views are not exactly mapped to my objects)
* Can external user modify this field? Eg id
* use \_\_slots\_\_ as we know the fields ?
* Returns a representation of this pydictobj class as a JSON schema. (nizox)


Most of the time you're manipulating data from a database server, modify it and save, especially in web development.

Here are the usual patterns:

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

### Create an object populate from existing data and modify it
    >>> dict_from_db = {'id': '50000685467ffd11d1000001', 'title': 'A post', 'body': "I'm a post"}
    >>> post = BlogPost(**dict_from_db)
    >>> post.title
    "I'm a title from the DB"
	
	>>> post.title = 'New title from cli'
    >>> post.validate()
    True
### See modified fields since creation

    >>> post.changed_fields()
    ['title']

	# Usefull for Mongo update
    >>> post.dict_for_changes()
    {'title': 'New title from cli'}

### Create an object with partial data
When working with real data, you will not fetch **every** fields from your DB, but still wants validation

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

### Prepare object for export and adjust visibility of fields
    class User(Document):
        id = IntegerField(required=True)
        firstname = StringField(required=True, max_length=40)
        email = EmailField()
    
		_owner_fields = ['firstname', 'email']
		_public_fields = ['firstname']
		
	>>> user = User(**dict_from_db)
	>>> user.dict_for_owner()
	{'firstname': 'Paul', 'email':'paul_sponge@yahoo.com'}
	>>> user.dict_for_public()
	{'firstname': 'Paul'}
	>> user.dict_for_save()
	{'firstname': 'Paul', 'email':'paul_sponge@yahoo.com', 'id': 56}

### Alias for field input
In mongo the id is called _id so we need a way to make the Document accept it is as id.

    class User(Document):
	    id = ObjectIdField(required=True, alias='_id')
		
	>>> user = User(_id=ObjectId('50000685467ffd11d1000001'))
	>>> user.id
	'50000685467ffd11d1000001'
	
### Hooks
There are 6 hooks to manipulate data before and after exports

* \_pre\_save_hook
* \_post\_save_hook
* \_pre\_owner_hook
* \_post\_owner_hook
* \_pre\_public_hook
* \_post\_public_hook

Here we are renaming firstname field to first_name

    class User(Document):
        firstname = StringField(required=True, max_length=40)
		def save_hook(dict):
			dict['_first_name] = dict['firstname']
			del dict['id']
			return dict	
		
		_public_fields = ['firstname']
		_pre_save_hook = save_hook
		
	>>> user = User(firstname='Bob')
	>>> user.dict_for_save()
	{'first_name':'Bob'}
	>>> user.dict_for_public()
	{'firstname':'Bob'}
	
		
### Example usage with mongo
We know we want to update only some fields firstname and email, so we fetch the object with no field, then we create a new user and save it

    class User(Document):
		id = ObjectIdField(required=True, alias='_id')
		firstname = StringField(required=True, max_length=40)
        email = EmailField()

	    _public_fields = ['firstname']
		
	>>> user_dict = db.user.find({'email':'bob@sponge.com'}, [])
	>>> user = User()
	>>> user.firstname = 'Bob'
	>>> user.email = 'bob@yahoo.com'
	>>> user.validate_partial()
	True
	>>> db.user.update({'_id': user.id}, user.changed_fields())
	
	>>> user = User()
	>>> user.id = ObjectId()
	>>> user.email = 'sponge@bob.com'
	>>> db.user.save(user.dict_for_save())
	
### @properties visibility
Properties are suitable for serialization

    class User(Document):
		firstname = StringField(required=True, max_length=40)
		name = StringField(required=True, max_length=40)
		
		@properties
		def full_name(self):
			return firstname + ' ' + name
			
		_public_fields = ['full_name']
		
		>>> user.dict_for_public()
		{'full_name': 'Sponge Bob'}
    
### Special case for Id field? TODO
Id field can be handled differently, for example in Mysql with auto increment the id is given by the server, in Mongo you generate it client side

    class User(Document):
        id = ObjectIdField(required=True) 
        firstname = StringField(required=True, max_length=40)
   