"""
Main routes for the Ticket Annotation Tool.

This module defines the routes for the main functionality of the application,
including the dashboard, annotation interface, and data loading.
"""
# Standard library imports
import os
import json
from datetime import datetime, timedelta

# Third-party imports
import pandas as pd
import plotly
import plotly.express as px
from flask import render_template, redirect, url_for, request, jsonify, current_app, flash
from flask_login import login_required, current_user

# Local application imports
from app import db
from app.main import bp
from app.models import Ticket, Category, Annotation, User

@bp.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('main/index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page with summary statistics and filtering"""

    # Default date range for filtering
    default_start_date = datetime(2025, 4, 1)  # fixed or (datetime.now() - timedelta(days=30))
    default_end_date = datetime(2025, 4, 30)  # fixed or datetime.now()

    # Get filter parameters
    start_date = request.args.get('start_date', default_start_date.strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', default_end_date.strftime('%Y-%m-%d'))
    category_id = request.args.get('category_id', 'all')
    
    # Convert to datetime objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Get all categories for the filter dropdown
    categories = Category.query.all()
    
    # Prepare data for the summary table
    summary_data = []
    chart_data = []
    
    for category in categories:
        # Base query for this category
        category_tickets = Ticket.query.filter(Ticket.categories.contains(category))
        
        # Apply date filter if tickets have created_at within range
        if category_id == 'all' or int(category_id) == category.id:
            # Count unlabeled tickets
            unlabeled_count = category_tickets.filter(~Ticket.annotations.any()).count()
            
            # Count positive annotations (is_app_issue = True)
            positive_count = db.session.query(Ticket).join(Annotation).filter(
                Ticket.categories.contains(category),
                Annotation.is_app_issue == True
            ).group_by(Ticket.id).count()
            
            # Count negative annotations (is_app_issue = False)
            negative_count = db.session.query(Ticket).join(Annotation).filter(
                Ticket.categories.contains(category),
                Annotation.is_app_issue == False
            ).group_by(Ticket.id).count()
            
            # Add to summary data
            summary_data.append({
                'category': category.name,
                'category_id': category.id,
                'unlabeled': unlabeled_count,
                'positive': positive_count,
                'negative': negative_count,
                'total': unlabeled_count + positive_count + negative_count
            })

            for ticket_data in category_tickets:
                # Get the most recent annotation for this ticket (if any)
                latest_annotation = ticket_data.get_latest_annotation()
                
                # Use the annotation data if it exists, otherwise set is_app_issue to None
                is_app_issue = 'unlabeled'
                if latest_annotation:
                    if latest_annotation.is_app_issue:
                        is_app_issue = 'positive'
                    else:
                        is_app_issue = 'negative'
                
                chart_data.append({
                    'date': ticket_data.created_at_zendesk.strftime('%Y-%m-%d'),
                    'category': category.name,
                    'is_app_issue': is_app_issue
                })
    
    # Create Plotly chart
    if chart_data:
        df = pd.DataFrame(chart_data)
        #df.to_csv('chart_json.csv')
        # Group by date and category, count issues
        #df_grouped = df[df['is_app_issue'] == True].groupby(['date', 'category']).size().reset_index(name='count')
        df_grouped = df.groupby(['date', 'category']).size().reset_index(name='count')
        
        fig = px.line(df_grouped, x='date', y='count', color='category',
                      title='Daily App Issues by Category')
        #fig.write_image("chart_json.png")

        chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    else:
        chart_json = None
    
    return render_template('main/dashboard.html', 
                          summary_data=summary_data,
                          categories=categories,
                          selected_category=category_id,
                          start_date=start_date,
                          end_date=end_date,
                          chart_json=chart_json)

@bp.route('/annotate')
@login_required
def annotate():
    """
    Annotation page for labeling tickets.
    
    Displays a ticket for annotation based on filter criteria and allows users
    to navigate through tickets.
    """
    # Get filter parameters
    category_id = request.args.get('category_id', 'all')
    status = request.args.get('status', 'unlabeled')  # unlabeled, positive, negative
    
    # Build query based on filters
    query = Ticket.query
    
    # Filter by category if specified
    if category_id != 'all':
        category = Category.query.get(int(category_id))
        if category:
            query = query.filter(Ticket.categories.contains(category))
    
    # Filter by annotation status
    if status == 'unlabeled':
        query = query.filter(~Ticket.annotations.any())
    elif status == 'positive':
        query = query.join(Annotation).filter(Annotation.is_app_issue == True)
    elif status == 'negative':
        query = query.join(Annotation).filter(Annotation.is_app_issue == False)
    
    # Get the ticket ID from the request, or get the first ticket from the query
    ticket_id = request.args.get('ticket_id')
    
    if ticket_id:
        ticket = Ticket.query.get(int(ticket_id))
        if not ticket:
            flash('Ticket not found.', 'error')
            return redirect(url_for('main.dashboard'))
    else:
        ticket = query.first()
        if not ticket:
            flash('No tickets found matching the criteria.', 'error')
            return redirect(url_for('main.dashboard'))
    
    # Get total count and current position
    total_count = query.count()
    current_position = list(query.all()).index(ticket) + 1 if ticket in query.all() else 1
    
    # Get the latest annotation for this ticket if it exists
    latest_annotation = ticket.get_latest_annotation()
    
    return render_template('main/annotate.html',
                          ticket=ticket,
                          current_position=current_position,
                          total_count=total_count,
                          category_id=category_id,
                          status=status,
                          latest_annotation=latest_annotation)

@bp.route('/api/annotate', methods=['POST'])
@login_required
def submit_annotation():
    """
    API endpoint for submitting annotations.
    
    Receives annotation data via JSON and saves it to the database.
    """
    data = request.json
    
    ticket_id = data.get('ticket_id')
    is_app_issue = data.get('is_app_issue')
    rationale = data.get('rationale', '')
    
    if ticket_id is None or is_app_issue is None:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    # Get the ticket
    ticket = Ticket.query.get(int(ticket_id))
    if not ticket:
        return jsonify({'success': False, 'message': 'Ticket not found'}), 404
    
    # Create new annotation
    annotation = Annotation(
        ticket_id=ticket.id,
        user_id=current_user.id,
        is_app_issue=is_app_issue,
        rationale=rationale
    )
    
    db.session.add(annotation)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Annotation submitted successfully'})

@bp.route('/api/next_ticket')
@login_required
def next_ticket():
    """
    API endpoint for getting the next ticket.
    
    Returns the next ticket in the sequence based on filter criteria.
    """
    current_ticket_id = request.args.get('current_ticket_id')
    category_id = request.args.get('category_id', 'all')
    status = request.args.get('status', 'unlabeled')
    
    # Build query based on filters
    query = Ticket.query
    
    # Filter by category if specified
    if category_id != 'all':
        category = Category.query.get(int(category_id))
        if category:
            query = query.filter(Ticket.categories.contains(category))
    
    # Filter by annotation status
    if status == 'unlabeled':
        query = query.filter(~Ticket.annotations.any())
    elif status == 'positive':
        query = query.join(Annotation).filter(Annotation.is_app_issue == True)
    elif status == 'negative':
        query = query.join(Annotation).filter(Annotation.is_app_issue == False)
    
    # Order by ID to ensure consistent ordering
    query = query.order_by(Ticket.id)
    
    # Get all tickets matching the criteria
    tickets = query.all()
    
    if not tickets:
        return jsonify({'success': False, 'message': 'No tickets found matching the criteria'})
    
    # Find the current ticket in the list
    current_index = -1
    if current_ticket_id:
        for i, ticket in enumerate(tickets):
            if ticket.id == int(current_ticket_id):
                current_index = i
                break
    
    # Get the next ticket
    if current_index >= 0 and current_index < len(tickets) - 1:
        next_ticket = tickets[current_index + 1]
    else:
        # If current ticket not found or it's the last one, return the first ticket
        next_ticket = tickets[0]
    
    # Redirect to the annotation page with the next ticket
    return jsonify({
        'success': True,
        'redirect': url_for('main.annotate', 
                           ticket_id=next_ticket.id,
                           category_id=category_id,
                           status=status)
    })

@bp.route('/load_sample_data')
@login_required
def load_sample_data():
    """
    Load sample data from JSON file.
    
    Imports ticket data from a JSON file and creates the necessary database records.
    Only accessible to authenticated users.
    """
    
    try:
        # Load JSON file
        input_file_path = current_app.config['TICKETS_JSON_FILE']
        if not os.path.exists(input_file_path):
            flash('JSON file not found: %s' % input_file_path, 'error')
            return redirect(url_for('main.dashboard'))
        
        df = pd.read_json(input_file_path, compression="gzip")
        
        # Create categories if they don't exist
        categories = [
            'account', 'background checks', 'document assistance', 
            'license and certification', 'shift attendance', 'shift cancellation', 
            'payment', 'technical issues', 'timesheet submission', 'others'
        ]
        
        category_objects = {}
        for category_name in categories:
            category = Category.query.filter_by(name=category_name).first()
            if not category:
                category = Category(name=category_name)
                db.session.add(category)
            category_objects[category_name] = category
        
        db.session.commit()
        
        # Process each row in the JSON file
        tickets_added = 0
        for _, row in df.iterrows():
            in_app_issue_likelihood = row['IN_APP_ISSUE_LIKELIHOOD']
            issue_description_not_an_issue = row['NOT_AN_ISSUE']
            
            likelihood = 'possible'
            if in_app_issue_likelihood == 4 and not issue_description_not_an_issue:
                likelihood = 'likely'
            elif in_app_issue_likelihood < 4 and issue_description_not_an_issue:
                # unlikely an issue: skip
                continue

            # Check if ticket already exists
            existing_ticket = Ticket.query.filter_by(ticket_id=str(row['TICKET_ID'])).first()
            if existing_ticket:
                continue
            
            # Create new ticket
            ticket = Ticket(
                ticket_id=str(row['TICKET_ID']),
                subject=row['SUBJECT'],
                summary=row.get('SUMMARY', None),
                conversation=row.get('CHAT_HISTORY', None),
                tech_issue_likelihood=likelihood,
                issue_description=row.get('ISSUE_DESCRIPTION', None),
                created_at_zendesk=datetime.strptime(row.get('CREATED_AT_PST', None), "%Y-%m-%d").date()
            )
            
            # Add categories
            ticket_categories = row.get('REQUEST_CATEGORIES', '')
            any_category_ok = False
            for category_name in ticket_categories:
                category_name = category_name.strip()
                if category_name and category_name in category_objects:
                    ticket.categories.append(category_objects[category_name])
                    any_category_ok = True

            if not any_category_ok:
                ticket.categories.append(category_objects['others'])
            
            db.session.add(ticket)
            tickets_added += 1
            
            # Commit in batches to avoid memory issues
            if tickets_added % 100 == 0:
                db.session.commit()
        
        # Final commit
        db.session.commit()
        
        flash('Successfully loaded %s tickets from JSON file.' % tickets_added, 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error loading data: %s' % str(e), 'error')
    
    return redirect(url_for('main.dashboard'))