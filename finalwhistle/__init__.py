import os
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_login import LoginManager

# Create server and configure
app = Flask(__name__)
app.debug = True
# CHANGE IN PRODUCTION
app.config['SERVER_NAME'] = '127.0.0.1:5000'
app.config['PREFERRED_URL_SCHEME'] = 'http'
app.config['BASEDIR'] = os.path.dirname(os.path.realpath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.config['BASEDIR'], 'test.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Try to fetch secret key from OS
try:
    app.config['SECRET_KEY'] = os.environ['FINALWHISTLE_SECRET_KEY']
except KeyError:
    # If cannot find secret key, exit unless in debug mode
    if app.debug:
        app.config['SECRET_KEY'] = 'debug-key'
    else:
        print('Trying to run outside of debug mode without OS provided secret key, exiting')
        exit(1)


# flask-mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.environ['FLASK_MAIL_USERNAME']
app.config['MAIL_DEFAULT_SENDER'] = os.environ['FLASK_MAIL_DEFAULT_SENDER']
app.config['MAIL_PASSWORD'] = os.environ['FLASK_MAIL_PASSWORD']

# Initialise Flask extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)
login = LoginManager(app)



# tell flask_login which view to redirect users to when they need to log in
login.login_view = 'login'

@login.user_loader
def load_user(user_id):
    from finalwhistle.models.user import get_user_by_id
    return get_user_by_id(user_id)

# Register url routes with app object [1]
# [1]: http://flask.pocoo.org/docs/0.12/patterns/packages/#simple-packages
import finalwhistle.views.account
import finalwhistle.views.admin
import finalwhistle.views.data_views
import finalwhistle.views.misc

# Import all models to ensure they're loaded
# This shouldn't be required later on once all models are referenced in other parts of the app
# but for creating and testing a db, this works for now
import finalwhistle.models.user
import finalwhistle.models.comment
import finalwhistle.models.user
import finalwhistle.models.article
import finalwhistle.models.football
import finalwhistle.models.contact


# http://flask.pocoo.org/docs/0.12/templating/#context-processors
# Returns the current year
@app.context_processor
def current_year():
    import datetime
    now = datetime.datetime.now()
    return dict(current_year=now.year)

@app.context_processor
def utility_processor():
    def max_number(numbers):
        return max(numbers)
    return dict(max_number=max_number)


@app.context_processor
def rename_me():
    def user_name_from_id(id):
        from finalwhistle.models.user import get_user_by_id
        return get_user_by_id(id).name
    return dict(user_name_from_id=user_name_from_id)
