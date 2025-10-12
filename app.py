from flask import Flask, render_template, request, redirect, send_file, flash, jsonify, session
from datetime import datetime, timedelta
from collections import defaultdict
import csv
import io
import calendar
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from models import db, Expense, Budget, SavingsGoal, Income, RecurringExpense
from calendar import monthrange
from werkzeug.security import generate_password_hash
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here_change_in_production'
app.config['WTF_CSRF_TIME_LIMIT'] = None
db.init_app(app)
migrate = Migrate(app, db)
csrf = CSRFProtect(app)

# Default currency - can be changed by user
def get_currency():
    return session.get('currency', '₹')

def set_currency(currency):
    session['currency'] = currency

def get_month_range(year, month):
    """Get the first and last day of a given month"""
    start = datetime(year, month, 1).date()
    last_day = monthrange(year, month)[1]
    end = datetime(year, month, last_day).date()
    return start, end

@app.context_processor
def inject_global_vars():
    """Inject global variables into all templates"""
    return {
        'datetime': datetime,
        'currency': get_currency(),
        'get_currency': get_currency  # Make the function available in templates
    }

@app.route("/set_currency/<currency>")
def set_currency_route(currency):
    """Change the display currency"""
    valid_currencies = ['₹', '$', '€', '£', '¥']
    if currency in valid_currencies:
        set_currency(currency)
        flash(f"Currency changed to {currency}", "success")
    return redirect(request.referrer or '/')

@app.route("/", methods=["GET", "POST"])
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
    total = sum(float(e.amount) for e in expenses)
    
    # Get all categories for dropdown
    all_expenses = Expense.query.all()
    categories = sorted(set(e.category for e in all_expenses))
    
    # Calculate category and payment totals
    category_totals = defaultdict(float)
    payment_totals = defaultdict(float)
    for e in expenses:
        category_totals[e.category] += float(e.amount)
        payment_totals[e.payment_method] += float(e.amount)
    
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
        monthly_data.append({
            'month': month_name,
            'total': float(month_total)
        })
        monthly_labels.append(month_name)
        monthly_totals.append(float(month_total))
    
    # Get income and expenses for current month
    first_day_of_month = today.replace(day=1)
    month_income = db.session.query(db.func.sum(Income.amount)).filter(
        Income.date >= first_day_of_month
    ).scalar() or 0
    
    month_expenses_total = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.date >= first_day_of_month
    ).scalar() or 0
    
    net_savings = float(month_income) - float(month_expenses_total)
    
    return render_template(
        "index.html",
        expenses=expenses,
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
        month_income=float(month_income),
        net_savings=net_savings
    )

@app.route("/analytics")
def analytics():
    """Comprehensive analytics and insights page"""
    all_expenses = Expense.query.all()
    total_expenses = sum(float(e.amount) for e in all_expenses)
    expense_count = len(all_expenses)
    
    # Get total income
    all_income = Income.query.all()
    total_income = sum(float(i.amount) for i in all_income)
    
    category_totals = defaultdict(float)
    category_counts = defaultdict(int)
    payment_totals = defaultdict(float)
    
    for e in all_expenses:
        category_totals[e.category] += float(e.amount)
        category_counts[e.category] += 1
        payment_totals[e.payment_method] += float(e.amount)
    
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
        
        monthly_trend.append({
            'month': start.strftime('%b %Y'),
            'total': float(month_total),
            'income': float(month_income),
            'count': month_count,
            'savings': float(month_income) - float(month_total)
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
def budgets():
    """Budget management page"""
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
        category_spending[e.category] += float(e.amount)
    
    budget_data = []
    total_budget = 0
    total_spent = 0
    
    for budget in budgets:
        spent = category_spending.get(budget.category, 0)
        remaining = float(budget.amount) - spent
        percentage = (spent / float(budget.amount) * 100) if float(budget.amount) > 0 else 0
        
        # Determine status color
        status = "success" if percentage < 80 else "warning" if percentage < 100 else "danger"
        
        budget_data.append({
            'id': budget.id,
            'category': budget.category,
            'budget': float(budget.amount),
            'spent': spent,
            'remaining': remaining,
            'percentage': percentage,
            'status': status
        })
        
        total_budget += float(budget.amount)
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
def savings():
    """Savings goals management"""
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
    
    # Calculate total savings progress
    total_target = sum(float(g.target_amount) for g in savings_goals)
    total_current = sum(float(g.current_amount) for g in savings_goals)
    
    return render_template(
        "savings.html",
        savings_goals=savings_goals,
        total_target=total_target,
        total_current=total_current
    )

@app.route("/income", methods=["GET", "POST"])
def income():
    """Income tracking and management"""
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
    total_income = sum(float(i.amount) for i in income_records)
    
    # Get all expenses for comparison
    total_expenses = sum(float(e.amount) for e in Expense.query.all())
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
            'total': float(month_total)
        })
    
    return render_template(
        "income.html",
        income_records=income_records,
        total_income=total_income,
        total_expenses=total_expenses,
        net_savings=net_savings,
        monthly_income=monthly_income
    )

