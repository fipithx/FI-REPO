from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from flask_login import login_required, current_user
from utils import trans_function, requires_role, get_mongo_db
import logging

logger = logging.getLogger(__name__)

agents_bp = Blueprint('agents_bp', __name__, template_folder='templates/agents')

@agents_bp.route('/dashboard')
@login_required
def dashboard():
    """Agent dashboard - main entry point for agent users."""
    try:
        # Check if admin is accessing on behalf of another user
        admin_user_id = request.args.get('admin_user_id') if current_user.role == 'admin' else None
        effective_user_id = admin_user_id if admin_user_id else current_user.id
        
        db = get_mongo_db()
        
        # Get user data
        user = db.users.find_one({'_id': effective_user_id})
        if not user:
            flash(trans_function('user_not_found', default='User not found'), 'danger')
            return redirect(url_for('index'))
        
        # Get agent-specific data
        agent_activities = list(db.agent_activities.find({'agent_id': effective_user_id}).sort('timestamp', -1).limit(10))
        
        # Get traders assisted by this agent
        traders_assisted = list(db.users.find({'role': 'trader'}).limit(10))  # Simplified for now
        
        # Agent statistics
        stats = {
            'activities_count': len(agent_activities),
            'traders_assisted': len(traders_assisted),
            'coin_balance': user.get('coin_balance', 0)
        }
        
        return render_template(
            'agents/agent_dashboard.html',
            user=user,
            stats=stats,
            agent_activities=agent_activities,
            traders_assisted=traders_assisted,
            admin_viewing=(admin_user_id is not None)
        )
    except Exception as e:
        logger.error(f"Error loading agent dashboard: {str(e)}")
        flash(trans_function('dashboard_error', default='Error loading dashboard'), 'danger')
        return render_template('agents/agent_dashboard.html', user={}, stats={}, agent_activities=[], traders_assisted=[]), 500

@agents_bp.route('/placeholder')
def placeholder():
    """Placeholder route for development."""
    return render_template('agents/placeholder.html', message="Agent Dashboard Placeholder")