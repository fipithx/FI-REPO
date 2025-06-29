import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, g
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets

# Import the new translation system
from translations import trans, get_translations, get_all_translations

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create logger for this module
logger = logging.getLogger('ficore_app')

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///ficore.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = None
    
    # Initialize extensions
    db = SQLAlchemy(app)
    migrate = Migrate(app, db)
    csrf = CSRFProtect(app)
    
    # Import models after db initialization
    from models import User, Bill, Budget, EmergencyFund, NetWorth, Quiz, FinancialHealth
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    # Session configuration
    @app.before_request
    def before_request():
        """Set up session and global variables before each request"""
        # Initialize session language if not set
        if 'lang' not in session:
            session['lang'] = 'en'  # Default language
        
        # Generate session ID if not exists
        if 'sid' not in session:
            session['sid'] = secrets.token_hex(8)
        
        # Make translation functions available globally
        g.trans = trans
        g.get_translations = get_translations
        g.logger = logger
        
        # Log request info
        logger.info(f"Request: {request.method} {request.path}", 
                   extra={'session_id': session.get('sid', 'no-session-id')})
    
    @app.context_processor
    def inject_template_globals():
        """Inject global variables into all templates"""
        return {
            'trans': trans,
            'get_translations': get_translations,
            'current_lang': session.get('lang', 'en'),
            'available_languages': [
                {'code': 'en', 'name': trans('general_english')},
                {'code': 'ha', 'name': trans('general_hausa')}
            ]
        }
    
    # Language switching route
    @app.route('/change-language', methods=['POST'])
    def change_language():
        """Handle language switching"""
        try:
            data = request.get_json()
            new_lang = data.get('language', 'en')
            
            if new_lang in ['en', 'ha']:
                session['lang'] = new_lang
                logger.info(f"Language changed to {new_lang}", 
                           extra={'session_id': session.get('sid', 'no-session-id')})
                return jsonify({
                    'success': True, 
                    'message': trans('general_language_changed', lang=new_lang)
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': trans('general_invalid_language')
                }), 400
                
        except Exception as e:
            logger.error(f"Error changing language: {str(e)}", 
                        extra={'session_id': session.get('sid', 'no-session-id')})
            return jsonify({
                'success': False, 
                'message': trans('general_error')
            }), 500
    
    # Authentication decorator
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash(trans('general_login_required'), 'warning')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    
    # Main routes
    @app.route('/')
    def index():
        """Home page"""
        return render_template('index.html', 
                             title=trans('general_welcome'),
                             page_title=trans('general_home'))
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Main dashboard"""
        try:
            # Get user data for dashboard
            user_id = session.get('user_id')
            
            # Get summary data from different modules
            dashboard_data = {
                'bills_summary': get_bills_summary(user_id),
                'budget_summary': get_budget_summary(user_id),
                'net_worth_summary': get_net_worth_summary(user_id),
                'emergency_fund_summary': get_emergency_fund_summary(user_id)
            }
            
            return render_template('dashboard/main.html',
                                 title=trans('general_dashboard'),
                                 dashboard_data=dashboard_data)
                                 
        except Exception as e:
            logger.error(f"Dashboard error: {str(e)}", 
                        extra={'session_id': session.get('sid', 'no-session-id')})
            flash(trans('general_error_loading_dashboard'), 'error')
            return redirect(url_for('index'))
    
    # Helper functions for dashboard data
    def get_bills_summary(user_id):
        """Get bills summary for dashboard"""
        try:
            bills = Bill.query.filter_by(user_id=user_id).all()
            return {
                'total': len(bills),
                'paid': len([b for b in bills if b.status == 'paid']),
                'unpaid': len([b for b in bills if b.status == 'unpaid']),
                'overdue': len([b for b in bills if b.status == 'overdue'])
            }
        except Exception as e:
            logger.error(f"Error getting bills summary: {str(e)}")
            return {'total': 0, 'paid': 0, 'unpaid': 0, 'overdue': 0}
    
    def get_budget_summary(user_id):
        """Get budget summary for dashboard"""
        try:
            budgets = Budget.query.filter_by(user_id=user_id).all()
            if budgets:
                latest_budget = budgets[-1]
                return {
                    'total_income': latest_budget.total_income or 0,
                    'total_expenses': latest_budget.total_expenses or 0,
                    'remaining': (latest_budget.total_income or 0) - (latest_budget.total_expenses or 0)
                }
            return {'total_income': 0, 'total_expenses': 0, 'remaining': 0}
        except Exception as e:
            logger.error(f"Error getting budget summary: {str(e)}")
            return {'total_income': 0, 'total_expenses': 0, 'remaining': 0}
    
    def get_net_worth_summary(user_id):
        """Get net worth summary for dashboard"""
        try:
            net_worth = NetWorth.query.filter_by(user_id=user_id).order_by(NetWorth.created_at.desc()).first()
            if net_worth:
                return {
                    'total_assets': net_worth.total_assets or 0,
                    'total_liabilities': net_worth.total_liabilities or 0,
                    'net_worth': net_worth.net_worth or 0
                }
            return {'total_assets': 0, 'total_liabilities': 0, 'net_worth': 0}
        except Exception as e:
            logger.error(f"Error getting net worth summary: {str(e)}")
            return {'total_assets': 0, 'total_liabilities': 0, 'net_worth': 0}
    
    def get_emergency_fund_summary(user_id):
        """Get emergency fund summary for dashboard"""
        try:
            emergency_fund = EmergencyFund.query.filter_by(user_id=user_id).order_by(EmergencyFund.created_at.desc()).first()
            if emergency_fund:
                return {
                    'target_amount': emergency_fund.target_amount or 0,
                    'current_savings': emergency_fund.current_savings or 0,
                    'savings_gap': (emergency_fund.target_amount or 0) - (emergency_fund.current_savings or 0),
                    'monthly_savings_needed': emergency_fund.monthly_savings_needed or 0
                }
            return {'target_amount': 0, 'current_savings': 0, 'savings_gap': 0, 'monthly_savings_needed': 0}
        except Exception as e:
            logger.error(f"Error getting emergency fund summary: {str(e)}")
            return {'target_amount': 0, 'current_savings': 0, 'savings_gap': 0, 'monthly_savings_needed': 0}
    
    # Authentication routes
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login"""
        if request.method == 'POST':
            try:
                email = request.form.get('email')
                password = request.form.get('password')
                
                if not email or not password:
                    flash(trans('general_email_password_required'), 'error')
                    return render_template('auth/login.html')
                
                user = User.query.filter_by(email=email).first()
                
                if user and check_password_hash(user.password_hash, password):
                    session['user_id'] = user.id
                    session['user_email'] = user.email
                    session['user_name'] = user.first_name
                    
                    logger.info(f"User logged in: {email}", 
                               extra={'session_id': session.get('sid', 'no-session-id')})
                    
                    flash(trans('general_login_successful'), 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash(trans('general_invalid_credentials'), 'error')
                    
            except Exception as e:
                logger.error(f"Login error: {str(e)}", 
                            extra={'session_id': session.get('sid', 'no-session-id')})
                flash(trans('general_login_error'), 'error')
        
        return render_template('auth/login.html', 
                             title=trans('general_login'))
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration"""
        if request.method == 'POST':
            try:
                first_name = request.form.get('first_name')
                last_name = request.form.get('last_name')
                email = request.form.get('email')
                password = request.form.get('password')
                confirm_password = request.form.get('confirm_password')
                
                # Validation
                if not all([first_name, last_name, email, password, confirm_password]):
                    flash(trans('general_all_fields_required'), 'error')
                    return render_template('auth/register.html')
                
                if password != confirm_password:
                    flash(trans('general_password_mismatch'), 'error')
                    return render_template('auth/register.html')
                
                # Check if user exists
                if User.query.filter_by(email=email).first():
                    flash(trans('general_email_already_exists'), 'error')
                    return render_template('auth/register.html')
                
                # Create new user
                user = User(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password_hash=generate_password_hash(password)
                )
                
                db.session.add(user)
                db.session.commit()
                
                logger.info(f"New user registered: {email}", 
                           extra={'session_id': session.get('sid', 'no-session-id')})
                
                flash(trans('general_registration_successful'), 'success')
                return redirect(url_for('login'))
                
            except Exception as e:
                logger.error(f"Registration error: {str(e)}", 
                            extra={'session_id': session.get('sid', 'no-session-id')})
                flash(trans('general_registration_error'), 'error')
                db.session.rollback()
        
        return render_template('auth/register.html', 
                             title=trans('general_register'))
    
    @app.route('/logout')
    def logout():
        """User logout"""
        user_email = session.get('user_email', 'unknown')
        session.clear()
        
        logger.info(f"User logged out: {user_email}", 
                   extra={'session_id': session.get('sid', 'no-session-id')})
        
        flash(trans('general_logout_successful'), 'success')
        return redirect(url_for('index'))
    
    # Profile management
    @app.route('/profile')
    @login_required
    def profile():
        """User profile page"""
        try:
            user = User.query.get(session['user_id'])
            if not user:
                flash(trans('general_user_not_found'), 'error')
                return redirect(url_for('logout'))
            
            return render_template('auth/profile.html', 
                                 title=trans('general_profile'),
                                 user=user)
                                 
        except Exception as e:
            logger.error(f"Profile error: {str(e)}", 
                        extra={'session_id': session.get('sid', 'no-session-id')})
            flash(trans('general_error'), 'error')
            return redirect(url_for('dashboard'))
    
    @app.route('/profile/update', methods=['POST'])
    @login_required
    def update_profile():
        """Update user profile"""
        try:
            user = User.query.get(session['user_id'])
            if not user:
                flash(trans('general_user_not_found'), 'error')
                return redirect(url_for('logout'))
            
            # Update user data
            user.first_name = request.form.get('first_name', user.first_name)
            user.last_name = request.form.get('last_name', user.last_name)
            user.phone = request.form.get('phone', user.phone)
            user.address = request.form.get('address', user.address)
            
            db.session.commit()
            
            # Update session data
            session['user_name'] = user.first_name
            
            logger.info(f"Profile updated for user: {user.email}", 
                       extra={'session_id': session.get('sid', 'no-session-id')})
            
            flash(trans('general_profile_updated'), 'success')
            
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}", 
                        extra={'session_id': session.get('sid', 'no-session-id')})
            flash(trans('general_update_error'), 'error')
            db.session.rollback()
        
        return redirect(url_for('profile'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html', 
                             title=trans('general_page_not_found')), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f"Internal server error: {str(error)}", 
                    extra={'session_id': session.get('sid', 'no-session-id')})
        return render_template('errors/500.html', 
                             title=trans('general_internal_error')), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html', 
                             title=trans('general_access_denied')), 403
    
    # API endpoints for AJAX calls
    @app.route('/api/translations/<lang>')
    def api_translations(lang):
        """API endpoint to get all translations for a language"""
        try:
            if lang not in ['en', 'ha']:
                return jsonify({'error': trans('general_invalid_language')}), 400
            
            translations = get_all_translations()
            result = {}
            
            # Flatten all translations for the requested language
            for module_name, module_translations in translations.items():
                if lang in module_translations:
                    result.update(module_translations[lang])
            
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"API translations error: {str(e)}", 
                        extra={'session_id': session.get('sid', 'no-session-id')})
            return jsonify({'error': trans('general_error')}), 500
    
    @app.route('/api/translate')
    def api_translate():
        """API endpoint for single translation"""
        try:
            key = request.args.get('key')
            lang = request.args.get('lang', session.get('lang', 'en'))
            
            if not key:
                return jsonify({'error': trans('general_missing_key')}), 400
            
            translation = trans(key, lang=lang)
            return jsonify({'key': key, 'translation': translation, 'lang': lang})
            
        except Exception as e:
            logger.error(f"API translate error: {str(e)}", 
                        extra={'session_id': session.get('sid', 'no-session-id')})
            return jsonify({'error': trans('general_error')}), 500
    
    # Register blueprints
    try:
        # Personal Finance Blueprints
        from personal.bill import bill_bp
        from personal.budget import budget_bp
        from personal.emergency_fund import emergency_fund_bp
        from personal.financial_health import financial_health_bp
        from personal.learning_hub import learning_hub_bp
        from personal.net_worth import net_worth_bp
        from personal.quiz import quiz_bp
        
        # Accounting Tools Blueprints
        from admin import admin_bp
        from agents import agents_bp
        from coins import coins_bp
        from creditors import creditors_bp
        from dashboard import dashboard_bp
        from debtors import debtors_bp
        from inventory import inventory_bp
        from payments import payments_bp
        from receipts import receipts_bp
        from reports import reports_bp
        
        # General Blueprints
        from common_features import common_features_bp
        from settings import settings_bp
        from users import users_bp
        
        # Register all blueprints
        app.register_blueprint(bill_bp)
        app.register_blueprint(budget_bp)
        app.register_blueprint(emergency_fund_bp)
        app.register_blueprint(financial_health_bp)
        app.register_blueprint(learning_hub_bp)
        app.register_blueprint(net_worth_bp)
        app.register_blueprint(quiz_bp)
        
        app.register_blueprint(admin_bp)
        app.register_blueprint(agents_bp)
        app.register_blueprint(coins_bp)
        app.register_blueprint(creditors_bp)
        app.register_blueprint(dashboard_bp)
        app.register_blueprint(debtors_bp)
        app.register_blueprint(inventory_bp)
        app.register_blueprint(payments_bp)
        app.register_blueprint(receipts_bp)
        app.register_blueprint(reports_bp)
        
        app.register_blueprint(common_features_bp)
        app.register_blueprint(settings_bp)
        app.register_blueprint(users_bp)
        
        logger.info("All blueprints registered successfully")
        
    except ImportError as e:
        logger.warning(f"Some blueprints could not be imported: {str(e)}")
        # Continue without the missing blueprints for development
    
    # Development routes (remove in production)
    if app.debug:
        @app.route('/dev/translations')
        def dev_translations():
            """Development route to view all translations"""
            all_translations = get_all_translations()
            return render_template('dev/translations.html', 
                                 translations=all_translations,
                                 title='Translation Debug')
        
        @app.route('/dev/session')
        def dev_session():
            """Development route to view session data"""
            return jsonify(dict(session))
    
    logger.info("Flask application created successfully")
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)