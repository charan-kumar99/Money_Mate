from flask import Flask, render_template, request, redirect, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Expense model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200))

# Home route
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
        except Exception as e:
            print("Error adding expense:", e)
        return redirect("/")

    selected = request.args.get("filter", "")
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    categories = sorted(set(e.category for e in expenses))
    if selected:
        expenses = [e for e in expenses if e.category == selected]

    total = sum(e.amount for e in expenses)
    return render_template(
        "index.html",
        expenses=expenses,
        categories=categories,
        selected=selected,
        total=total
    )

# Upload CSV
@app.route("/upload", methods=["POST"])
def upload_csv():
    file = request.files.get("file")
    if file:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        for row in reader:
            try:
                date = datetime.strptime(row["Date"], "%Y-%m-%d").date()
                category = row["Category"]
                amount = float(row["Amount"])
                note = row.get("Note", "")
                new_expense = Expense(date=date, category=category, amount=amount, note=note)
                db.session.add(new_expense)
            except Exception as e:
                print("Error adding row:", e)
        db.session.commit()
    return redirect("/")

# Download CSV
@app.route("/export")
def export_csv():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Category", "Amount", "Note"])
    for e in expenses:
        writer.writerow([e.date.strftime("%Y-%m-%d"), e.category, e.amount, e.note])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="expenses.csv"
    )

# Clear All
@app.route("/clear", methods=["POST"])
def clear_all():
    try:
        Expense.query.delete()
        db.session.commit()
    except Exception as e:
        print("Error clearing expenses:", e)
    return redirect("/")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
