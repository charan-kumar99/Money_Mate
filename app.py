import os
from flask import Flask, render_template, request, redirect, send_file, flash, jsonify, session, url_for
from datetime import datetime, timedelta
from collections import defaultdict
import csv
import io
import calendar
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from models import db, Expense, Budget, SavingsGoal, Income, RecurringExpense, User
from calendar import monthrange
from werkzeug.security import generate_password_hash
import json
from google import genai
import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from flask_mail import Mail, Message
import random
import string

app = Flask(__name__)

# Database Configuration - supports both local and cloud
# For local: uses local PostgreSQL
# For production: uses DATABASE_URL environment variable (Neon, Supabase, etc.)
if os.environ.get('DATABASE_URL'):
    # Production - use cloud database
    database_url = os.environ.get('DATABASE_URL')
    # Fix for SQLAlchemy (some providers use postgres:// instead of postgresql://)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Local development - use local PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Passw0rd@localhost:5432/money_mate'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a3f9c2d5e6b7f8a9c0d1e2f3b4a5c6d7e8f9b0c1d2e3f4a5b6c7d8e9f0a1b2c3')
app.config['WTF_CSRF_TIME_LIMIT'] = None
app.config['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', '')

# Email Configuration (Gmail)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'your-app-password')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'your-email@gmail.com')

# Configure Gemini client
client = genai.Client(api_key=app.config['GEMINI_API_KEY'])

db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)
mail = Mail(app)

# Currency conversion via API (base currency: INR)
API_RATES_CACHE = {}
LAST_FETCHED = None

def get_exchange_rates():
    global API_RATES_CACHE, LAST_FETCHED
    now = datetime.now()
    if not API_RATES_CACHE or (LAST_FETCHED and (now - LAST_FETCHED).total_seconds() > 3600):
        try:
            response = requests.get('https://open.er-api.com/v6/latest/INR', timeout=5)
            if response.status_code == 200:
                data = response.json()
                API_RATES_CACHE = data.get('rates', {})
                LAST_FETCHED = now
        except Exception as e:
            print("Failed to fetch rates:", e)
    return API_RATES_CACHE

SYMBOL_TO_ISO = {'₹': 'INR', '$': 'USD', '€': 'EUR', '£': 'GBP', '¥': 'JPY'}
ISO_TO_SYMBOL = {'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥'}
STATIC_FALLBACK = {'INR': 1.0, 'USD': 0.012, 'EUR': 0.011, 'GBP': 0.0094, 'JPY': 1.80}

def get_currency():
    curr = session.get('currency', '₹')
    return ISO_TO_SYMBOL.get(curr, curr) if len(curr) > 1 else curr

def get_currency_iso():
    curr = session.get('currency', '₹')
    return SYMBOL_TO_ISO.get(curr, curr)

def set_currency(currency):
    session['currency'] = currency

def get_currency_rate(target_currency):
    """Get conversion rate for selected currency"""
    rates = get_exchange_rates()
    iso = SYMBOL_TO_ISO.get(target_currency, target_currency)
    if rates and iso in rates:
        return rates[iso]
    return STATIC_FALLBACK.get(iso, 1.0)

def convert_amount(amount, target_currency='₹'):
    """Convert amount from INR to target currency"""
    rate = get_currency_rate(target_currency)
    return float(amount) * rate

def get_conversion_info(currency):
    """Get readable conversion information"""
    iso = SYMBOL_TO_ISO.get(currency, currency)
    if iso == 'INR':
        return None
    rate = get_currency_rate(currency)
    if rate > 1:
        return f"1 INR = {rate:.2f} {iso}"
    else:
        reverse_rate = 1 / rate if rate > 0 else 0
        return f"1 {iso} = ₹{reverse_rate:.2f}"

def get_month_range(year, month):
    """Get the first and last day of a given month"""
    start = datetime(year, month, 1).date()
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day).date()
    return start, end

@app.context_processor
def inject_global_vars():
    """Inject global variables into all templates"""
    currency = get_currency()
    iso_code = get_currency_iso()
    return {
        'datetime': datetime,
        'currency': currency,
        'get_currency': get_currency,
        'conversion_info': get_conversion_info(currency),
        'currency_name': iso_code
    }

# Currency Cache for Frankfurter API
converter_cache = {}

def get_frankfurter_rate(from_currency, to_currency):
    """Fetch rate from Frankfurter API with caching"""
    # API doesn't support same currency conversion
    if from_currency == to_currency:
        return 1.0
        
    key = f"{from_currency}-{to_currency}"

    if key in converter_cache:
        return converter_cache[key]
    else:
        try:
            url = f"https://api.frankfurter.dev/latest?from={from_currency}&to={to_currency}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                rate = data['rates'][to_currency]
                converter_cache[key] = rate
                return rate
            return None
        except Exception as e:
            print("Converter API error:", e)
            return None

@app.route('/convert', methods=['GET'])
def convert():
    from_curr = request.args.get('from')
    to_curr = request.args.get('to')
    amount = request.args.get('amount')
    
    if not all([from_curr, to_curr, amount]):
        return jsonify({"error": "Missing parameters"}), 400

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"error": "Invalid amount"}), 400

    rate = get_frankfurter_rate(from_curr, to_curr)

    if rate is not None:
        converted = float(rate) * amount
        return jsonify({
            "from": from_curr,
            "to": to_curr,
            "amount": amount,
            "converted": converted
        })
    else:
        return jsonify({"error": "Conversion failed"}), 500

@app.route("/set_currency/<currency>")
def set_currency_route(currency):
    """Change the display currency"""
    set_currency(currency)
    valid_name = SYMBOL_TO_ISO.get(currency, currency)
    flash(f"Currency changed to {valid_name}", "success")
    return redirect(request.referrer or '/')

