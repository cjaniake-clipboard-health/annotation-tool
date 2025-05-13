"""
Database models for the Ticket Annotation Tool.

This module defines the database models for users, tickets, categories, and annotations.
"""
from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    name = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    annotations = db.relationship('Annotation', backref='annotator', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.email)

@login_manager.user_loader
def load_user(id):
    """Load a user from the database by ID for Flask-Login."""
    return User.query.get(int(id))

# Association table for many-to-many relationship between Ticket and Category
ticket_category = db.Table('ticket_category',
    db.Column('ticket_id', db.Integer, db.ForeignKey('ticket.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(64), index=True, unique=True)
    subject = db.Column(db.String(256))
    summary = db.Column(db.Text, nullable=True)
    conversation = db.Column(db.Text, nullable=True)
    tech_issue_likelihood = db.Column(db.String(64), nullable=True)
    subject = db.Column(db.String(256))
    issue_description = db.Column(db.Text, nullable=True)
    created_at_zendesk = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    categories = db.relationship('Category', secondary=ticket_category,
                               backref=db.backref('tickets', lazy='dynamic'))
    annotations = db.relationship('Annotation', backref='ticket', lazy='dynamic')
    
    def __repr__(self):
        return '<Ticket {}>'.format(self.ticket_id)
    
    def get_latest_annotation(self):
        """Return the most recent annotation for this ticket, or None if no annotations exist."""
        return self.annotations.order_by(Annotation.created_at.desc()).first()
    
    def is_annotated(self):
        """Check if the ticket has been annotated."""
        return self.annotations.count() > 0
    
    def is_app_issue(self):
        """Return the latest annotation verdict, or None if no annotations exist."""
        latest = self.get_latest_annotation()
        return latest.is_app_issue if latest else None

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    
    def __repr__(self):
        return '<Category {}>'.format(self.name)

class Annotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    is_app_issue = db.Column(db.Boolean, nullable=False)
    rationale = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Foreign keys
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return '<Annotation {} for Ticket {}>'.format(self.id, self.ticket_id)