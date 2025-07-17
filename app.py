from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from calendar import monthrange
import requests
import os
from dotenv import load_dotenv

load_dotenv('Weather_API_Key.env')

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notion.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')
db = SQLAlchemy(app)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)

class WeeklyPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20))
    task = db.Column(db.String(200))

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(200))
    priority = db.Column(db.String(20))

with app.app_context():
    db.create_all()

def get_weather():
    try:
        api_key = os.getenv('WEATHER_API_KEY')
        if not api_key:
            return {'temp': 'N/A', 'condition': 'API key missing', 'location': 'Unknown'}

        location = session.get('location', 'Auckland')
        response = requests.get(
            f"http://api.openweathermap.org/data/2.5/weather?q={location}&units=metric&appid={api_key}"
        )
        response.raise_for_status()
        data = response.json()

        return {
            'temp': round(data['main']['temp'], 1),
            'condition': data['weather'][0]['description'].capitalize(),
            'icon': data['weather'][0]['icon'],
            'location': location,
            'feels_like': round(data['main']['feels_like'], 1),
            'humidity': data['main']['humidity'],
            'wind': round(data['wind']['speed'], 1)
        }
    except Exception as e:
        print(f"Weather API error: {e}")
        return {'temp': 'N/A', 'condition': 'Service unavailable', 'location': 'Unknown'}

def get_progress():
    today = datetime.now()
    start_of_year = datetime(today.year, 1, 1)
    start_of_month = datetime(today.year, today.month, 1)
    start_of_week = today - timedelta(days=today.weekday())

    total_days_year = (datetime(today.year + 1, 1, 1) - start_of_year).days
    total_days_month = monthrange(today.year, today.month)[1]
    total_days_week = 7

    passed_year = (today - start_of_year).days + 1
    passed_month = (today - start_of_month).days + 1
    passed_week = (today - start_of_week).days + 1

    return {
        'year': {'total': total_days_year, 'passed': passed_year},
        'month': {'total': total_days_month, 'passed': passed_month},
        'week': {'total': total_days_week, 'passed': passed_week},
    }

@app.route('/')
def index():
    weather = get_weather()
    progress = get_progress()
    weekly = WeeklyPlan.query.all()
    PRIORITY_ORDER = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
    todos = sorted(Todo.query.all(), key=lambda x: PRIORITY_ORDER.get(x.priority, 4))
    notes = Note.query.all()
    return render_template('index.html',
                         weather=weather,
                         progress=progress,
                         weekly=weekly,
                         todos=todos,
                         notes=notes,
                         current_location=session.get('location', 'Auckland'))

@app.route('/set_location', methods=['POST'])
def set_location():
    session['location'] = request.form['location']
    return redirect(url_for('index'))

@app.route('/add_note', methods=['POST'])
def add_note():
    title = request.form['title']
    content = request.form['content']
    db.session.add(Note(title=title, content=content))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit_note/<int:id>')
def edit_note(id):
    note = Note.query.get_or_404(id)
    return render_template('edit.html', note=note)

@app.route('/update_note/<int:id>', methods=['POST'])
def update_note(id):
    note = Note.query.get_or_404(id)
    note.title = request.form['title']
    note.content = request.form['content']
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_note/<int:id>')
def delete_note(id):
    db.session.delete(Note.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_weekly', methods=['POST'])
def add_weekly():
    day = request.form['day']
    task = request.form['task']
    db.session.add(WeeklyPlan(day=day, task=task))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_weekly/<int:id>')
def delete_weekly(id):
    db.session.delete(WeeklyPlan.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_todo', methods=['POST'])
def add_todo():
    task = request.form['task']
    priority = request.form['priority']
    db.session.add(Todo(task=task, priority=priority))
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_todo/<int:id>')
def delete_todo(id):
    db.session.delete(Todo.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)