@app.route("/api/currencies")
def api_currencies():
    rates = get_exchange_rates()
    return jsonify({"currencies": sorted(list(rates.keys())) if rates else list(STATIC_FALLBACK.keys())})

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Main dashboard with expense tracking and overview"""
    if request.method == "POST":
        try:
            # Validate and process new expense
            date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            category = request.form["category"].strip()
            amount = float(request.form["amount"])
            note = request.form.get("note", "").strip()
            payment_method = request.form.get("payment_method", "cash")
            
            if amount <= 0:
                flash("Amount must be greater than 0!", "danger")
                return redirect("/")
            
            if not category:
                flash("Category is required!", "danger")
                return redirect("/")
            
            new_expense = Expense(
                date=date, 
                category=category, 
                amount=amount, 
                note=note, 
                payment_method=payment_method
            )
            db.session.add(new_expense)
            db.session.commit()
            flash("Expense added successfully! 🎉", "success")
        except ValueError as e:
            flash(f"Invalid input: {str(e)}", "danger")
        except Exception as e:
            db.session.rollback()
            print("Error adding expense:", e)
            flash("Error adding expense. Please try again.", "danger")
        return redirect("/")

    # Apply filters
    category_filter = request.args.get("category_filter", "")
    date_filter = request.args.get("date_filter", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    sort_by = request.args.get("sort_by", "date_desc")
    search_query = request.args.get("search_query", "")
    payment_filter = request.args.get("payment_filter", "")
    
    expenses = Expense.query
    
    today = datetime.now().date()
    if date_filter == "last_7_days":
        seven_days_ago = today - timedelta(days=7)
        expenses = expenses.filter(Expense.date >= seven_days_ago)
    elif date_filter == "last_30_days":
        thirty_days_ago = today - timedelta(days=30)
        expenses = expenses.filter(Expense.date >= thirty_days_ago)
    elif date_filter == "this_month":
        first_day_of_month = today.replace(day=1)
        expenses = expenses.filter(Expense.date >= first_day_of_month)
    elif date_filter == "last_month":
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        expenses = expenses.filter(Expense.date >= first_day_last_month, Expense.date <= last_day_last_month)
    elif date_filter == "custom" and start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            expenses = expenses.filter(Expense.date >= start, Expense.date <= end)
        except ValueError:
            pass
    
    if category_filter:
        expenses = expenses.filter(Expense.category == category_filter)

    if payment_filter:
        expenses = expenses.filter(Expense.payment_method == payment_filter)

    if search_query:
        expenses = expenses.filter(Expense.note.ilike(f"%{search_query}%"))

    # Apply sorting
    if sort_by == "date_desc":
        expenses = expenses.order_by(Expense.date.desc())
    elif sort_by == "date_asc":
        expenses = expenses.order_by(Expense.date.asc())
    elif sort_by == "amount_desc":
        expenses = expenses.order_by(Expense.amount.desc())
    elif sort_by == "amount_asc":
        expenses = expenses.order_by(Expense.amount.asc())
    elif sort_by == "category":
        expenses = expenses.order_by(Expense.category.asc())
    
    expenses = expenses.all()
    
    # Convert amounts to selected currency
    currency = get_currency()
    total = sum(convert_amount(e.amount, currency) for e in expenses)
    
    # Get all categories for dropdown
    all_expenses = Expense.query.all()
    categories = sorted(set(e.category for e in all_expenses))
    
    # Calculate category and payment totals
    category_totals = defaultdict(float)
    payment_totals = defaultdict(float)
    for e in expenses:
        category_totals[e.category] += convert_amount(e.amount, currency)
        payment_totals[e.payment_method] += convert_amount(e.amount, currency)
    
    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Monthly trend data (last 6 months)
    monthly_data = []
    monthly_labels = []
    monthly_totals = []
    
    for i in range(5, -1, -1):
        calc_month = today.month - i
        calc_year = today.year
        while calc_month <= 0:
            calc_month += 12
            calc_year -= 1
        start, end = get_month_range(calc_year, calc_month)
        month_total = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.date >= start,
            Expense.date <= end
        ).scalar() or 0
        month_name = start.strftime('%b %Y')
        converted_total = convert_amount(month_total, currency)
        monthly_data.append({
            'month': month_name,
            'total': converted_total
        })
        monthly_labels.append(month_name)
        monthly_totals.append(converted_total)
    
    # Get income and expenses for current month
    first_day_of_month = today.replace(day=1)
    month_income = db.session.query(db.func.sum(Income.amount)).filter(
        Income.date >= first_day_of_month
    ).scalar() or 0
    
    month_expenses_total = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.date >= first_day_of_month
    ).scalar() or 0
    
    month_income_converted = convert_amount(month_income, currency)
    month_expenses_converted = convert_amount(month_expenses_total, currency)
    net_savings = month_income_converted - month_expenses_converted
    
    # Convert expense amounts for display
    expense_list = []
    for e in expenses:
        expense_list.append({
            'id': e.id,
            'date': e.date,
            'category': e.category,
            'amount': convert_amount(e.amount, currency),
            'note': e.note,
            'payment_method': e.payment_method
        })
    
    return render_template(
        "index.html",
        expenses=expense_list,
        categories=categories,
        category_filter=category_filter,
        date_filter=date_filter,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        search_query=search_query,
        payment_filter=payment_filter,
        total=total,
        top_categories=top_categories,
        monthly_data=monthly_data,
        monthly_labels=monthly_labels,
        monthly_totals=monthly_totals,
        expense_count=len(expenses),
        payment_totals=payment_totals,
        month_income=month_income_converted,
        net_savings=net_savings
    )

@app.route("/analytics")
@login_required
def analytics():
    """Comprehensive analytics and insights page"""
    currency = get_currency()
    
    all_expenses = Expense.query.all()
    total_expenses = sum(convert_amount(e.amount, currency) for e in all_expenses)
    expense_count = len(all_expenses)
    
    # Get total income
    all_income = Income.query.all()
    total_income = sum(convert_amount(i.amount, currency) for i in all_income)
    
    category_totals = defaultdict(float)
    category_counts = defaultdict(int)
    payment_totals = defaultdict(float)
    
    for e in all_expenses:
        converted_amount = convert_amount(e.amount, currency)
        category_totals[e.category] += converted_amount
        category_counts[e.category] += 1
        payment_totals[e.payment_method] += converted_amount
    
    category_data = [
        {
            'category': cat,
            'total': total,
            'count': category_counts[cat],
            'avg': total / category_counts[cat] if category_counts[cat] > 0 else 0,
            'percentage': (total / total_expenses * 100) if total_expenses > 0 else 0
        }
        for cat, total in category_totals.items()
    ]
    category_data.sort(key=lambda x: x['total'], reverse=True)
    
    # 12-month trend analysis
    monthly_trend = []
    today = datetime.now().date()
    for i in range(11, -1, -1):
        calc_month = today.month - i
        calc_year = today.year
        while calc_month <= 0:
            calc_month += 12
            calc_year -= 1
        start, end = get_month_range(calc_year, calc_month)
        
        month_total = db.session.query(db.func.sum(Expense.amount)).filter(
            Expense.date >= start,
            Expense.date <= end
        ).scalar() or 0
        
        month_income = db.session.query(db.func.sum(Income.amount)).filter(
            Income.date >= start,
            Income.date <= end
        ).scalar() or 0
        
        month_count = Expense.query.filter(Expense.date >= start, Expense.date <= end).count()
        
        month_total_converted = convert_amount(month_total, currency)
        month_income_converted = convert_amount(month_income, currency)
        
        monthly_trend.append({
            'month': start.strftime('%b %Y'),
            'total': month_total_converted,
            'income': month_income_converted,
            'count': month_count,
            'savings': month_income_converted - month_total_converted
        })
    
    # Calculate averages
    if all_expenses:
        first_expense_date = min(e.date for e in all_expenses)
        days_tracked = (today - first_expense_date).days + 1
        daily_avg = total_expenses / days_tracked if days_tracked > 0 else 0
    else:
        daily_avg = 0
    
    weekly_avg = daily_avg * 7
    monthly_avg = daily_avg * 30

    # Prepare chart data
    category_chart_data = {item['category']: item['total'] for item in category_data}
    month_chart_data = {item['month']: item['total'] for item in monthly_trend}
    month_income_data = {item['month']: item['income'] for item in monthly_trend}
    payment_chart_data = dict(payment_totals)
    
    return render_template(
        "analytics.html",
        total_expenses=total_expenses,
        total_income=total_income,
        expense_count=expense_count,
        category_data=category_data,
        monthly_trend=monthly_trend,
        daily_avg=daily_avg,
        weekly_avg=weekly_avg,
        monthly_avg=monthly_avg,
        category_chart_data=category_chart_data,
        month_chart_data=month_chart_data,
        month_income_data=month_income_data,
        payment_chart_data=payment_chart_data
    )

@app.route("/budgets", methods=["GET", "POST"])
@login_required
def budgets():
    """Budget management page"""
    currency = get_currency()
    today = datetime.now()
    current_month = today.month
    current_year = today.year
    
    if request.method == "POST":
        try:
            category = request.form["category"].strip()
            amount = float(request.form["amount"])
            
            if amount <= 0:
                flash("Budget amount must be greater than 0!", "danger")
                return redirect("/budgets")
            
            # Check if budget already exists for this category and month
            existing_budget = Budget.query.filter_by(
                category=category,
                month=current_month,
                year=current_year
            ).first()
            
            if existing_budget:
                existing_budget.amount = amount
                flash(f"Budget for {category} updated! 💰", "success")
            else:
                new_budget = Budget(
                    category=category,
                    amount=amount,
                    month=current_month,
                    year=current_year
                )
                db.session.add(new_budget)
                flash(f"Budget for {category} created! 💰", "success")
            
            db.session.commit()
        except ValueError:
            flash("Invalid input. Please check your data.", "danger")
        except Exception as e:
            db.session.rollback()
            print("Error managing budget:", e)
            flash("Error managing budget. Please try again.", "danger")
        return redirect("/budgets")
    
    # Get current month's budgets
    budgets = Budget.query.filter_by(month=current_month, year=current_year).all()
    
    first_day = today.replace(day=1).date()
    month_expenses = Expense.query.filter(Expense.date >= first_day).all()
    
    # Calculate category spending
    category_spending = defaultdict(float)
    for e in month_expenses:
        category_spending[e.category] += convert_amount(e.amount, currency)
    
    budget_data = []
    total_budget = 0
    total_spent = 0
    
    for budget in budgets:
        budget_amount = convert_amount(budget.amount, currency)
        spent = category_spending.get(budget.category, 0)
        remaining = budget_amount - spent
        percentage = (spent / budget_amount * 100) if budget_amount > 0 else 0
        
        # Determine status color
        status = "success" if percentage < 80 else "warning" if percentage < 100 else "danger"
        
        budget_data.append({
            'id': budget.id,
            'category': budget.category,
            'budget': budget_amount,
            'spent': spent,
            'remaining': remaining,
            'percentage': percentage,
            'status': status
        })
        
        total_budget += budget_amount
        total_spent += spent
    
    all_expenses = Expense.query.all()
    categories = sorted(set(e.category for e in all_expenses))
    
    return render_template(
        "budgets.html",
        budget_data=budget_data,
        categories=categories,
        current_month=calendar.month_name[current_month],
        current_year=current_year,
        total_budget=total_budget,
        total_spent=total_spent
    )

@app.route("/savings", methods=["GET", "POST"])
@login_required
def savings():
    """Savings goals management"""
    currency = get_currency()
    
    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            target_amount = float(request.form["target_amount"])
            deadline = request.form.get("deadline")
            current_amount = float(request.form.get("current_amount", 0))
            
            if target_amount <= 0:
                flash("Target amount must be greater than 0!", "danger")
                return redirect("/savings")
            
            if deadline:
                deadline = datetime.strptime(deadline, "%Y-%m-%d").date()
            
            new_goal = SavingsGoal(
                name=name,
                target_amount=target_amount,
                current_amount=current_amount,
                deadline=deadline
            )
            db.session.add(new_goal)
            db.session.commit()
            flash("Savings goal created successfully! 🎯", "success")
        except ValueError:
            flash("Invalid input. Please check your data.", "danger")
        except Exception as e:
            db.session.rollback()
            print("Error creating savings goal:", e)
            flash("Error creating savings goal. Please try again.", "danger")
        return redirect("/savings")
    
    savings_goals = SavingsGoal.query.all()
    
    # Convert amounts to selected currency
    goals_list = []
    total_target = 0
    total_current = 0
    
    for goal in savings_goals:
        target = convert_amount(goal.target_amount, currency)
        current = convert_amount(goal.current_amount, currency)
        
        goals_list.append({
            'id': goal.id,
            'name': goal.name,
            'target_amount': target,
            'current_amount': current,
            'deadline': goal.deadline,
            'progress_percentage': (current / target * 100) if target > 0 else 0,
            'is_completed': current >= target
        })
        
        total_target += target
        total_current += current
    
    return render_template(
        "savings.html",
        savings_goals=goals_list,
        total_target=total_target,
        total_current=total_current
    )

@app.route("/income", methods=["GET", "POST"])
@login_required
def income():
    """Income tracking and management"""
    currency = get_currency()
    
    if request.method == "POST":
        try:
            date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            source = request.form["source"].strip()
            amount = float(request.form["amount"])
            note = request.form.get("note", "").strip()
            
            if amount <= 0:
                flash("Amount must be greater than 0!", "danger")
                return redirect("/income")
            
            new_income = Income(
                date=date,
                source=source,
                amount=amount,
                note=note
            )
            db.session.add(new_income)
            db.session.commit()
            flash("Income added successfully! 💵", "success")
        except ValueError:
            flash("Invalid input. Please check your data.", "danger")
        except Exception as e:
            db.session.rollback()
            print("Error adding income:", e)
            flash("Error adding income. Please try again.", "danger")
        return redirect("/income")
    
    # Get all income records
    income_records = Income.query.order_by(Income.date.desc()).all()
    total_income = sum(convert_amount(i.amount, currency) for i in income_records)
    
    # Get all expenses for comparison
    all_expenses = Expense.query.all()
    total_expenses = sum(convert_amount(e.amount, currency) for e in all_expenses)
    net_savings = total_income - total_expenses
    
    # Monthly income trend
    monthly_income = []
    today = datetime.now().date()
    for i in range(5, -1, -1):
        calc_month = today.month - i
        calc_year = today.year
        while calc_month <= 0:
            calc_month += 12
            calc_year -= 1
        start, end = get_month_range(calc_year, calc_month)
        month_total = db.session.query(db.func.sum(Income.amount)).filter(
            Income.date >= start,
            Income.date <= end
        ).scalar() or 0
        month_name = start.strftime('%b %Y')
        monthly_income.append({
            'month': month_name,
            'total': convert_amount(month_total, currency)
        })
    
    # Convert income amounts for display
    income_list = []
    for i in income_records:
        income_list.append({
            'id': i.id,
            'date': i.date,
            'source': i.source,
            'amount': convert_amount(i.amount, currency),
            'note': i.note
        })
    
    return render_template(
        "income.html",
        income_records=income_list,
        total_income=total_income,
        total_expenses=total_expenses,
        net_savings=net_savings,
        monthly_income=monthly_income
    )

@app.route("/recurring", methods=["GET", "POST"])
@login_required
def recurring():
    """Recurring expenses management"""
    currency = get_currency()
    
    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            category = request.form["category"].strip()
            amount = float(request.form["amount"])
            frequency = request.form["frequency"]
            next_due = datetime.strptime(request.form["next_due"], "%Y-%m-%d").date()
            
            if amount <= 0:
                flash("Amount must be greater than 0!", "danger")
                return redirect("/recurring")
            
            new_recurring = RecurringExpense(
                name=name,
                category=category,
                amount=amount,
                frequency=frequency,
                next_due=next_due,
                is_active=True
            )
            db.session.add(new_recurring)
            db.session.commit()
            flash("Recurring expense added successfully! 🔄", "success")
        except ValueError:
            flash("Invalid input. Please check your data.", "danger")
        except Exception as e:
            db.session.rollback()
            print("Error adding recurring expense:", e)
            flash("Error adding recurring expense. Please try again.", "danger")
        return redirect("/recurring")
    
    recurring_expenses = RecurringExpense.query.filter_by(is_active=True).all()
    all_expenses = Expense.query.all()
    categories = sorted(set(e.category for e in all_expenses))
    
    # Convert amounts for display
    recurring_list = []
    for r in recurring_expenses:
        recurring_list.append({
            'id': r.id,
            'name': r.name,
            'category': r.category,
            'amount': convert_amount(r.amount, currency),
            'frequency': r.frequency,
            'next_due': r.next_due,
            'is_active': r.is_active
        })
    
    return render_template(
        "recurring.html",
        recurring_expenses=recurring_list,
        categories=categories
    )

# DELETE ROUTES
@app.route("/delete_income/<int:income_id>", methods=["POST"])
@login_required
def delete_income(income_id):
    """Delete an income record"""
    income_record = Income.query.get_or_404(income_id)
    try:
        db.session.delete(income_record)
        db.session.commit()
        flash("Income record deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        print("Error deleting income:", e)
        flash("Error deleting income record.", "danger")
    return redirect("/income")

@app.route("/toggle_recurring/<int:recurring_id>", methods=["POST"])
@login_required
def toggle_recurring(recurring_id):
    """Toggle recurring expense active status"""
    recurring = RecurringExpense.query.get_or_404(recurring_id)
    try:
        recurring.is_active = not recurring.is_active
        db.session.commit()
        status = "activated" if recurring.is_active else "deactivated"
        flash(f"Recurring expense {status}!", "success")
    except Exception as e:
        db.session.rollback()
        print("Error toggling recurring:", e)
        flash("Error updating recurring expense.", "danger")
    return redirect("/recurring")

@app.route("/delete_recurring/<int:recurring_id>", methods=["POST"])
@login_required
def delete_recurring(recurring_id):
    """Delete a recurring expense"""
    recurring = RecurringExpense.query.get_or_404(recurring_id)
    try:
        db.session.delete(recurring)
        db.session.commit()
        flash("Recurring expense deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        print("Error deleting recurring:", e)
        flash("Error deleting recurring expense.", "danger")
    return redirect("/recurring")

@app.route("/update_savings/<int:goal_id>", methods=["POST"])
@login_required
def update_savings(goal_id):
    """Update savings goal progress"""
    goal = SavingsGoal.query.get_or_404(goal_id)
    try:
        current_amount = float(request.form["current_amount"])
        if current_amount < 0:
            flash("Amount cannot be negative!", "danger")
            return redirect("/savings")
        goal.current_amount = current_amount
        db.session.commit()
        flash("Savings goal updated successfully! 💰", "success")
    except Exception as e:
        db.session.rollback()
        print("Error updating savings goal:", e)
        flash("Error updating savings goal.", "danger")
    return redirect("/savings")

@app.route("/delete_savings/<int:goal_id>", methods=["POST"])
@login_required
def delete_savings(goal_id):
    """Delete a savings goal"""
    goal = SavingsGoal.query.get_or_404(goal_id)
    try:
        db.session.delete(goal)
        db.session.commit()
        flash("Savings goal deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        print("Error deleting savings goal:", e)
        flash("Error deleting savings goal.", "danger")
    return redirect("/savings")

@app.route("/delete_budget/<int:budget_id>", methods=["POST"])
@login_required
def delete_budget(budget_id):
    """Delete a budget"""
    budget = Budget.query.get_or_404(budget_id)
    try:
        db.session.delete(budget)
        db.session.commit()
        flash("Budget deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        print("Error deleting budget:", e)
        flash("Error deleting budget.", "danger")
    return redirect("/budgets")

@app.route("/export")
@login_required
def export_csv():
    """Export ALL user data to a comprehensive CSV file"""
    currency = get_currency()
    today_dt = datetime.now()
    today = today_dt.date()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # SECTION 1: EXPENSES
    writer.writerow(["=== EXPENSES ==="])
    writer.writerow(["Date", "Category", "Amount", "Note", "Payment Method"])
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    total_expenses = 0
    for e in expenses:
        amt = convert_amount(e.amount, currency)
        total_expenses += amt
        writer.writerow([e.date.strftime("%Y-%m-%d"), e.category, f"{amt:.2f}", e.note or "", e.payment_method])
    writer.writerow(["", "", f"Total: {total_expenses:.2f}", "", ""])
    writer.writerow([])
    
    # SECTION 2: INCOME
    writer.writerow(["=== INCOME ==="])
    writer.writerow(["Date", "Source", "Amount", "Note"])
    income_records = Income.query.order_by(Income.date.desc()).all()
    total_income = 0
    for i in income_records:
        amt = convert_amount(i.amount, currency)
        total_income += amt
        writer.writerow([i.date.strftime("%Y-%m-%d"), i.source, f"{amt:.2f}", i.note or ""])
    writer.writerow(["", "", f"Total: {total_income:.2f}", ""])
    writer.writerow([])
    
    # SECTION 3: BUDGETS
    writer.writerow(["=== BUDGETS (Current Month) ==="])
    writer.writerow(["Category", "Budget Amount", "Spent", "Remaining", "Utilization %"])
    budgets_list = Budget.query.filter_by(month=today_dt.month, year=today_dt.year).all()
    first_day = today.replace(day=1)
    month_expenses = Expense.query.filter(Expense.date >= first_day).all()
    cat_spending = defaultdict(float)
    for e in month_expenses:
        cat_spending[e.category] += convert_amount(e.amount, currency)
    for b in budgets_list:
        b_amt = convert_amount(b.amount, currency)
        spent = cat_spending.get(b.category, 0)
        writer.writerow([b.category, f"{b_amt:.2f}", f"{spent:.2f}", f"{b_amt - spent:.2f}", f"{(spent/b_amt*100) if b_amt > 0 else 0:.1f}%"])
    writer.writerow([])
    
    # SECTION 4: SAVINGS GOALS
    writer.writerow(["=== SAVINGS GOALS ==="])
    writer.writerow(["Goal Name", "Current Amount", "Target Amount", "Progress %", "Deadline"])
    savings_goals = SavingsGoal.query.all()
    for g in savings_goals:
        cur = convert_amount(g.current_amount, currency)
        tgt = convert_amount(g.target_amount, currency)
        pct = (cur / tgt * 100) if tgt > 0 else 0
        writer.writerow([g.name, f"{cur:.2f}", f"{tgt:.2f}", f"{pct:.1f}%", g.deadline.strftime("%Y-%m-%d") if g.deadline else "No deadline"])
    writer.writerow([])
    
    # SECTION 5: RECURRING EXPENSES
    writer.writerow(["=== RECURRING EXPENSES ==="])
    writer.writerow(["Name", "Category", "Amount", "Frequency", "Next Due", "Status"])
    recurring_list = RecurringExpense.query.all()
    for r in recurring_list:
        r_amt = convert_amount(r.amount, currency)
        writer.writerow([r.name, r.category, f"{r_amt:.2f}", r.frequency, r.next_due.strftime("%Y-%m-%d"), "Active" if r.is_active else "Paused"])
    writer.writerow([])
    
    # SECTION 6: SUMMARY
    writer.writerow(["=== FINANCIAL SUMMARY ==="])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Income", f"{currency}{total_income:.2f}"])
    writer.writerow(["Total Expenses", f"{currency}{total_expenses:.2f}"])
    writer.writerow(["Net Balance", f"{currency}{total_income - total_expenses:.2f}"])
    writer.writerow(["Expense Count", len(expenses)])
    writer.writerow(["Income Records", len(income_records)])
    writer.writerow(["Active Budgets", len(budgets_list)])
    writer.writerow(["Savings Goals", len(savings_goals)])
    writer.writerow(["Recurring Expenses", len(recurring_list)])
    writer.writerow(["Currency", currency])
    writer.writerow(["Export Date", today_dt.strftime("%Y-%m-%d %H:%M:%S")])
    
    output.seek(0)
    filename = f"money_mate_full_report_{today_dt.strftime('%Y%m%d_%H%M%S')}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )

@app.route("/export_pdf")
@login_required
def export_pdf():
    """Export ALL user data to a well-structured PDF file"""
    currency = get_currency()
    today_dt = datetime.now()
    today = today_dt.date()
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#3b82f6'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Title
    elements.append(Paragraph("Money Mate Financial Report", title_style))
    elements.append(Paragraph(f"Generated on {today_dt.strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    elements.append(Spacer(1, 0.3*inch))
    
    # SECTION 1: FINANCIAL SUMMARY
    elements.append(Paragraph("Financial Summary", heading_style))
    
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    total_expenses = sum(convert_amount(e.amount, currency) for e in expenses)
    
    income_records = Income.query.order_by(Income.date.desc()).all()
    total_income = sum(convert_amount(i.amount, currency) for i in income_records)
    
    net_balance = total_income - total_expenses
    
    summary_data = [
        ['Metric', 'Value'],
        ['Total Income', f'{currency}{total_income:,.2f}'],
        ['Total Expenses', f'{currency}{total_expenses:,.2f}'],
        ['Net Balance', f'{currency}{net_balance:,.2f}'],
        ['Total Transactions', str(len(expenses))],
        ['Income Records', str(len(income_records))],
        ['Currency', currency]
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # SECTION 2: EXPENSES
    elements.append(Paragraph("Recent Expenses", heading_style))
    
    expense_data = [['Date', 'Category', 'Amount', 'Payment', 'Note']]
    for e in expenses[:20]:  # Show last 20 expenses
        amt = convert_amount(e.amount, currency)
        expense_data.append([
            e.date.strftime("%Y-%m-%d"),
            e.category,
            f'{currency}{amt:.2f}',
            e.payment_method,
            (e.note[:30] + '...') if e.note and len(e.note) > 30 else (e.note or '')
        ])
    
    if len(expense_data) > 1:
        expense_table = Table(expense_data, colWidths=[1*inch, 1.2*inch, 1*inch, 1*inch, 2.3*inch])
        expense_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(expense_table)
    else:
        elements.append(Paragraph("No expenses recorded yet.", styles['Normal']))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # SECTION 3: INCOME
    elements.append(Paragraph("Income Records", heading_style))
    
    income_data = [['Date', 'Source', 'Amount', 'Note']]
    for i in income_records[:15]:  # Show last 15 income records
        amt = convert_amount(i.amount, currency)
        income_data.append([
            i.date.strftime("%Y-%m-%d"),
            i.source,
            f'{currency}{amt:.2f}',
            (i.note[:40] + '...') if i.note and len(i.note) > 40 else (i.note or '')
        ])
    
    if len(income_data) > 1:
        income_table = Table(income_data, colWidths=[1.2*inch, 1.5*inch, 1.3*inch, 2.5*inch])
        income_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(income_table)
    else:
        elements.append(Paragraph("No income recorded yet.", styles['Normal']))
    
    elements.append(PageBreak())
    
    # SECTION 4: BUDGETS
    elements.append(Paragraph("Current Month Budgets", heading_style))
    
    budgets_list = Budget.query.filter_by(month=today_dt.month, year=today_dt.year).all()
    first_day = today.replace(day=1)
    month_expenses = Expense.query.filter(Expense.date >= first_day).all()
    cat_spending = defaultdict(float)
    for e in month_expenses:
        cat_spending[e.category] += convert_amount(e.amount, currency)
    
    budget_data = [['Category', 'Budget', 'Spent', 'Remaining', 'Usage %']]
    for b in budgets_list:
        b_amt = convert_amount(b.amount, currency)
        spent = cat_spending.get(b.category, 0)
        remaining = b_amt - spent
        usage_pct = (spent / b_amt * 100) if b_amt > 0 else 0
        budget_data.append([
            b.category,
            f'{currency}{b_amt:.2f}',
            f'{currency}{spent:.2f}',
            f'{currency}{remaining:.2f}',
            f'{usage_pct:.1f}%'
        ])
    
    if len(budget_data) > 1:
        budget_table = Table(budget_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1*inch])
        budget_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(budget_table)
    else:
        elements.append(Paragraph("No budgets set for current month.", styles['Normal']))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # SECTION 5: SAVINGS GOALS
    elements.append(Paragraph("Savings Goals", heading_style))
    
    savings_goals = SavingsGoal.query.all()
    savings_data = [['Goal Name', 'Current', 'Target', 'Progress %', 'Deadline']]
    for g in savings_goals:
        cur = convert_amount(g.current_amount, currency)
        tgt = convert_amount(g.target_amount, currency)
        pct = (cur / tgt * 100) if tgt > 0 else 0
        savings_data.append([
            g.name,
            f'{currency}{cur:.2f}',
            f'{currency}{tgt:.2f}',
            f'{pct:.1f}%',
            g.deadline.strftime("%Y-%m-%d") if g.deadline else "No deadline"
        ])
    
    if len(savings_data) > 1:
        savings_table = Table(savings_data, colWidths=[1.8*inch, 1.2*inch, 1.2*inch, 1*inch, 1.3*inch])
        savings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(savings_table)
    else:
        elements.append(Paragraph("No savings goals set.", styles['Normal']))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # SECTION 6: RECURRING EXPENSES
    elements.append(Paragraph("Recurring Expenses", heading_style))
    
    recurring_list = RecurringExpense.query.all()
    recurring_data = [['Name', 'Category', 'Amount', 'Frequency', 'Next Due', 'Status']]
    for r in recurring_list:
        r_amt = convert_amount(r.amount, currency)
        recurring_data.append([
            r.name,
            r.category,
            f'{currency}{r_amt:.2f}',
            r.frequency,
            r.next_due.strftime("%Y-%m-%d"),
            "Active" if r.is_active else "Paused"
        ])
    
    if len(recurring_data) > 1:
        recurring_table = Table(recurring_data, colWidths=[1.3*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
        recurring_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ec4899')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(recurring_table)
    else:
        elements.append(Paragraph("No recurring expenses set.", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    
    buffer.seek(0)
    filename = f"money_mate_report_{today_dt.strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )

@app.route("/clear", methods=["POST"])
@login_required
def clear_all():
    """Clear all expenses (use with caution)"""
    try:
        count = Expense.query.count()
        Expense.query.delete()
        db.session.commit()
        flash(f"Successfully cleared {count} expenses! 🗑️", "success")
    except Exception as e:
        db.session.rollback()
        print("Error clearing expenses:", e)
        flash("Error clearing expenses. Please try again.", "danger")
    return redirect("/")

@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    """Edit an existing expense"""
    expense = Expense.query.get_or_404(expense_id)
    all_expenses = Expense.query.all()
    categories = sorted(set(e.category for e in all_expenses))
    currency = get_currency()
    
    if request.method == "POST":
        try:
            expense.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            expense.category = request.form["category"].strip()
            expense.amount = float(request.form["amount"])
            expense.note = request.form.get("note", "").strip()
            expense.payment_method = request.form.get("payment_method", "cash")
            
            if expense.amount <= 0:
                flash("Amount must be greater than 0!", "danger")
                return render_template("edit.html", expense=expense, categories=categories)
            
            db.session.commit()
            flash("Expense successfully updated! ✅", "success")
            return redirect("/")
        except ValueError:
            flash("Invalid input. Please check your data.", "danger")
        except Exception as e:
            db.session.rollback()
            print("Error updating expense:", e)
            flash("Failed to update expense.", "danger")
    
    # Convert expense amount for display
    expense_data = {
        'id': expense.id,
        'date': expense.date,
        'category': expense.category,
        'amount': convert_amount(expense.amount, currency),
        'note': expense.note,
        'payment_method': expense.payment_method
    }
    
    return render_template("edit.html", expense=expense_data, categories=categories)

@app.route("/delete/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    """Delete an expense"""
    expense = Expense.query.get_or_404(expense_id)
    try:
        db.session.delete(expense)
        db.session.commit()
        flash("Expense successfully deleted! 🗑️", "success")
    except Exception as e:
        db.session.rollback()
        print("Error deleting expense:", e)
        flash("Failed to delete expense.", "danger")
    return redirect("/")

# API ROUTES
@app.route("/api/chart-data")
@login_required
def chart_data():
    """API endpoint for chart data"""
    currency = get_currency()
    all_expenses = Expense.query.all()
    category_totals = defaultdict(float)
    for e in all_expenses:
        category_totals[e.category] += convert_amount(e.amount, currency)
    
    return jsonify({
        'categories': list(category_totals.keys()),
        'amounts': list(category_totals.values())
    })

@app.route("/api/expense-stats")
@login_required
def expense_stats():
    """API endpoint for expense statistics"""
    currency = get_currency()
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    total_expenses = Expense.query.count()
    weekly_expenses = Expense.query.filter(Expense.date >= week_ago).count()
    monthly_expenses = Expense.query.filter(Expense.date >= month_ago).count()
    
    return jsonify({
        'total': total_expenses,
        'weekly': weekly_expenses,
        'monthly': monthly_expenses
    })

# AI Tips API (for dynamic personalized tips)
@app.route('/api/ai-tips', methods=['GET'])
@login_required
def ai_tips_api():
    """Generate personalized AI tips based on user data"""
    import time
    from google.genai import types
    
    page = request.args.get('page', 'budgets')
    currency = get_currency()
    
    try:
        # Gather user context based on page
        context_parts = []
        
        if page == 'budgets':
            today = datetime.now()
            budgets = Budget.query.filter_by(month=today.month, year=today.year).all()
            first_day = today.date().replace(day=1)
            month_expenses = Expense.query.filter(Expense.date >= first_day).all()
            cat_spending = defaultdict(float)
            for e in month_expenses:
                cat_spending[e.category] += float(e.amount)
            
            for b in budgets:
                spent = cat_spending.get(b.category, 0)
                pct = (spent / float(b.amount) * 100) if float(b.amount) > 0 else 0
                context_parts.append(f"- {b.category}: Budget {currency}{float(b.amount):,.2f}, Spent {currency}{spent:,.2f} ({pct:.0f}% used)")
            
            all_expenses = Expense.query.all()
            total_exp = sum(float(e.amount) for e in all_expenses)
            all_income = Income.query.all()
            total_inc = sum(float(i.amount) for i in all_income)
            
            context_str = "\n".join(context_parts) if context_parts else "No budgets set yet."
            prompt = f"""Based on this user's budget data, generate exactly 4 short personalized budgeting tips. Each tip should be 1 sentence max.

