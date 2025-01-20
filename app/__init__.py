from flask import Flask, render_template
from config import Config
from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import LoginManager
from flask_migrate import Migrate
# from app.api import bp as api_bp
# from app import routes
# from app import routes, models, errors
# from app.models import db


# Initialize the database and login manager
db = SQLAlchemy()
login = LoginManager()
migrate = Migrate()

def nl2br_filter(text):
    return text.replace('\n', '<br>\n')

def create_app(config_class=Config):
    # Create the App context
    app = Flask(__name__)

    basedir = os.path.abspath(os.path.dirname(__file__))

    # Configure SQLite database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+os.path.join(basedir, 'movies.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.from_object(Config)


    # Set up Flask-Login
    app.config['SECRET_KEY'] = 'your-secret-key' 
    login.init_app(app)
    login.login_view = 'login' 

    # Initialize the database
    db.init_app(app)

    # Set up migrations with Flask-Migrate
    migrate.init_app(app, db)

    # Register the custom filter for nl2br
    app.jinja_env.filters['nl2br'] = nl2br_filter

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500
    
    with app.app_context():
        from .models import Post
        db.create_all()

    from .routes import init_routes
    init_routes(app)
    
    return app

