import re
from flask import Flask, render_template, g, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import os

app = Flask(__name__)
app.config.from_pyfile('config.cfg')
app.config['SECRET_KEY'] = os.urandom(24)

db = SQLAlchemy(app)

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'GET':
        users = Users.query.order_by(Users.firstname).all()
        return render_template('home.html', users=users)
    
    if request.method == 'POST':
        if request.form['find_user'] == '' or request.form['find_user'] == None:
            users = Users.query.order_by(Users.firstname).all()
            return render_template('home.html', users=users)
        else:
            find_user = request.form['find_user']
            users = Users.query.order_by(Users.firstname).filter(Users.username.like("%" + find_user + "%")).all()

            if users:
                return render_template('home.html', users=users)
            else:
                return render_template('home.html', error="No users found")

@app.route('/register', methods=['GET', 'POST'])
def register():
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    if request.method == 'POST':
        # check if username is unique
        if (Users.query.filter(func.lower(Users.username) == func.lower(request.form['username'])).count() >= 1):
            return render_template('register.html', error="Username already in use!")

        # check if email is unique
        if (Emaildb.query.filter(func.lower(Emaildb.email) == func.lower(request.form['email'])).count() >= 1):
            return render_template('register.html', error="Email is already in use!")
        
        if request.form['username'] == "" or request.form['firstname'] == "" or request.form['lastname'] == "" or request.form['email'] == "":
            return render_template('register.html', error="Please fill in all fields for registration!")
        
        if not(re.fullmatch(regex, request.form['email'])):
            return render_template('register.html', error="Please enter a valid e-mail!")

        user = Users(username = request.form['username'], firstname=request.form['firstname'], lastname=request.form['lastname'])
        db.session.add(user)
        db.session.commit()
        user_new = Users.query.filter(Users.username == user.username).one()
        email = Emaildb(email = request.form['email'], user_id=user_new.id)
        db.session.add(email)
        db.session.commit()
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/edit/<user_id>/<delete>', methods=['GET', 'POST'])
@app.route('/edit/<user_id>', methods=['GET', 'POST'], defaults={'delete': False})
def edit(user_id,delete):
    user=Users.query.filter(Users.id == user_id).first()

    print(request.method)
    print(delete)

    if delete:
        user=Users.query.filter(Users.id == user_id).first()
        emails=Emaildb.query.filter(Emaildb.user_id == user_id).all()
        db.session.delete(user)
        for email in emails:
            db.session.delete(email)
        db.session.commit()
        return render_template("edit.html", delete=delete, error="User \"{}\" deleted!".format(user.username))

    if request.method == "GET" and not(delete):
        return render_template('edit.html', user=user)

    if request.method == "POST":
        if (Users.query.filter(func.lower(Users.username) == func.lower(request.form['username'])).count() >= 1) and (user.username != request.form['username']):
            return render_template('edit.html', user=user, error="Username already in use!")
        
        if request.form['username'] == "" or request.form['firstname'] == "" or request.form['lastname'] == "":
            return render_template('edit.html', user=user, error="No fields should be left blank!")

        user.username = request.form['username']
        user.firstname = request.form['firstname']
        user.lastname = request.form['lastname']
        db.session.commit()
        return render_template('edit.html', user=user)

#============================================================================
#                           EDIT EMAILS PAGE
#============================================================================
@app.route('/editemail/<user_id>/<delete_email>', methods=['GET', 'POST'])
@app.route('/editemail/<user_id>', methods=['GET', 'POST'], defaults={'delete_email': ''})
def editemail(user_id,delete_email):
    user=Users.query.filter(Users.id == user_id).first()
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    if not(delete_email == '' or delete_email == None):
        if Emaildb.query.filter(Emaildb.user_id == user_id).count() > 1:
            email=Emaildb.query.filter(Emaildb.email == delete_email).one()
            db.session.delete(email)
            db.session.commit()
            return render_template("editemail.html", user=user, user_id=user_id, error="Email \"{}\" deleted!".format(email.email))
        
        return render_template("editemail.html", user=user, user_id=user_id, error="User must have at least one e-mail")

    if request.method == 'GET':
        return render_template('editemail.html', user=user)

    if request.method == 'POST':
        if request.form['email'] == '' or request.form['email'] == None:
            return render_template('editemail.html', user=user)

        if not(re.fullmatch(regex, request.form['email'])):
            return render_template('editemail.html', user=user, error="Please enter a valid e-mail!")

        if (Emaildb.query.filter(func.lower(Emaildb.email) == func.lower(request.form['email'])).count() >= 1):
            print(request.form['email'])
            return render_template('editemail.html', user=user, error="Email is already in use!")

        addEmail = Emaildb(email=request.form['email'], user_id=user_id)
        db.session.add(addEmail)
        db.session.commit()
        return render_template('editemail.html', user=user)

#==============================================================================
#                           DEFINITION OF THE TABLES
#==============================================================================
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    firstname = db.Column(db.String(80), nullable=False)
    lastname = db.Column(db.String(80), nullable=False)
    emails = db.relationship('Emaildb', backref='users', lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % self.username

class Emaildb(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
#==============================================================================
if __name__ == '__main__':
    app.run()