User's budgets this month:
{context_str}
Total income: {currency}{total_inc:,.2f}
Total expenses: {currency}{total_exp:,.2f}

Return ONLY the 4 tips, one per line, no numbering, no bullets, no extra text."""

        elif page == 'savings':
            savings = SavingsGoal.query.all()
            for s in savings:
                progress = (float(s.current_amount) / float(s.target_amount) * 100) if float(s.target_amount) > 0 else 0
                deadline_str = f" (Deadline: {s.deadline.strftime('%d %b %Y')})" if s.deadline else ""
                context_parts.append(f"- {s.name}: {currency}{float(s.current_amount):,.2f}/{currency}{float(s.target_amount):,.2f} ({progress:.0f}% done){deadline_str}")
            
            all_income = Income.query.all()
            total_inc = sum(float(i.amount) for i in all_income)
            
            context_str = "\n".join(context_parts) if context_parts else "No savings goals yet."
            prompt = f"""Based on this user's savings goals, generate exactly 4 short personalized saving tips. Each tip should be 1 sentence max.

User's savings goals:
{context_str}
Monthly income: {currency}{total_inc:,.2f}

Return ONLY the 4 tips, one per line, no numbering, no bullets, no extra text."""

        elif page == 'recurring':
            recurring = RecurringExpense.query.filter_by(is_active=True).all()
            total_monthly = 0
            for r in recurring:
                amt = float(r.amount)
                if r.frequency == 'daily':
                    monthly_cost = amt * 30
                elif r.frequency == 'weekly':
                    monthly_cost = amt * 4
                elif r.frequency == 'yearly':
                    monthly_cost = amt / 12
                else:
                    monthly_cost = amt
                total_monthly += monthly_cost
                context_parts.append(f"- {r.name}: {currency}{amt:,.2f}/{r.frequency} ({r.category}, due: {r.next_due.strftime('%d %b %Y')})")
            
            context_str = "\n".join(context_parts) if context_parts else "No recurring expenses yet."
            prompt = f"""Based on this user's recurring expenses, generate exactly 4 short personalized tips. Each tip should be 1 sentence max.

