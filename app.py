from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from check import notemail
import os

app = Flask(__name__)
app.config.from_pyfile('config.cfg')
app.config['SECRET_KEY'] = os.urandom(24)

db = SQLAlchemy(app)

#============================================================================
#                           INDEX/HOME PAGE
#============================================================================
@app.route('/', methods=['GET', 'POST'])
def index():
    sel1 = sel2 = ""
    page = request.args.get('page', 1, type=int)
    per_page = 8

    if request.method == 'GET':
        sel1 = "selected"
        
        users = Users.query.order_by(func.lower(Users.firstname)).paginate(page=page,per_page=per_page)
        print(users.per_page)

        #users = Users.query.order_by(func.lower(Users.firstname)).all()
        return render_template('home.html', sel1=sel1, sel2=sel2, users=users)
    
    if request.method == 'POST':
        if request.form['search_by'] == '1':
            sel1 = "selected"
        if request.form['search_by'] == '2':
            sel2 = "selected"

        if request.form['find_user'] == '' or request.form['find_user'] == None:
            users = Users.query.order_by(func.lower(Users.firstname)).paginate(page=page,per_page=per_page)
            return render_template('home.html', sel1=sel1, sel2=sel2, search_val=request.form['search_by'], old_srch = request.form['find_user'], users=users)
        else:
            find_user = request.form['find_user']
            if request.form['search_by'] == '1':
                users = Users.query.order_by(func.lower(Users.firstname)).filter(Users.username.like("%" + find_user + "%")).paginate(page=page,per_page=per_page)
            
            if request.form['search_by'] == '2':
                subquery = db.session.query(Emaildb.user_id).filter(Emaildb.email.like("%" + find_user + "%")).subquery()
                users = db.session.query(Users).order_by(func.lower(Users.firstname)).filter(Users.id.in_(subquery)).paginate(page=page,per_page=per_page)
                
            if users:
                return render_template('home.html', sel1=sel1, sel2=sel2, search_val=request.form['search_by'], old_srch = request.form['find_user'], users=users)
            else:
                return render_template('home.html', sel1=sel1, sel2=sel2, search_val=request.form['search_by'], error="No users found")

#============================================================================
#                           REGISTER USER PAGE
#============================================================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    
    if request.method == 'GET':
        return render_template('register.html')

    if request.method == 'POST':
        error = None
        # check if username is unique
        if (Users.query.filter(func.lower(Users.username) == func.lower(request.form['username'])).count() >= 1):
            error="Username already in use!"

        if (' ' in request.form['username']):
            error="Username shouldn't have spaces!"

        # check if email is unique
        if (Emaildb.query.filter(func.lower(Emaildb.email) == func.lower(request.form['email'])).count() >= 1):
            error="Email is already in use!"
        
        if request.form['username'] == "" or request.form['firstname'] == "" or request.form['lastname'] == "" or request.form['email'] == "":
            error="Please fill in all fields for registration!"
        
        if notemail(request.form['email']):
            error="Please enter a valid e-mail!"
        
        if error:
            return render_template('register.html', \
                                    prev_user = request.form['username'], prev_first = request.form['firstname'], \
                                    prev_last = request.form['lastname'], prev_email = request.form['email'], \
                                    error = error)
        else:     
            user = Users(username = request.form['username'], firstname=request.form['firstname'], lastname=request.form['lastname'])
            db.session.add(user)
            db.session.commit()
            user_new = Users.query.filter(Users.username == user.username).one()
            email = Emaildb(email = request.form['email'], user_id=user_new.id)
            db.session.add(email)
            db.session.commit()
            return redirect(url_for('index'))

#============================================================================
#                           EDIT USER PAGE
#============================================================================
@app.route('/edit/<user_id>/<do_delete>', methods=['GET', 'POST'])
@app.route('/edit/<user_id>', methods=['GET', 'POST'], defaults={'do_delete': False})
def edit(user_id,do_delete):
    user=Users.query.filter(Users.id == user_id).first()

    if do_delete:
        user=Users.query.filter(Users.id == user_id).first()
        emails=Emaildb.query.filter(Emaildb.user_id == user_id).all()
        db.session.delete(user)
        for email in emails:
            db.session.delete(email)
        db.session.commit()
        return render_template("edit.html", do_delete=do_delete, error="User \"{}\" deleted!".format(user.username))

    if request.method == "GET" and not(do_delete):
        return render_template('edit.html', user=user)

    if request.method == "POST":
        if request.form['firstname'] == "" or request.form['lastname'] == "":
            return render_template('edit.html', user=user, error="No fields should be left blank!")

        user.firstname = request.form['firstname']
        user.lastname = request.form['lastname']
        db.session.commit()
        return render_template('edit.html', user=user)

#============================================================================
#                           EMAIL CONTROL PAGE
#============================================================================
@app.route('/emailcontrol/<user_id>/<delete_email>', methods=['GET', 'POST'])
@app.route('/emailcontrol/<user_id>', methods=['GET', 'POST'], defaults={'delete_email': ''})
def emailcontrol(user_id,delete_email):
    user=Users.query.filter(Users.id == user_id).first()
    
    if not(delete_email == '' or delete_email == None):
        if Emaildb.query.filter(Emaildb.user_id == user_id).count() > 1:
            email=Emaildb.query.filter(Emaildb.email == delete_email).one()
            db.session.delete(email)
            db.session.commit()
            return render_template("emailcontrol.html", user=user, user_id=user_id, error="Email \"{}\" deleted!".format(email.email))
        
        return render_template("emailcontrol.html", user=user, user_id=user_id, error="User must have at least one e-mail")

    if request.method == 'GET':
        return render_template('emailcontrol.html', user=user)

    if request.method == 'POST':
        if request.form['email'] == '' or request.form['email'] == None:
            return render_template('emailcontrol.html', user=user)

        if notemail(request.form['email']):
            return render_template('emailcontrol.html', user=user, old_email=request.form['email'], error="Please enter a valid e-mail!")

        if (Emaildb.query.filter(func.lower(Emaildb.email) == func.lower(request.form['email'])).count() >= 1):
            return render_template('emailcontrol.html', user=user, old_email=request.form['email'], error="Email is already in use!")

        addEmail = Emaildb(email=request.form['email'], user_id=user_id)
        db.session.add(addEmail)
        db.session.commit()
        return render_template('emailcontrol.html', user=user)

#============================================================================
#                           EMAIL EDIT PAGE
#============================================================================
@app.route('/editemail/<user_id>/<edit_email>', methods=['GET', 'POST'])
def editemail(user_id,edit_email):
    user=Users.query.filter(Users.id == user_id).first()
    email = Emaildb.query.filter(Emaildb.id == edit_email).one()
    the_email = email.email

    if request.method == 'GET':
        return render_template('editemail.html', the_email=the_email, user=user, email=email)

    if request.method == 'POST':
        if notemail(request.form['email']) or request.form['email'] == '' or request.form['email'] == None:
            return render_template('editemail.html', the_email=the_email, user=user, email=email, error="Please enter a valid e-mail!")

        if ((Emaildb.query.filter(func.lower(Emaildb.email) == func.lower(request.form['email'])).count() >= 1) and (not(str.lower(the_email) == str.lower(request.form['email'])))):
            return render_template('editemail.html', the_email=the_email, user=user, email=email, error="Email is already in use!")

        email.email = request.form['email']
        db.session.commit()
        return render_template('emailcontrol.html', user=user)

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
    email = db.Column(db.String(120), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
#==============================================================================
if __name__ == '__main__':
    app.run()