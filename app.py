from flask import Flask, render_template, request, redirect, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import csv
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'
db = SQLAlchemy(app)

# Make datetime available in all templates
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            category = request.form["category"]
            amount = float(request.form["amount"])
            note = request.form["note"]
            new_expense = Expense(date=date, category=category, amount=amount, note=note)
            db.session.add(new_expense)
            db.session.commit()
            flash("Expense added successfully!", "success")
        except Exception as e:
            print("Error adding expense:", e)
            flash("Error adding expense. Please try again.", "danger")
        return redirect("/")

    # Get filter parameters
    category_filter = request.args.get("category_filter", "")
    date_filter = request.args.get("date_filter", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    
    # Base query
    expenses = Expense.query.order_by(Expense.date.desc())
    
    # Apply date filtering
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
    
    expenses = expenses.all()
    
    # Get all categories for dropdown
    all_expenses = Expense.query.all()
    categories = sorted(set(e.category for e in all_expenses))
    
    # Apply category filtering
    if category_filter:
        expenses = [e for e in expenses if e.category == category_filter]

    total = sum(e.amount for e in expenses)
    
    # Get current date for the form default
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    return render_template(
        "index.html",
        expenses=expenses,
        categories=categories,
        category_filter=category_filter,
        date_filter=date_filter,
        start_date=start_date,
        end_date=end_date,
        total=total,
        current_date=current_date
    )

@app.route("/upload", methods=["POST"])
def upload_csv():
    file = request.files.get("file")
    if file:
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            reader = csv.DictReader(stream)
            count = 0
            for row in reader:
                try:
                    date = datetime.strptime(row["Date"], "%Y-%m-%d").date()
                    category = row["Category"]
                    amount = float(row["Amount"])
                    note = row.get("Note", "")
                    new_expense = Expense(date=date, category=category, amount=amount, note=note)
                    db.session.add(new_expense)
                    count += 1
                except Exception as e:
                    print("Error adding row:", e)
            db.session.commit()
            flash(f"Successfully uploaded {count} expenses!", "success")
        except Exception as e:
            print("Error uploading CSV:", e)
            flash("Error uploading CSV file. Please check the format.", "danger")
    else:
        flash("No file selected.", "warning")
    return redirect("/")

@app.route("/export")
def export_csv():
    # Get same filters as index page
    category_filter = request.args.get("category_filter", "")
    date_filter = request.args.get("date_filter", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    
    # Apply same filtering logic
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
    
    expenses = expenses.all()
    
    if category_filter:
        expenses = [e for e in expenses if e.category == category_filter]
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Category", "Amount", "Note"])
    for e in expenses:
        writer.writerow([e.date.strftime("%Y-%m-%d"), e.category, e.amount, e.note or ""])
    output.seek(0)
    
    filename = "expenses.csv"
    if date_filter:
        filename = f"expenses_{date_filter}.csv"
    if category_filter:
        filename = f"expenses_{category_filter.lower()}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )

@app.route("/clear", methods=["POST"])
def clear_all():
    try:
        count = Expense.query.count()
        Expense.query.delete()
        db.session.commit()
        flash(f"Successfully cleared {count} expenses!", "success")
    except Exception as e:
        print("Error clearing expenses:", e)
        flash("Error clearing expenses. Please try again.", "danger")
    return redirect("/")

@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if request.method == "POST":
        try:
            expense.date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            expense.category = request.form["category"]
            expense.amount = float(request.form["amount"])
            expense.note = request.form["note"]
            db.session.commit()
            flash("Expense successfully updated!", "success")
            return redirect("/")
        except Exception as e:
            print("Error updating expense:", e)
            flash("Failed to update expense.", "danger")
    
    # Pass current_date for the edit form as well
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template("edit.html", expense=expense, current_date=current_date)

@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    try:
        db.session.delete(expense)
        db.session.commit()
        flash("Expense successfully deleted!", "success")
    except Exception as e:
        print("Error deleting expense:", e)
        flash("Failed to delete expense.", "danger")
    return redirect("/")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)