User's recurring expenses:
{context_str}
Estimated monthly cost: {currency}{total_monthly:,.2f}

Return ONLY the 4 tips, one per line, no numbering, no bullets, no extra text."""
        else:
            return jsonify({'success': False, 'error': 'Invalid page'})
        
        # Try models with fallback
        models_to_try = ['gemini-2.0-flash-lite', 'gemini-2.0-flash', 'gemini-2.5-flash']
        
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.8,
                        max_output_tokens=300
                    )
                )
                
                if response.text:
                    tips = [tip.strip() for tip in response.text.strip().split('\n') if tip.strip()]
                    return jsonify({'success': True, 'tips': tips})
            except Exception as e:
                print(f"Tips model {model_name} failed: {str(e)}")
                if '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e):
                    time.sleep(2)
                continue
        
        return jsonify({'success': False, 'error': 'AI service busy'})
        
    except Exception as e:
        print(f"Error generating tips: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

# AI Support API (for floating widget)
@app.route('/api/ai-support', methods=['POST'])
@login_required
@csrf.exempt
def ai_support_api():
    """API endpoint for AI chatbot using Google Gemini"""
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        history = data.get('history', [])
        
        if not user_message:
            return jsonify({'success': False, 'error': 'No message provided'})
        
        # Fetch comprehensive user stats to provide full context to the AI
        currency = session.get('currency', '₹')
        today = datetime.now().date()
        
        # Expenses
        all_expenses = Expense.query.all()
        all_income = Income.query.all()
        total_expense = sum(float(e.amount) for e in all_expenses)
        total_income = sum(float(i.amount) for i in all_income)
        
        category_totals = defaultdict(float)
        for e in all_expenses:
            category_totals[e.category] += float(e.amount)
        cat_stats = ", ".join([f"{cat}: {currency}{amt:,.2f}" for cat, amt in sorted(category_totals.items(), key=lambda x: x[1], reverse=True)])
        
        # Recent 5 expenses
        recent_expenses = Expense.query.order_by(Expense.date.desc()).limit(5).all()
        recent_exp_str = "\n".join([f"  - {e.date.strftime('%d %b')}: {e.category} - {currency}{float(e.amount):,.2f} ({e.note or 'no note'})" for e in recent_expenses])
        
        # Income sources
        income_sources = defaultdict(float)
        for i in all_income:
            income_sources[i.source] += float(i.amount)
        income_str = ", ".join([f"{src}: {currency}{amt:,.2f}" for src, amt in income_sources.items()])
        
        # Budgets (current month)
        current_month = today.month
        current_year = today.year
        budgets = Budget.query.filter_by(month=current_month, year=current_year).all()
        first_day = today.replace(day=1)
        month_exp = Expense.query.filter(Expense.date >= first_day).all()
        month_cat_spending = defaultdict(float)
        for e in month_exp:
            month_cat_spending[e.category] += float(e.amount)
        budget_str = "\n".join([f"  - {b.category}: Budget {currency}{float(b.amount):,.2f}, Spent {currency}{month_cat_spending.get(b.category, 0):,.2f} ({(month_cat_spending.get(b.category, 0)/float(b.amount)*100) if float(b.amount) > 0 else 0:.0f}% used)" for b in budgets]) if budgets else "  No budgets set"
        
        # Savings Goals
        savings = SavingsGoal.query.all()
        savings_str = "\n".join([f"  - {s.name}: {currency}{float(s.current_amount):,.2f}/{currency}{float(s.target_amount):,.2f} ({(float(s.current_amount)/float(s.target_amount)*100) if float(s.target_amount) > 0 else 0:.0f}% done){' - Deadline: ' + s.deadline.strftime('%d %b %Y') if s.deadline else ''}" for s in savings]) if savings else "  No savings goals"
        
        # Recurring Expenses
        recurring = RecurringExpense.query.filter_by(is_active=True).all()
        recurring_str = "\n".join([f"  - {r.name}: {currency}{float(r.amount):,.2f}/{r.frequency} (Next due: {r.next_due.strftime('%d %b %Y')})" for r in recurring]) if recurring else "  No recurring expenses"
        
        user_context = f"""

