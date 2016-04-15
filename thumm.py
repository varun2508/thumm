from flask import Flask, jsonify, request,send_from_directory
from flask import render_template
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import and_
from sqlalchemy import func
from marshmallow import Schema, fields, ValidationError, pre_load
from pprint import pprint
from flask_mail import Mail, Message
from math import radians, cos, sin, asin, sqrt
import uuid
import os
from datetime import datetime, timedelta
import json

mail = Mail()

app = Flask(__name__)
mail.init_app(app)

app.config.from_pyfile('config.cfg')
db = SQLAlchemy(app)

# This is the path to the upload directory
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['UPLOAD_EVENTS_FOLDER'] = 'uploads/events/'
# These are the extension that we are accepting to be uploaded
app.config['ALLOWED_EXTENSIONS'] = set(['png', 'jpg', 'jpeg'])

# For a given file, return whether it's an allowed type or not
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


##### MODELS #####

class Users(db.Model):
	__tablename__ = 'Users'
	id = db.Column('id', db.Integer, primary_key=True)
	name = db.Column('name', db.Unicode)
	email = db.Column('email', db.Unicode)
	password = db.Column('password', db.Unicode)
	facebook_id = db.Column('facebook_id', db.Unicode)
	phone_id = db.Column('phone_id', db.Unicode)
	phone_type = db.Column('phone_type', db.Unicode)
	birthdate = db.Column('birthdate', db.Unicode)
	location = db.Column('location', db.Unicode)
	phone = db.Column('phone', db.Unicode)
	gender = db.Column('gender', db.Unicode)
	photo = db.Column('photo', db.Unicode)
	token = db.Column('token', db.Unicode)
	status = db.Column('status', db.Unicode)
	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}
	def __init__(self, name, email, password):
		self.name = name
		self.email = email
		self.password = password
		
class User_friends(db.Model):
	__tablename__ = 'User_friends'
	id = db.Column('id', db.Integer, primary_key=True)
	user_id = db.Column('user_id', db.Integer)
	friend_id = db.Column('friend_id', db.Integer, db.ForeignKey("Users.id"))
	
	friend = db.relationship("Users", foreign_keys=[friend_id])
	
	def __init__(self, user_id, friend_id):
		self.user_id = user_id
		self.friend_id = friend_id
	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}
	
class Friend_request(db.Model):
	__tablename__ = 'Friend_request'
	id = db.Column('id', db.Integer, primary_key=True)
	from_id = db.Column('from_id', db.Integer, db.ForeignKey("Users.id"))
	to_id = db.Column('to_id', db.Integer, db.ForeignKey("Users.id"))
	date = db.Column('date', db.Date)
	
	from_user = db.relationship("Users", foreign_keys=[from_id])
	to_user = db.relationship("Users", foreign_keys=[to_id])
	
	def __init__(self, from_id, to_id):
		self.from_id = from_id
		self.to_id = to_id
		self.date = datetime.now()


class Notification(db.Model):
	__tablename__ = 'Notifications'
	id = db.Column('id', db.Integer, primary_key=True)
	date = db.Column('date', db.Date)
	msg = db.Column('msg', db.Unicode)
	user_id = db.Column('user_id', db.Integer)
	data = db.Column('data', db.Unicode)
	type = db.Column('type', db.Unicode)
	status = db.Column('status', db.Integer)
	def __init__(self, msg, type, data, user_id):
		self.user_id = user_id
		self.msg = msg
		self.type = type
		self.data = json.dumps(data)
		self.date = datetime.now()
	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}

		
class Events(db.Model):
	__tablename__ = 'Events'
	id = db.Column('id', db.Integer, primary_key=True)
	lat = db.Column('lat', db.Float)
	long = db.Column('long', db.Float)
	location = db.Column('location', db.Unicode)
	date = db.Column('date', db.Date)
	type = db.Column('type', db.Unicode)
	notes = db.Column('notes', db.Unicode)
	picture = db.Column('picture', db.Unicode)
	category = db.Column('category', db.Unicode)
	user_id = db.Column('user_id', db.Integer, db.ForeignKey("Users.id"))
	added = db.Column('added', db.Date)
	
	user = db.relationship("Users", foreign_keys=[user_id])
	
	def __init__(self, user_id):
		self.user_id = user_id
		self.added = datetime.now()
	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}
			
