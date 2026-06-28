from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Numeric
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Settings fields
    gemini_api_key = db.Column(db.String(255), default='')
    preferred_currency = db.Column(db.String(10), default='₹')
    ai_personality = db.Column(db.String(50), default='balanced')  # frugal, balanced, ambitious
    
    # Notification preferences
    notify_budget_alerts = db.Column(db.Boolean, default=True)
    notify_due_reminders = db.Column(db.Boolean, default=True)
    notify_monthly_digest = db.Column(db.Boolean, default=False)
    notify_savings_milestones = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Expense(db.Model):
    __tablename__ = 'expense'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    amount = db.Column(Numeric(precision=10, scale=2), nullable=False)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(20), default='cash', index=True)

    def __repr__(self):
        return f'<Expense {self.category}: {self.amount}>'

class Budget(db.Model):
    __tablename__ = 'budget'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(Numeric(precision=10, scale=2), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('category', 'month', 'year', name='uix_category_month_year'),
        db.Index('idx_month_year', 'month', 'year'),
    )

    def __repr__(self):
        return f'<Budget {self.category}: {self.amount}>'

class SavingsGoal(db.Model):
    __tablename__ = 'savings_goal'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(Numeric(precision=10, scale=2), nullable=False)
    current_amount = db.Column(Numeric(precision=10, scale=2), default=0)
    deadline = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def progress_percentage(self):
        if self.target_amount > 0:
            return (float(self.current_amount) / float(self.target_amount)) * 100
        return 0

    @property
    def is_completed(self):
        return float(self.current_amount) >= float(self.target_amount)

    def __repr__(self):
        return f'<SavingsGoal {self.name}: {self.current_amount}/{self.target_amount}>'

class Income(db.Model):
    __tablename__ = 'income'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    source = db.Column(db.String(50), nullable=False)
    amount = db.Column(Numeric(precision=10, scale=2), nullable=False)
    note = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Income {self.source}: {self.amount}>'

class RecurringExpense(db.Model):
    __tablename__ = 'recurring_expense'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(Numeric(precision=10, scale=2), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, yearly
    next_due = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RecurringExpense {self.name}: {self.amount} ({self.frequency})>'

class Achievement(db.Model):
    __tablename__ = 'achievement'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_key = db.Column(db.String(50), nullable=False)  # unique key for the badge type
    unlocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'badge_key', name='uix_user_badge'),
    )
    
    def __repr__(self):
        return f'<Achievement {self.badge_key} for user {self.user_id}>'

# Badge definitions — static catalog
BADGE_CATALOG = {
    'first_expense': {
        'name': 'First Step',
        'icon': '🏁',
        'description': 'Logged your first expense',
    },
    'expense_streak_7': {
        'name': 'Consistent Tracker',
        'icon': '🔥',
        'description': 'Logged expenses 7 days in a row',
    },
    'budget_master': {
        'name': 'Budget Master',
        'icon': '🎯',
        'description': 'Stayed under budget for a full month',
    },
    'savings_starter': {
        'name': 'Savings Starter',
        'icon': '🌱',
        'description': 'Created your first savings goal',
    },
    'goal_crusher': {
        'name': 'Goal Crusher',
        'icon': '🏆',
        'description': 'Completed a savings goal',
    },
    'income_diversifier': {
        'name': 'Income Diversifier',
        'icon': '💎',
        'description': 'Tracked 3+ income sources',
    },
    'big_saver': {
        'name': 'Big Saver',
        'icon': '💰',
        'description': 'Saved over ₹10,000 total',
    },
    'analytics_pro': {
        'name': 'Analytics Pro',
        'icon': '📊',
        'description': 'Visited analytics 10+ times',
    },
    'century_club': {
        'name': 'Century Club',
        'icon': '💯',
        'description': 'Logged 100 transactions',
    },
    'recurring_champion': {
        'name': 'Recurring Champion',
        'icon': '🔄',
        'description': 'Managed 5+ recurring expenses',
    },
}