COMPLETE USER FINANCIAL DATA (Currency: {currency}):

OVERVIEW:
- Total Income: {currency}{total_income:,.2f}
- Total Expenses: {currency}{total_expense:,.2f}
- Net Balance: {currency}{total_income - total_expense:,.2f}

SPENDING BY CATEGORY: {cat_stats}

RECENT TRANSACTIONS:
{recent_exp_str or '  No transactions yet'}

INCOME SOURCES: {income_str or 'None recorded'}

CURRENT MONTH BUDGETS:
{budget_str}

SAVINGS GOALS:
{savings_str}

RECURRING EXPENSES:
{recurring_str}"""

        # System prompt
        system_prompt = f"""You are Money Mate AI Assistant, a helpful financial advisor chatbot for the Money Mate expense tracking application. 

Your role is to:
- Help users with budgeting, saving, and expense tracking
- Provide personalized financial advice based on their ACTUAL data shown below
- Answer questions about their spending patterns, budgets, savings progress, and recurring costs
- Reference specific numbers from their data when giving advice
- Be friendly, supportive, and encouraging

Keep responses concise and practical. Use emojis occasionally. Always base your advice on the user's real data.

{user_context}"""
        
        # Build conversation
        full_prompt = system_prompt + "\n\n"
        
        # Add conversation history (limit to last 10 messages)
        for msg in history[-10:]:
            if msg['role'] == 'user':
                full_prompt += f"User: {msg['content']}\n"
            elif msg['role'] == 'assistant':
                full_prompt += f"Assistant: {msg['content']}\n"
        
        # Add current message
        full_prompt += f"User: {user_message}\nAssistant:"
        
        # Use the configured Gemini client
        from google.genai import types
        import time
        
        # Build contents from history
        contents = []
        for msg in history[-10:]:
            role = 'user' if msg['role'] == 'user' else 'model'
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg['content'])]))
        
        # Add current message
        contents.append(types.Content(role='user', parts=[types.Part.from_text(text=user_message)]))
        
        # Try multiple models with retries for rate limiting (free tier has per-model quotas)
        models_to_try = ['gemini-2.0-flash-lite', 'gemini-2.0-flash', 'gemini-2.5-flash']
        last_error = None
        max_retries = 2
        
        for model_name in models_to_try:
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.7,
                            max_output_tokens=500
                        )
                    )
                    
                    if response.text:
                        return jsonify({
                            'success': True,
                            'response': response.text
                        })
                except Exception as model_error:
                    last_error = model_error
                    error_str = str(model_error)
                    print(f"Model {model_name} attempt {attempt+1} failed: {error_str}")
                    # If rate limited, wait before retrying the same model
                    if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                        if attempt < max_retries - 1:
                            time.sleep(3)
                            continue
                    break  # Non-rate-limit error, try next model
            time.sleep(1)  # Brief pause between models
        
        # All models failed
        print(f"All models failed. Last error: {last_error}")
        return jsonify({
            'success': False,
            'error': 'AI service is temporarily busy. Please wait a moment and try again.'
        })
            
    except Exception as e:
        print(f"Error in AI support: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'An error occurred processing your request'
        })


def generate_tips_on_login():
    """Generate tips for all pages on login and store in session"""
    from google.genai import types
    import time
    
    currency = get_currency()
    today = datetime.now()
    
    tips_data = {}
    
    # Generate tips for each page
    pages = ['budgets', 'savings', 'recurring']
    
    for page in pages:
        try:
            context_parts = []
            
            if page == 'budgets':
                budgets = Budget.query.filter_by(month=today.month, year=today.year).all()
                first_day = today.date().replace(day=1)
                month_expenses = Expense.query.filter(Expense.date >= first_day).all()
                cat_spending = defaultdict(float)
                for e in month_expenses:
                    cat_spending[e.category] += float(e.amount)
                
                for b in budgets:
                    spent = cat_spending.get(b.category, 0)
                    pct = (spent / float(b.amount) * 100) if float(b.amount) > 0 else 0
                    context_parts.append(f"- {b.category}: Budget {currency}{float(b.amount):,.2f}, Spent {currency}{spent:,.2f} ({pct:.0f}% used)")
                
                all_expenses = Expense.query.all()
                total_exp = sum(float(e.amount) for e in all_expenses)
                all_income = Income.query.all()
                total_inc = sum(float(i.amount) for i in all_income)
                
                context_str = "\n".join(context_parts) if context_parts else "No budgets set yet."
                prompt = f"""Based on this user's budget data, generate exactly 4 short personalized budgeting tips. Each tip should be 1 sentence max.