class Event_requests(db.Model):
	__tablename__ = 'Events_requests'
	id = db.Column('id', db.Integer, primary_key=True)
	user_id = db.Column('user_id', db.Integer)
	from_id = db.Column('from_id', db.Integer)
	event_id = db.Column('event_id', db.Integer, db.ForeignKey("Events.id"))
	
	event = db.relationship("Events", foreign_keys=[event_id])
	
	def __init__(self, user_id, event_id, from_id):
		self.user_id = user_id
		self.event_id = event_id
		self.from_id = from_id
	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Event_attends(db.Model):
	__tablename__ = 'Event_attends'
	id = db.Column('id', db.Integer, primary_key=True)
	user_id = db.Column('user_id', db.Integer,  db.ForeignKey("Users.id"))
	event_id = db.Column('event_id', db.Integer)
	lat = db.Column('lat', db.Float)
	long = db.Column('long', db.Float)
	status = db.Column('status', db.Unicode)
	date = db.Column('date', db.Date)
	
	user = db.relationship("Users", foreign_keys=[user_id])
	
	def __init__(self, user_id, event_id):
		self.user_id = user_id
		self.event_id = event_id
		self.date = datetime.now()
	def as_dict(self):
		return {c.name: getattr(self, c.name) for c in self.__table__.columns}
	

@app.route('/user/login', methods=['POST'])
def get_User():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		user = db.session.query(Users).filter_by(email=request.form.get('email')).filter_by(password=request.form.get('password')).first()
		if user:
			token = uuid.uuid4().hex
			user.token = token
			user.phone_id = request.form.get('phone_id')
			db.session.commit()
			return jsonify({'data': user.as_dict() ,'result' : { 'code' : 1 }})
		else:
			return jsonify({'result' : { 'msg': 'Wrong username or password' , 'code' : 2}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}}), 400

@app.route('/user/register', methods=['POST'])
def reg_User():
	try:
		if request.form.get('facebook_id') :
			#user try to login with facebook
			me = db.session.query(Users).filter_by(facebook_id=request.form.get('facebook_id')).first()
			if me:
				token = uuid.uuid4().hex
				me.token = token
				me.phone_id = request.form.get('phone_id')
				me.status = 'active'
				db.session.commit()
				return jsonify({'data': me.as_dict() ,'result' : { 'code' : 1 }})
			else :
				# need to register
				me = db.session.query(Users).filter_by(email=request.form.get('email')).first()
				if me:
					# found by email
					token = uuid.uuid4().hex
					me.token = token
					me.phone_id = request.form.get('phone_id')
					me.facebook_id = request.form.get('facebook_id')
					me.status = 'active'
					db.session.commit()
					return jsonify({'data': me.as_dict() ,'result' : { 'code' : 1 }})
				else :
					me = Users(request.form.get('name'), request.form.get('email'), request.form.get('password'))
					token = uuid.uuid4().hex
					me.token = token
					me.phone_id = request.form.get('phone_id')
					me.facebook_id = request.form.get('facebook_id')
					db.session.add(me)
					me.status = 'active'
					db.session.commit()
					result = me.as_dict()
					result['registered'] = 'true'
					return jsonify({'data': result ,'result' : { 'code' : 1 }})
		else :
			#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
			user = db.session.query(Users).filter_by(email=request.form.get('email')).first()
			if user:
				if user.status == "active":
					return jsonify({'result' : { 'msg': 'This email is allready registered' , 'code' : 2}})
				
				if user.status == "new":
					token = uuid.uuid4().hex
					user.token = token
					user.phone_id = request.form.get('phone_id')
					user.name=request.form.get('name')
					user.status="active"
					db.session.add(user)
					db.session.commit()
					result = user.as_dict()
					result['registered'] = 'true'
					return jsonify({'data': result ,'result' : { 'code' : 1 }})
			else:
				me = Users(request.form.get('name'), request.form.get('email'), request.form.get('password'))
				token = uuid.uuid4().hex
				me.token = token
				me.phone_id = request.form.get('phone_id')
				me.status="active"
				db.session.add(me)
				db.session.commit()
				result = me.as_dict()
				result['registered'] = 'true'
				return jsonify({'data': result ,'result' : { 'code' : 1 }})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}}), 400

