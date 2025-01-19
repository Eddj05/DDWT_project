from flask import Flask
from app import create_app

# Maak een app-instantie met behulp van de create_app-functie
app = create_app()

if __name__ == "__main__":
    # Start de Flask-app in debug-modus
    app.run(debug=True)