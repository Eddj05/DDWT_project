from flask import Flask
from app import create_app

# Make an app-instance with the create_app-function
app = create_app()

if __name__ == "__main__":
    # Start the Flask-app in debug-mode
    app.run(debug=True)