@app.route('/user/update', methods=['POST'])
def update_User():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		user = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if user is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			if request.form.get('name'):
				user.name = request.form.get('name')
			if request.form.get('email'):
				user.email = request.form.get('email')
			if request.form.get('password'):
				user.password = request.form.get('password')
			if request.form.get('birthdate'):
				user.birthdate = request.form.get('birthdate')
			if request.form.get('gender'):
				user.gender = request.form.get('gender')
			if request.form.get('phone'):
				user.phone = request.form.get('phone')
			if request.form.get('location'):
				user.location  = request.form.get('location')
			if request.method == 'POST' and 'photo' in request.files:
				file = request.files['photo']
				if file and allowed_file(file.filename):
					# Make the filename safe, remove unsupported chars
					#filename = secure_filename(file.filename)
					filename, file_extension = os.path.splitext(file.filename)
					filename = str(user.id) + file_extension
					# Move the file form the temporal folder to
					# the upload folder we setup
					new_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
					file.save(new_path)
					user.photo = new_path
			db.session.commit()
			return jsonify({'data': user.as_dict() ,'result' : { 'code' : 1 }})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})

@app.route('/user/view', methods=['POST'])
def view_User():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			user = db.session.query(Users).filter_by(id=request.form.get('id')).first()
			if user is None:
				return jsonify({'result' : { 'code' : 2 , "msg" : "Wrong user id" }})
			else:
				return jsonify({'data': user.as_dict() ,'result' : { 'code' : 1 }})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/friends/add_friend', methods=['POST'])
def add_Friend():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			post_user_id = request.form.get('user_id')
			post_facebook_id = request.form.get('facebook_id')
			post_email = request.form.get('email')
			
			user = None
			if post_user_id:
				# search by user_id
				print ' search by user_id '
				user = db.session.query(Users).filter_by(id=post_user_id).first()
			
			if post_facebook_id and user is None:
				# search by facebook_id
				print ' search by facebook_id'
				user = db.session.query(Users).filter_by(facebook_id=post_facebook_id).first()
			
			if post_email and user is None:
				# search by email
				print ' search by email '
				user = db.session.query(Users).filter_by(email=post_email).first()
			
			if user is None:
				if post_email:
					msg = Message("hello", sender=(app.config['ADMIN_NAME'] , app.config['ADMIN_EMAIL'] ), recipients=[post_email])
					msg.html =  render_template("email.html", user_me=me)
					mail.send(msg)
					
					user = Users('', post_email, '')
					user.facebook_id = post_facebook_id
					user.status="new"
					db.session.add(user)
				else:
					return jsonify({'result' : { 'code' : 2 , 'msg' : 'User not found' }})
			
			friend_request = db.session.query(Friend_request).filter_by(from_id=me.id).filter_by(to_id=user.id).first()
			if friend_request != None:
				return jsonify({'result' : { 'code' : 3 , 'msg' : 'User already invited'}})
				
			friend_request = Friend_request(me.id , user.id)
			db.session.add(friend_request)
			
			arr = {'from_id' : me.id}
			notification = Notification('this is pur msf', 'friend_request', {'from_id' : me.id} , user.id)
			db.session.add(notification)
			
			db.session.commit()
			return jsonify({'result' : { 'code' : 1 , 'msg' : 'User invited'}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})

@app.route('/friends/get_friends', methods=['GET'])
def get_Friends():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			friends = [u.friend.as_dict() for u in db.session.query(User_friends).filter_by(user_id=me.id).all()]
			return jsonify({'data': friends , 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})

@app.route('/friends/search_friends', methods=['POST'])
def search_Friends():
	try:
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			friends = [u[1].as_dict() for u in db.session.query(User_friends, Users).join(Users, Users.id == User_friends.friend_id).filter(User_friends.user_id == me.id ).filter(Users.name.like('%' + request.form.get('name') + '%')).all()]
			return jsonify({'data': friends , 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})

