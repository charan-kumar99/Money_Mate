from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import Numeric

db = SQLAlchemy()

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