@app.route("/recurring", methods=["GET", "POST"])
def recurring():
    """Recurring expenses management"""
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
    
    return render_template(
        "recurring.html",
        recurring_expenses=recurring_expenses,
        categories=categories
    )

# DELETE ROUTES
@app.route("/delete_income/<int:income_id>", methods=["POST"])
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

@app.route("/upload", methods=["POST"])
def upload_csv():
    """Upload and process CSV file with expenses"""
    file = request.files.get("file")
    if file:
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            reader = csv.DictReader(stream)
            required_headers = ["Date", "Category", "Amount"]
            
            if not all(header in reader.fieldnames for header in required_headers):
                flash("CSV must contain Date, Category, and Amount columns.", "danger")
                return redirect("/")
            
            count = 0
            errors = 0
            for row in reader:
                try:
                    date = datetime.strptime(row["Date"].strip(), "%Y-%m-%d").date()
                    category = row["Category"].strip()
                    amount = float(row["Amount"])
                    note = row.get("Note", "").strip()
                    payment_method = row.get("Payment Method", "cash").strip().lower()
                    
                    if amount > 0 and category:
                        new_expense = Expense(
                            date=date,
                            category=category,
                            amount=amount,
                            note=note,
                            payment_method=payment_method
                        )
                        db.session.add(new_expense)
                        count += 1
                    else:
                        errors += 1
                except Exception as e:
                    print("Error adding row:", e)
                    errors += 1
            
            db.session.commit()
            flash(f"Successfully uploaded {count} expenses! {errors} rows skipped.", "success")
        except Exception as e:
            db.session.rollback()
            print("Error uploading CSV:", e)
            flash("Error uploading CSV file. Please check the format.", "danger")
    else:
        flash("No file selected.", "warning")
    return redirect("/")

@app.route("/export")
def export_csv():
    """Export expenses to CSV file"""
    category_filter = request.args.get("category_filter", "")
    date_filter = request.args.get("date_filter", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    search_query = request.args.get("search_query", "")
    payment_filter = request.args.get("payment_filter", "")
    
    expenses = Expense.query.order_by(Expense.date.desc())
    
    today = datetime.now().date()
    if date_filter == "last_7_days":
        seven_days_ago = today - timedelta(days=7)
        expenses = expenses.filter(Expense.date >= seven_days_ago)
    elif date_filter == "this_month":
        first_day_of_month = today.replace(day=1)
        expenses = expenses.filter(Expense.date >= first_day_of_month)
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
    
    expenses = expenses.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Category", "Amount", "Note", "Payment Method"])
    for e in expenses:
        writer.writerow([
            e.date.strftime("%Y-%m-%d"),
            e.category,
            float(e.amount),
            e.note or "",
            e.payment_method
        ])
    output.seek(0)
    
    filename = f"expenses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )

@app.route("/clear", methods=["POST"])
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
def edit_expense(expense_id):
    """Edit an existing expense"""
    expense = Expense.query.get_or_404(expense_id)
    all_expenses = Expense.query.all()
    categories = sorted(set(e.category for e in all_expenses))
    
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
    
    return render_template("edit.html", expense=expense, categories=categories)

@app.route("/delete/<int:expense_id>", methods=["POST"])
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
def chart_data():
    """API endpoint for chart data"""
    all_expenses = Expense.query.all()
    category_totals = defaultdict(float)
    for e in all_expenses:
        category_totals[e.category] += float(e.amount)
    
    return jsonify({
        'categories': list(category_totals.keys()),
        'amounts': list(category_totals.values())
    })

@app.route("/api/expense-stats")
def expense_stats():
    """API endpoint for expense statistics"""
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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)