@app.route('/users/search', methods=['POST'])
def search_Users():
	try:
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong 1' , 'code' : -1}})
		else:
			search_name = request.form.get('name')
			facebook_flague = request.form.get('facebook')
			limit = request.form.get('limit')
			offset = request.form.get('offset')
			
			if limit is None:
				limit = 50
			
			q = db.session.query(Users, Friend_request, User_friends).outerjoin(User_friends,and_( Users.id == User_friends.friend_id, User_friends.user_id == me.id)).\
																										outerjoin(Friend_request, and_(Users.id == Friend_request.to_id, Friend_request.from_id == me.id)).\
																										filter(Friend_request.id == None).\
																										filter(User_friends.id == None)
			if search_name:
				q = q.filter(Users.name.like('%' + search_name + '%'))
			
			if facebook_flague == "1":
				q = q.filter(Users.facebook_id.isnot(None))
			
			if facebook_flague == "2":
				q = q.filter(Users.facebook_id == None)
			
			users = [u[0].as_dict() for u in q.limit(limit).offset(offset)]
			
			return jsonify({'data': users , 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong 2' , 'code' : -1}})


@app.route('/friends/accept', methods=['POST'])
def accept_Friends():
	try:
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			friend_id = request.form.get('user_id')
			friend_request = db.session.query(Friend_request).filter_by(from_id=friend_id).filter_by(to_id=me.id).first()
			if friend_request:
				
				friendship = User_friends(friend_id, me.id)
				db.session.add(friendship)
				
				friendship = User_friends(me.id, friend_id)
				db.session.add(friendship)
				
				db.session.delete(friend_request)
				
				db.session.commit()
				return jsonify({'result' : { 'code' : 1 }})
			else:
				return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})

