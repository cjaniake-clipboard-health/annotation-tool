import os
import json
import secrets
from flask import redirect, url_for, request, session, current_app, render_template, flash, session
from flask_login import login_user, logout_user, current_user, login_required
from authlib.integrations.flask_client import OAuth
from app import db
from app.auth import bp
from app.models import User

# Initialize OAuth
oauth = OAuth()

@bp.record_once
def on_load(state):
    app = state.app
    oauth.init_app(app)
    
    # Register Google OAuth client
    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url=app.config['GOOGLE_DISCOVERY_URL'],
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

@bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    # Generate a secure nonce
    nonce = secrets.token_urlsafe(16)
    session['nonce'] = nonce

    # Redirect to Google OAuth
    redirect_uri = url_for('auth.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)

@bp.route('/callback')
def callback():
    # Get token from Google
    token = oauth.google.authorize_access_token()

    nonce = session.pop('nonce', None)  # Remove nonce from session after use

    # Get user info from Google
    user_info = oauth.google.parse_id_token(token, nonce=nonce)
    
    # Check if user's email domain is allowed
    email = user_info.get('email', '')
    if not email.endswith('@' + current_app.config['COMPANY_DOMAIN']):
        flash('Access restricted to company email addresses only.', 'error')
        return redirect(url_for('auth.login'))
    
    # Find or create user
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email, name=user_info.get('name', ''))
        db.session.add(user)
        db.session.commit()
    
    # Log in user
    login_user(user)
    
    # Redirect to next page or dashboard
    next_page = session.get('next', url_for('main.dashboard'))
    session.pop('next', None)
    
    return redirect(next_page)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/unauthorized')
def unauthorized():
    return render_template('auth/unauthorized.html')