User's budgets this month:
{context_str}
Total income: {currency}{total_inc:,.2f}
Total expenses: {currency}{total_exp:,.2f}

Return ONLY the 4 tips, one per line, no numbering, no bullets, no extra text."""

            elif page == 'savings':
                savings = SavingsGoal.query.all()
                for s in savings:
                    progress = (float(s.current_amount) / float(s.target_amount) * 100) if float(s.target_amount) > 0 else 0
                    deadline_str = f" (Deadline: {s.deadline.strftime('%d %b %Y')})" if s.deadline else ""
                    context_parts.append(f"- {s.name}: {currency}{float(s.current_amount):,.2f}/{currency}{float(s.target_amount):,.2f} ({progress:.0f}% done){deadline_str}")
                
                all_income = Income.query.all()
                total_inc = sum(float(i.amount) for i in all_income)
                
                context_str = "\n".join(context_parts) if context_parts else "No savings goals yet."
                prompt = f"""Based on this user's savings goals, generate exactly 4 short personalized saving tips. Each tip should be 1 sentence max.

User's savings goals:
{context_str}
Monthly income: {currency}{total_inc:,.2f}

Return ONLY the 4 tips, one per line, no numbering, no bullets, no extra text."""

            elif page == 'recurring':
                recurring = RecurringExpense.query.filter_by(is_active=True).all()
                total_monthly = 0
                for r in recurring:
                    amt = float(r.amount)
                    if r.frequency == 'daily':
                        monthly_cost = amt * 30
                    elif r.frequency == 'weekly':
                        monthly_cost = amt * 4
                    elif r.frequency == 'yearly':
                        monthly_cost = amt / 12
                    else:
                        monthly_cost = amt
                    total_monthly += monthly_cost
                    context_parts.append(f"- {r.name}: {currency}{amt:,.2f}/{r.frequency} ({r.category}, due: {r.next_due.strftime('%d %b %Y')})")
                
                context_str = "\n".join(context_parts) if context_parts else "No recurring expenses yet."
                prompt = f"""Based on this user's recurring expenses, generate exactly 4 short personalized tips. Each tip should be 1 sentence max.