@app.route('/friends/reject', methods=['POST'])
def reject_Friend():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			user_id = request.form.get('user_id')
			
			friend_request = db.session.query(Friend_request).filter_by(from_id=user_id).filter_by(to_id=me.id).first()
			if friend_request:
				
				db.session.delete(friend_request)
				
				db.session.commit()
				return jsonify({'result' : { 'code' : 1 }})
			else:
				return jsonify({'result' : { 'msg': 'No request found' , 'code' : -1}})
				
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/friends/cancel', methods=['POST'])
def cancel_Friend_request():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			user_id = request.form.get('user_id')
			
			friend_request = db.session.query(Friend_request).filter_by(from_id=me.id).filter_by(to_id=user_id).first()
			if friend_request:
				
				db.session.delete(friend_request)
				
				db.session.commit()
				return jsonify({'result' : { 'code' : 1 }})
			else:
				return jsonify({'result' : { 'msg': 'No request found' , 'code' : -1}})
				
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/get_notifications', methods=['GET'])
def get_Notifications():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			notifications = []
			print me.id
			for u in db.session.query(Notification).filter_by(user_id=me.id).filter_by(status=0).all():
				notification = u.as_dict()
				notification['data'] = json.loads(notification['data'])
				notifications.append(notification)
				u.status = 1
			db.session.commit()	
			return jsonify({'data': notifications , 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/get_friend_requests', methods=['GET'])
def get_Friend_Requests():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			incoming = []
			for u in db.session.query(Friend_request, Users).join(Users, Users.id == Friend_request.from_id).filter(Friend_request.to_id==me.id).all():
				tmp = u[1].as_dict()
				tmp['date'] = u[0].date
				incoming.append(tmp)
				
			outcoming = []
			for u in db.session.query(Friend_request, Users).join(Users, Users.id == Friend_request.to_id).filter(Friend_request.from_id==me.id).all():
				tmp = u[1].as_dict()
				tmp['date'] = u[0].date
				outcoming.append(tmp)
				
			return jsonify({'data': {'incoming' : incoming, 'outcoming' : outcoming} , 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/events/add_event', methods=['POST'])
def add_Event():
	try:
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			lat = request.form.get('lat')
			long = request.form.get('long')
			location = request.form.get('location')
			date = request.form.get('date')
			time = request.form.get('time')
			type = request.form.get('type')
			notes = request.form.get('notes')
			category = request.form.get('category')
			
			event = Events(me.id )
			
			event.lat = lat
			event.long = long
			event.location = location
			event.date = datetime.strptime(date, '%m-%d-%Y %H:%M')
			event.type = type
			
			event.notes = notes
			event.category = category
			
			db.session.add(event)
			db.session.commit()
			
			if request.method == 'POST' and 'picture' in request.files:
				file = request.files['picture']
				if file and allowed_file(file.filename):
					# Make the filename safe, remove unsupported chars
					#filename = secure_filename(file.filename)
					filename, file_extension = os.path.splitext(file.filename)
					filename = str(event.id) + file_extension
					# Move the file form the temporal folder to
					# the upload folder we setup
					new_path = os.path.join(app.config['UPLOAD_EVENTS_FOLDER'], filename)
					file.save(new_path)
					event.picture = new_path
			
			db.session.commit()
			return jsonify({'result' : { 'code' : 1 , 'msg' : 'Event added'}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		

@app.route('/events/edit_event', methods=['POST'])
def edit_Event():
	try:
		print request.form.get('token')
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong 1' , 'code' : -1}})
		event = db.session.query(Events).filter_by(id=request.form.get('event_id')).first()
		
		if event != None and event.user_id == me.id:
			lat = request.form.get('lat')
			long = request.form.get('long')
			location = request.form.get('location')
			date = request.form.get('date')
			time = request.form.get('time')
			type = request.form.get('type')
			notes = request.form.get('notes')
			category = request.form.get('category')
			print category
			if (lat):
				event.lat = lat
			if (long):
				event.long = long
			if (location):
				event.location = location
			if (date):
				event.date = datetime.strptime(date, '%m-%d-%Y %H:%M')
			if (type):
				event.type = type
			
			if (notes):
				event.notes = notes
			if (category):
				event.category = category
			
			if request.method == 'POST' and 'picture' in request.files:
				file = request.files['picture']
				if file and allowed_file(file.filename):
					# Make the filename safe, remove unsupported chars
					#filename = secure_filename(file.filename)
					filename, file_extension = os.path.splitext(file.filename)
					filename = str(event.id) + file_extension
					# Move the file form the temporal folder to
					# the upload folder we setup
					new_path = os.path.join(app.config['UPLOAD_EVENTS_FOLDER'], filename)
					file.save(new_path)
					event.picture = new_path
			
			db.session.commit()
			return jsonify({'result' : { 'code' : 1 , 'msg' : 'Event saved'}})
			
		return jsonify({'result' : { 'msg': 'Event not found' , 'code' : -1}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong 2' , 'code' : -1}})
		

@app.route('/events/delete_event', methods=['GET'])
def delete_Event():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event = db.session.query(Events).filter_by(id=request.args.get('id')).first()
			
			if event != None and event.user_id == me.id:
				db.session.delete(event)
				db.session.commit()
				return jsonify({'result' : { 'code' : 1 , "msg" : "Event deleted"}})
				
			return jsonify({'result' : { 'msg': 'Event not found' , 'code' : -1}})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})

		

@app.route('/events/get_events', methods=['GET'])
def get_Events():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			s_lat = float(request.args.get('lat'))
			s_long = float(request.args.get('long'))
			s_type =request.args.get('type')
			radius = float(request.args.get('radius'))
			full = request.args.get('full')
			location = request.args.get('location')
			category = request.args.get('category')
			
			yesterday = datetime.now() - timedelta(days=1)
			
			if (s_type == "public"):
				events = []
				q = db.session.query(Events, Users).join(Users, Users.id == Events.user_id).filter(Events.lat>=s_lat-5).\
																										filter(Events.lat<=s_lat+5).\
																										filter(Events.long<=s_long+5).\
																										filter(Events.type=="public").\
																										filter(Events.date>=yesterday).\
																										filter(Events.long<=s_long+5)
				if location:
					q = q.filter(Events.location.like('%' + location + '%'))
				if category:
					q = q.filter(Events.category == category)
				for u in q.all():
					arr = u[0].as_dict()
					if full != "1":
						# all except mine and my attends
						if arr['user_id'] != me.id :
							my_attend = db.session.query(Event_attends.id).filter_by(event_id=arr['id']).filter_by(user_id=me.id).count();
							if my_attend == 0:
								arr['user'] = u[1].as_dict();
								arr['attends'] = db.session.query(Event_attends.id).filter_by(event_id=arr['id']).count();
								arr['date'] = datetime.strftime(arr['date'], '%m-%d-%Y %H-%M')
								events.append(arr);
					else:
						# all
						arr['user'] = u[1].as_dict();
						arr['attends'] = db.session.query(Event_attends.id).filter_by(event_id=arr['id']).count();
						arr['date'] = datetime.strftime(arr['date'], '%m-%d-%Y %H-%M')
						events.append(arr);
					
				for event in events:
					dist = haversine(float(event['long']), float(event['lat']), s_long, s_lat)
					if (dist > radius):
						events.remove(event)
				return jsonify({'data': events, 'result' : { 'code' : 1 }})
			else:
				event_requests = []
				
				for u in db.session.query(Event_requests).filter_by(user_id=me.id).all():
					event_requests.append(u.event_id)
				
				events = []
				q = db.session.query(Events, Users).join(Users, Users.id == Events.user_id).filter(Events.lat>=s_lat-5).\
																										filter(Events.lat<=s_lat+5).\
																										filter(Events.long<=s_long+5).\
																										filter(Events.long<=s_long+5).\
																										filter(Events.type=="private").\
																										filter(Events.date>=yesterday).\
																										filter(Events.id.in_(event_requests))
				if location:
					q = q.filter(Events.location.like('%' + location + '%'))
				if category:
					q = q.filter(Events.category == category)
					
				for u in q.all():
					arr = u[0].as_dict()
					arr['user'] = u[1].as_dict();
					arr['attends'] = db.session.query(Event_attends.id).filter_by(event_id=arr['id']).count();
					arr['date'] = datetime.strftime(arr['date'], '%m-%d-%Y %H-%M')
					events.append(arr);
					
				for event in events:
					dist = haversine(float(event['long']), float(event['lat']), s_long, s_lat)
					print dist
					if (dist > radius):
						events.remove(event)
				return jsonify({'data': events, 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})



@app.route('/events/get_my_events', methods=['GET'])
def get_my_Events():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			events = []
			yesterday = datetime.now() - timedelta(days=1)
			for u in db.session.query(Events).filter_by(user_id=me.id).filter(Events.date>=yesterday).all():
				arr = u.as_dict()
				arr['user'] = me.as_dict();
				arr['attends'] = db.session.query(Event_attends.id).filter_by(event_id=arr['id']).count();
				arr['date'] = datetime.strftime(arr['date'], '%m-%d-%Y %H-%M')
				events.append(arr);
				
			
			return jsonify({'data': events, 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/events/get_user_events', methods=['GET'])
def get_user_Events():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			events = []
			user_id = token=request.args.get('user_id');
			yesterday = datetime.now() - timedelta(days=1)
			for u in db.session.query(Events).filter_by(user_id=user_id).filter(Events.date>=yesterday).all():
				arr = u.as_dict()
				arr['user'] = me.as_dict();
				arr['attends'] = db.session.query(Event_attends.id).filter_by(event_id=arr['id']).count();
				arr['date'] = datetime.strftime(arr['date'], '%m-%d-%Y %H-%M')
				events.append(arr);
				
			
			return jsonify({'data': events, 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/events/get_friends_events', methods=['GET'])
def get_friends_Events():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			events = []
			friends_ids = []
				
			for u in db.session.query(User_friends).filter_by(user_id=me.id).all():
				friends_ids.append(u.friend_id)
			
			yesterday = datetime.now() - timedelta(days=1)
			for u in db.session.query(Events, Users).join(Users, Users.id == Events.user_id).filter(Events.user_id.in_(friends_ids)).filter(Events.date>=yesterday).all():
				arr = u[0].as_dict()
				arr['user'] = u[1].as_dict();
				arr['attends'] = db.session.query(Event_attends.id).filter_by(event_id=arr['id']).count();
				arr['date'] = datetime.strftime(arr['date'], '%m-%d-%Y %H-%M')
				events.append(arr);
				
			
			return jsonify({'data': events, 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})

@app.route('/events/get_one_event', methods=['GET'])
def get_One_Event():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event = db.session.query(Events, Users).join(Users, Users.id == Events.user_id).filter(Events.id==request.args.get('id')).first()
			if event is None:
				return jsonify({'result' : { 'msg': 'Event not found' , 'code' : -1}})
			dict_event = event[0].as_dict()
			dict_event['user'] = event[1].as_dict()
			dict_event['attends'] = db.session.query(Event_attends.id).filter_by(event_id=dict_event['id']).count();
			dict_event['date'] = datetime.strftime(dict_event['date'], '%m-%d-%Y %H-%M')
			return jsonify({'data': dict_event, 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/events/get_friends', methods=['GET'])
def get_Friends_Event():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event_id = request.args.get('event_id')
			
			friends = [u.friend.as_dict() for u in db.session.query(User_friends).filter_by(user_id=me.id).all()]
			for friend in friends:
				friend['invited'] = db.session.query(Event_requests).filter_by(event_id=event_id).filter_by(user_id=friend['id']).count();
				if friend['invited'] == 0:
					friend['invited'] = db.session.query(Event_attends).filter_by(event_id=event_id).filter_by(user_id=friend['id']).count();
				
			return jsonify({'data': friends, 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/events/invite_friend', methods=['POST'])
def invite_Friend():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			user_id = request.form.get('user_id')
			event_id = request.form.get('event_id')
			
			user = db.session.query(Users).filter_by(id=user_id).first()
			event = db.session.query(Events).filter_by(id=event_id).first()
			
			if user is None:
				return jsonify({'result' : { 'msg': 'User not found' , 'code' : -1}})
				
			if event is None:
				return jsonify({'result' : { 'msg': 'Event not found' , 'code' : -1}})
			
			event_request = db.session.query(Event_requests).filter_by(user_id=user.id).filter_by(event_id=event.id).first()
			if event_request != None:
				return jsonify({'result' : { 'code' : 2 , 'msg' : 'User already invited'}})
				
			event_request = Event_requests(user.id , event.id, me.id)
			db.session.add(event_request)
			
			db.session.commit()
			return jsonify({'result' : { 'code' : 1 , 'msg' : 'User invited'}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/events/get_invitations', methods=['GET'])
def get_Invitations():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event_requests = []
			for u in db.session.query(Event_requests, Events, Users).join(Events, Events.id == Event_requests.event_id).join(Users, Users.id == Events.user_id).filter(Event_requests.user_id==me.id).filter(Events.date>=datetime.now()).all():
				arr = u[1].as_dict();
				arr['user'] = u[2].as_dict();
				event_requests.append(arr);
				
			return jsonify({'data' : event_requests,  'result' : { 'code' : 1 }})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/events/accept_invitation', methods=['POST'])
def accept_Invitation():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event_id = request.form.get('event_id')
			event = db.session.query(Events).filter_by(id=event_id).first()
			
			if event is None:
				return jsonify({'result' : { 'msg': 'Event not found' , 'code' : -1}})
			
			event_request = db.session.query(Event_requests).filter_by(user_id=me.id).filter_by(event_id=event.id).first()
			if event_request is None:
				return jsonify({'result' : { 'msg': 'Request not found' , 'code' : -1}})
				
			event_attend = Event_attends(me.id, event.id )
			db.session.add(event_attend)
			db.session.delete(event_request)
			
			db.session.commit()
			return jsonify({'result' : { 'code' : 1 , 'msg' : 'OK'}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})

@app.route('/events/reject_invitation', methods=['POST'])
def reject_Invitation():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event_id = request.form.get('event_id')
			event = db.session.query(Events).filter_by(id=event_id).first()
			
			if event is None:
				return jsonify({'result' : { 'msg': 'Event not found' , 'code' : -1}})
			
			event_request = db.session.query(Event_requests).filter_by(user_id=me.id).filter_by(event_id=event.id).first()
			if event_request is None:
				return jsonify({'result' : { 'msg': 'Request not found' , 'code' : -1}})
				
			
			db.session.delete(event_request)
			
			db.session.commit()
			return jsonify({'result' : { 'code' : 1 , 'msg' : 'OK'}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})



@app.route('/events/get_attending', methods=['GET'])
def get_Attending():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event_id = request.args.get('event_id');
			
			users = [u[1].as_dict() for u in db.session.query(Event_attends, Users).join(Users).filter(Users.id == Event_attends.user_id).filter(Event_attends.event_id==event_id).all()]
			
			return jsonify({'data': users, 'result' : { 'code' : 1 }})
			
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})

@app.route('/events/will_attend', methods=['POST'])
def will_Attend():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event_id = request.form.get('event_id')
			event = db.session.query(Events).filter_by(id=event_id).first()
			
			if event is None:
				return jsonify({'result' : { 'msg': 'Event not found' , 'code' : -1}})
			
			event_attend = db.session.query(Event_attends).filter_by(user_id=me.id).filter_by(event_id=event.id).first()
			if event_attend is None:
				event_attend = Event_attends(me.id, event.id )
				event_attend.lat = request.form.get('lat')
				event_attend.long = request.form.get('long')
				event_attend.status = 'will'
				event_attend.date = datetime.now()
				db.session.add(event_attend)
			else:
				event_attend.lat = request.form.get('lat')
				event_attend.long = request.form.get('long')
				event_attend.status = 'will'
				event_attend.date = datetime.now()
			
			db.session.commit()
			return jsonify({'result' : { 'code' : 1 , 'msg' : 'OK'}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/events/did_attend', methods=['POST'])
def did_Attend():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event_id = request.form.get('event_id')
			event = db.session.query(Events).filter_by(id=event_id).first()
			
			if event is None:
				return jsonify({'result' : { 'msg': 'Event not found' , 'code' : -1}})
			
			event_attend = db.session.query(Event_attends).filter_by(user_id=me.id).filter_by(event_id=event.id).first()
			if event_attend is None:
				event_attend = Event_attends(me.id, event.id )
				event_attend.lat = request.form.get('lat')
				event_attend.long = request.form.get('long')
				event_attend.status = 'did'
				event_attend.date = datetime.now()
				db.session.add(event_attend)
			else:
				event_attend.lat = request.form.get('lat')
				event_attend.long = request.form.get('long')
				event_attend.status = 'did'
				event_attend.date = datetime.now()
			
			db.session.commit()
			return jsonify({'result' : { 'code' : 1 , 'msg' : 'OK'}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/user/attends', methods=['POST'])
def user_Attends():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.form.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			yesterday = datetime.now() - timedelta(days=1)
			user_id = request.form.get('user_id')
			
			event_attends = []
			for u in db.session.query(Event_attends, Events).join(Events, Events.id==Event_attends.event_id).filter(Event_attends.user_id==user_id).filter(Event_attends.date>=yesterday).all():
				arr = u[0].as_dict();
				arr['event'] = u[1].as_dict();
				event_attends.append(arr)
				
			return jsonify({'data' : event_attends, 'result' : { 'code' : 1 , 'msg' : 'OK'}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/user/my_attends', methods=['GET'])
def my_Attends():
	try:
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event_attends = []
			for u in db.session.query(Event_attends, Events).join(Events, Events.id==Event_attends.event_id).filter(Event_attends.user_id==me.id).filter(Events.date>=datetime.now()).all():
				arr = u[0].as_dict();
				arr['event'] = u[1].as_dict();
				event_attends.append(arr)
				
			return jsonify({'data' : event_attends, 'result' : { 'code' : 1 , 'msg' : 'OK'}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


@app.route('/events/remove_attend', methods=['GET'])
def remove_Attend():
	try:
		#user = Users.query.filter_by(username=request.form.get('username')).filter_by(password=request.form.get('password')).first();
		me = db.session.query(Users).filter_by(token=request.args.get('token')).first()
		if me is None:
			return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})
		else:
			event_id = request.args.get('event_id');
			event_attend = db.session.query(Event_attends).filter_by(user_id=me.id).filter_by(event_id=event_id).first()
			if event_attend is None:
				return jsonify({'result' : { 'msg': 'No event found' , 'code' : -1}})
			
			db.session.delete(event_attend)
			db.session.commit()
			
			return jsonify({'result' : { 'code' : 1 , 'msg' : 'OK'}})
	except IntegrityError:
		return jsonify({'result' : { 'msg': 'Something went wrong' , 'code' : -1}})


		
@app.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)		

@app.route('/uploads/events/<filename>', methods=['GET'])
def uploaded_file_events(filename):
    return send_from_directory(app.config['UPLOAD_EVENTS_FOLDER'],
                               filename)

def haversine(lon1, lat1, lon2, lat2):
	R = 3.959
	x = (lon2 - lon1) * cos( 0.5*(lat2+lat1) )
	y = lat2 - lat1
	d = R * sqrt( x*x + y*y )
	return d
	
if __name__ == "__main__":
	app.debug = True;
	app.run(host= '178.62.143.179')
