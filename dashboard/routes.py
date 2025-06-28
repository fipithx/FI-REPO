from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from utils import trans_function, requires_role, get_mongo_db
import logging

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard_bp', __name__, template_folder='templates/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """Trader dashboard - main entry point for trader users."""
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
        
        # Get trader-specific data
        records_count = db.records.count_documents({'user_id': effective_user_id})
        cashflows_count = db.cashflows.count_documents({'user_id': effective_user_id})
        inventory_count = db.inventory.count_documents({'user_id': effective_user_id})
        
        # Recent activities
        recent_records = list(db.records.find({'user_id': effective_user_id}).sort('created_at', -1).limit(5))
        recent_cashflows = list(db.cashflows.find({'user_id': effective_user_id}).sort('created_at', -1).limit(5))
        
        stats = {
            'records': records_count,
            'cashflows': cashflows_count,
            'inventory': inventory_count,
            'coin_balance': user.get('coin_balance', 0)
        }
        
        return render_template(
            'dashboard/trader_dashboard.html',
            user=user,
            stats=stats,
            recent_records=recent_records,
            recent_cashflows=recent_cashflows,
            admin_viewing=(admin_user_id is not None)
        )
    except Exception as e:
        logger.error(f"Error loading trader dashboard: {str(e)}")
        flash(trans_function('dashboard_error', default='Error loading dashboard'), 'danger')
        return render_template('dashboard/trader_dashboard.html', user={}, stats={}, recent_records=[], recent_cashflows=[]), 500

@dashboard_bp.route('/placeholder')
def placeholder():
    """Placeholder route for development."""
    return render_template('dashboard/placeholder.html', message="Trader Dashboard Placeholder")