from flask import Flask, session, redirect, request, url_for, render_template, jsonify
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from flask_session import Session
import tempfile

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = tempfile.gettempdir()
app.secret_key = os.getenv('SECRET_KEY', "personal_health_analysis_secret")

# Initialize Flask-Session
Session(app)

# OAuth 2.0 client configuration
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = [
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.body.read'
]

class HealthMonitoringSystem:
    def __init__(self):
        pass

    def initialize_google_auth(self):
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=url_for('oauth2callback', _external=True)
        )
        return flow

    def fetch_fitness_data(self, credentials):
        try:
            fitness_service = build('fitness', 'v1', credentials=credentials)
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=30)

            # Convert times to milliseconds
            end_time_ms = int(end_time.timestamp() * 1000)
            start_time_ms = int(start_time.timestamp() * 1000)

            body = {
                "aggregateBy": [{
                    "dataTypeName": "com.google.step_count.delta",
                    "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
                }],
                "bucketByTime": {"durationMillis": 86400000},  # Daily buckets
                "startTimeMillis": start_time_ms,
                "endTimeMillis": end_time_ms
            }

            response = fitness_service.users().dataset().aggregate(userId="me", body=body).execute()
            return self._process_fitness_response(response)

        except Exception as e:
            print(f"Error fetching fitness data: {str(e)}")
            return pd.DataFrame({'date': [], 'steps': []})

    def _process_fitness_response(self, response):
        daily_steps = []
        for bucket in response.get('bucket', []):
            start_time = datetime.fromtimestamp(int(bucket['startTimeMillis']) / 1000).date()
            steps = 0
            for dataset in bucket.get('dataset', []):
                for point in dataset.get('point', []):
                    for value in point.get('value', []):
                        steps += int(value.get('intVal', 0))

            daily_steps.append({'date': start_time, 'steps': steps})

        return pd.DataFrame(daily_steps)

    def analyze_health_risks(self, fitness_data):
        if fitness_data.empty:
            return {'risk_score': 0, 'risk_factors': {}, 'recommendations': []}

        avg_steps = float(fitness_data['steps'].mean())
        step_consistency = float(fitness_data['steps'].std())
        inactive_days = int(len(fitness_data[fitness_data['steps'] < 5000]))

        risk_factors = {
            'sedentary_lifestyle': int(avg_steps < 7000),
            'inconsistent_activity': int(step_consistency > 4000),
            'frequent_inactivity': int(inactive_days > 10)
        }

        risk_score = sum([
            40 if risk_factors['sedentary_lifestyle'] else 0,
            30 if risk_factors['inconsistent_activity'] else 0,
            30 if risk_factors['frequent_inactivity'] else 0
        ])

        return {
            'risk_score': int(risk_score),
            'risk_factors': risk_factors,
            'recommendations': self._generate_recommendations(risk_factors)
        }

    def _generate_recommendations(self, risk_factors):
        recommendations = []
        if risk_factors['sedentary_lifestyle']:
            recommendations.append({
                'category': 'Activity Level',
                'suggestion': 'Aim for 10,000 daily steps',
                'action_items': ['Walk after meals', 'Use stairs instead of elevator']
            })
        if risk_factors['inconsistent_activity']:
            recommendations.append({
                'category': 'Consistency',
                'suggestion': 'Establish a regular workout schedule',
                'action_items': ['Join a class', 'Exercise at the same time daily']
            })
        if risk_factors['frequent_inactivity']:
            recommendations.append({
                'category': 'Regular Movement',
                'suggestion': 'Reduce inactive days',
                'action_items': ['Stretch hourly', 'Do simple exercises at home']
            })
        return recommendations

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/authorize')
def authorize():
    flow = HealthMonitoringSystem().initialize_google_auth()
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    if 'state' not in session:
        return redirect(url_for('authorize'))
    
    state = session['state']
    flow = HealthMonitoringSystem().initialize_google_auth()

    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        print(f"Error fetching token: {e}")
        return redirect(url_for('authorize'))

    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    return render_template('dashboard.html')

@app.route('/api/fitness-data')
def fitness_data():
    if 'credentials' not in session:
        return jsonify({'error': 'Not authorized'}), 401

    credentials = Credentials(**session['credentials'])
    health_system = HealthMonitoringSystem()

    fitness_data = health_system.fetch_fitness_data(credentials)
    analysis = health_system.analyze_health_risks(fitness_data)

    # Convert fitness data into serializable format
    serializable_data = [
        {'date': row['date'].isoformat(), 'steps': int(row['steps'])}
        for row in fitness_data.to_dict('records')
    ]

    return jsonify({
        'fitness_data': serializable_data,
        'health_analysis': analysis
    })

if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # For development only
    app.run(port=5000, debug=True)