User's recurring expenses:
{context_str}
Estimated monthly cost: {currency}{total_monthly:,.2f}

Return ONLY the 4 tips, one per line, no numbering, no bullets, no extra text."""
            
            # Try models with fallback
            models_to_try = ['gemini-2.0-flash-lite', 'gemini-2.0-flash', 'gemini-2.5-flash']
            
            for model_name in models_to_try:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.8,
                            max_output_tokens=300
                        )
                    )
                    
                    if response.text:
                        tips = [tip.strip() for tip in response.text.strip().split('\n') if tip.strip()]
                        tips_data[page] = tips[:4]  # Ensure only 4 tips
                        break
                except Exception as e:
                    print(f"Tips model {model_name} failed for {page}: {str(e)}")
                    if '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e):
                        time.sleep(2)
                    continue
            
            # Fallback tips if AI fails
            if page not in tips_data:
                fallback = {
                    'budgets': [
                        'Set realistic budgets based on past spending',
                        'Review and adjust budgets monthly',
                        'Track variable expenses separately',
                        'Include savings as a budget category'
                    ],
                    'savings': [
                        'Set specific and measurable savings goals',
                        'Automate your savings with recurring transfers',
                        'Start with small amounts and increase gradually',
                        'Track your progress regularly to stay motivated'
                    ],
                    'recurring': [
                        'Review recurring expenses quarterly',
                        'Look for subscription services you no longer use',
                        'Negotiate better rates on regular bills',
                        'Set reminders before renewal dates'
                    ]
                }
                tips_data[page] = fallback.get(page, [])
        
        except Exception as e:
            print(f"Error generating tips for {page}: {str(e)}")
            # Use fallback
            fallback = {
                'budgets': [
                    'Set realistic budgets based on past spending',
                    'Review and adjust budgets monthly',
                    'Track variable expenses separately',
                    'Include savings as a budget category'
                ],
                'savings': [
                    'Set specific and measurable savings goals',
                    'Automate your savings with recurring transfers',
                    'Start with small amounts and increase gradually',
                    'Track your progress regularly to stay motivated'
                ],
                'recurring': [
                    'Review recurring expenses quarterly',
                    'Look for subscription services you no longer use',
                    'Negotiate better rates on regular bills',
                    'Set reminders before renewal dates'
                ]
            }
            tips_data[page] = fallback.get(page, [])
    
    return tips_data

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['login_success'] = True
            
            # Generate tips on login
            tips_data = generate_tips_on_login()
            session['ai_tips'] = tips_data
            
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
@csrf.exempt
def forgot_password():
    """Step 1: Request OTP for password reset"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        
        if not username:
            flash('Please enter your username', 'error')
            return render_template('forgot_password.html')
        
        user = User.query.filter_by(username=username).first()
        
        if not user:
            flash('Username not found', 'error')
            return render_template('forgot_password.html')
        
        if not user.email:
            flash('No email associated with this account', 'error')
            return render_template('forgot_password.html')
        
        # Generate 6-digit OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Store OTP in session with expiry (10 minutes)
        session['reset_otp'] = otp
        session['reset_username'] = username
        session['otp_expiry'] = (datetime.now() + timedelta(minutes=10)).isoformat()
        
        # Send OTP via email
        try:
            # Check if email is configured
            if app.config['MAIL_USERNAME'] == 'your-email@gmail.com' or not app.config.get('MAIL_USERNAME'):
                # Development mode - show OTP in console instead of sending email
                print("\n" + "="*60)
                print("🔐 DEVELOPMENT MODE - OTP FOR PASSWORD RESET")
                print("="*60)
                print(f"Username: {username}")
                print(f"Email: {user.email}")
                print(f"OTP Code: {otp}")
                print(f"Valid for: 10 minutes")
                print("="*60 + "\n")
                
                flash(f'Development Mode: Check console for OTP (Email: {user.email})', 'success')
                return redirect(url_for('verify_otp'))
            
            # Production mode - send actual email
            msg = Message(
                'Money Mate - Password Reset OTP',
                recipients=[user.email]
            )
            msg.html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <h2 style="color: #00d9b8; text-align: center;">Money Mate</h2>
                        <h3 style="color: #333;">Password Reset Request</h3>
                        <p style="color: #666; font-size: 16px;">Hello <strong>{username}</strong>,</p>
                        <p style="color: #666; font-size: 16px;">You requested to reset your password. Use the OTP below to proceed:</p>
                        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                            <h1 style="color: #00d9b8; letter-spacing: 8px; margin: 0; font-size: 36px;">{otp}</h1>
                        </div>
                        <p style="color: #666; font-size: 14px;">This OTP is valid for 10 minutes.</p>
                        <p style="color: #666; font-size: 14px;">If you didn't request this, please ignore this email.</p>
                        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                        <p style="color: #999; font-size: 12px; text-align: center;">Money Mate - Your Personal Finance Manager</p>
                    </div>
                </body>
            </html>
            """
            mail.send(msg)
            flash(f'OTP sent to {user.email[:3]}***{user.email.split("@")[1]}', 'success')
            return redirect(url_for('verify_otp'))
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            
            # Fallback to console mode if email fails
            print("\n" + "="*60)
            print("⚠️  EMAIL FAILED - SHOWING OTP IN CONSOLE")
            print("="*60)
            print(f"Username: {username}")
            print(f"Email: {user.email}")
            print(f"OTP Code: {otp}")
            print(f"Valid for: 10 minutes")
            print(f"Error: {str(e)}")
            print("="*60 + "\n")
            
            flash(f'Email service unavailable. Check console for OTP (Development Mode)', 'success')
            return redirect(url_for('verify_otp'))
    
    return render_template('forgot_password.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
@csrf.exempt
def verify_otp():
    """Step 2: Verify OTP"""
    if 'reset_username' not in session:
        flash('Please start the password reset process', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        entered_otp = request.form.get('otp', '').strip()
        
        # Check if OTP expired
        if 'otp_expiry' in session:
            expiry = datetime.fromisoformat(session['otp_expiry'])
            if datetime.now() > expiry:
                session.pop('reset_otp', None)
                session.pop('reset_username', None)
                session.pop('otp_expiry', None)
                flash('OTP expired. Please request a new one.', 'error')
                return redirect(url_for('forgot_password'))
        
        if entered_otp == session.get('reset_otp'):
            # OTP verified, allow password reset
            session['otp_verified'] = True
            return redirect(url_for('reset_password'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
    
    return render_template('verify_otp.html')

@app.route('/reset-password', methods=['GET', 'POST'])
@csrf.exempt
def reset_password():
    """Step 3: Reset password after OTP verification"""
    if not session.get('otp_verified'):
        flash('Please verify OTP first', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not new_password or not confirm_password:
            flash('Please fill in all fields', 'error')
            return render_template('reset_password.html')
        
        if new_password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html')
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('reset_password.html')
        
        username = session.get('reset_username')
        user = User.query.filter_by(username=username).first()
        
        if user:
            user.set_password(new_password)
            db.session.commit()
            
            # Clear session data
            session.pop('reset_otp', None)
            session.pop('reset_username', None)
            session.pop('otp_expiry', None)
            session.pop('otp_verified', None)
            
            flash('Password reset successfully! Please login with your new password.', 'success')
            return redirect(url_for('login'))
        else:
            flash('User not found', 'error')
            return redirect(url_for('forgot_password'))
    
    return render_template('reset_password.html')

@app.route('/signup', methods=['GET', 'POST'])
@csrf.exempt
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('signup.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('signup.html')
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))