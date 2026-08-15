# 💰 Money Mate - Personal Finance Management Web Application

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20App-brightgreen?style=for-the-badge&logo=render)](https://money-mate-e33v.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-316192?style=for-the-badge&logo=postgresql)](https://neon.tech/)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange?style=for-the-badge&logo=google)](https://ai.google.dev/)

A modern, full-featured personal finance and expense tracking web application built with **Flask**, **SQLAlchemy**, and **Bootstrap 5**, integrated with **Sentinel API Security Lab** authentication and **Google Gemini AI** financial assistance.

---

## 🚀 Live Demo

**Experience Money Mate Live:** [https://money-mate-e33v.onrender.com](https://money-mate-e33v.onrender.com)

---

## ✨ Features Overview

### 🔐 1. Authentication & Security (Sentinel API)
- **Argon2id Authentication**: Secure registration and login powered by Sentinel API Security Lab.
- **6-Digit OTP Email Verification**: Verifies email authenticity on signup and password reset.
- **Resend OTP Support**: Instant one-click OTP resend mechanism.
- **Password Reset Flow**: Safe OTP-based password recovery.
- **CSRF Protection**: Form integrity protected via `Flask-WTF` CSRF tokens.

### 💳 2. Expense Tracking & Management
- **Quick Logging**: Add expenses with date, category, payment method, amount, and notes.
- **Multi-Filter Search**: Filter by category, payment method (Cash, Credit Card, Debit Card, Bank Transfer, Digital Wallet), and date ranges (7 days, 30 days, month, custom).
- **Sortable Records**: Sort transactions by date, amount, or category.
- **Full CRUD Support**: Edit or delete transactions with instant balance recalculation.

### 📊 3. Interactive Analytics & Visualizations
- **Income vs. Expenses**: Monthly comparative overview with net savings metrics.
- **12-Month Spending Trend**: Interactive Chart.js trend line chart.
- **Category Breakdown**: Dynamic pie charts showing spending distribution.
- **Payment Method Distribution**: Doughnut charts displaying payment method preferences.
- **Daily / Weekly / Monthly Averages**: Automated run-rate calculations.

### 💼 4. Category Budgeting & Smart Alerts
- **Monthly Category Limits**: Set customized spending budgets per category and month.
- **Visual Progress Bars**: Color-coded progress indicators (`success` < 80%, `warning` 80-99%, `danger` ≥ 100%).
- **Automated Email Alerts**: Automatic email notifications when spending reaches 80% or exceeds budget limits.

### 🎯 5. Savings Goals Tracker
- **Target Tracking**: Set targets, log contributions, and define optional target deadlines.
- **Progress Visuals**: Progress bars tracking completion percentage toward each financial milestone.
- **Celebration Confetti**: Dynamic particle animation triggers when any goal reaches 100% completion.

### 💵 6. Income Tracking
- **Multi-Source Logging**: Track salary, freelance, business, investments, and gifts.
- **Net Savings Calculation**: Automatic calculation of `Total Income - Total Expenses`.
- **Monthly Income Trends**: Visual representation of incoming cash flow over time.

### 🔄 7. Recurring Expenses & Bill Reminders
- **Subscription Management**: Track Netflix, Spotify, gym memberships, utilities, and rent.
- **Flexible Frequencies**: Daily, Weekly, Monthly, and Yearly intervals.
- **Next Due Tracking**: Automatic date tracking for upcoming billing cycles.
- **Email Reminders**: Automated email reminders sent 3 days before upcoming payments.
- **Active / Pause Toggles**: Temporarily pause subscriptions without deleting them.

### 🤖 8. Google Gemini AI Assistance
- **Floating AI Chatbot**: Interactive financial advisor with live context of your actual financial data (income, recent spending, budgets, savings goals).
- **Personalized Tips**: AI-generated suggestions tailored to your budget, savings goals, and recurring expenses.
- **Custom AI Personalities**: Configure AI tone in Settings (**Frugal**, **Balanced**, or **Ambitious**).

### 🏆 9. Gamification & Achievement Badges
- **10 Milestone Badges**: Unlock achievements for logging expenses, maintaining streaks, staying under budget, and hitting savings milestones.
- **Badge Showcase**: View unlocked badges and descriptions in the Settings dashboard.

### 💱 10. Multi-Currency Engine
- **Live Currency Conversion**: Real-time rates fetched from Open Exchange Rates and Frankfurter APIs.
- **Supported Currencies**: ₹ (INR), $ (USD), € (EUR), £ (GBP), ¥ (JPY).
- **Session & Profile Persistence**: Selected currency applies globally across all templates and reports.

### 📄 11. Complete Export Suite
- **Comprehensive CSV Export**: Exports complete expense, income, budget, savings, and summary datasets.
- **Formatted PDF Report**: Beautifully styled PDF reports generated with `ReportLab` featuring financial summary tables, expense lists, and budget usage metrics.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11, Flask 3.0, Gunicorn
- **Database & ORM**: PostgreSQL (Neon Cloud) / SQLite (Local), SQLAlchemy 2.0, Flask-Migrate (Alembic)
- **Security**: Sentinel API Security Lab, Flask-WTF CSRF, Werkzeug
- **AI & Integrations**: Google Gemini API (`google-genai` SDK), Requests
- **Document Generation**: ReportLab (PDF), Python CSV / IO
- **Email**: Flask-Mail (SMTP / Gmail)
- **Frontend**: HTML5, CSS3 (Custom Dark Theme), Bootstrap 5.3, Font Awesome 6, Chart.js, SweetAlert2, Canvas-Confetti

---

## 📦 Local Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/charan-kumar99/Money_Mate.git
cd Money_Mate
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```env
SECRET_KEY=your-random-secret-key
DATABASE_URL=sqlite:///money_mate.db
GEMINI_API_KEY=your-gemini-api-key-optional

# Email setup (Optional for production emails; console mode used if omitted)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-gmail-app-password
```

### 5. Run the Application
```bash
python app.py
```
Open your browser at `http://127.0.0.1:5000`.

---

## ☁️ Deployment (Render)

1. Push your repository to **GitHub**.
2. On [Render](https://render.com), create a new **Web Service** linked to your repo.
3. Configure the service:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Set the following **Environment Variables** in the Render Dashboard:
   - `SECRET_KEY`: A strong random string
   - `DATABASE_URL`: Your Neon PostgreSQL connection string (`postgresql://...`)
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `MAIL_USERNAME`: Gmail address (for email alerts/OTP)
   - `MAIL_PASSWORD`: Gmail App Password (16 characters)

---

## 📁 Project Structure

```
Money_Mate/
├── app.py              # Main Flask application, routes, AI & export logic
├── models.py           # SQLAlchemy database models & badge catalog
├── requirements.txt    # Production dependencies
├── runtime.txt         # Python runtime version for deployment (3.11.10)
├── Procfile            # Deployment process definition
├── static/
│   ├── style.css       # Custom styles and theme variables
│   └── charts.js       # Chart.js initialization and config
├── templates/
│   ├── base.html       # Base layout with sidebar, navbar, toasts & AI widget
│   ├── index.html      # Main dashboard & expense manager
│   ├── analytics.html  # Comprehensive analytics & visual reports
│   ├── budgets.html    # Category budget tracking & limits
│   ├── savings.html    # Financial goals & progress tracking
│   ├── income.html     # Income records & net savings
│   ├── recurring.html  # Recurring bills & subscription manager
│   ├── settings.html   # User preferences, AI settings & badge showcase
│   ├── edit.html       # Transaction editor
│   ├── login.html      # Sentinel API login
│   ├── signup.html     # Sentinel API registration
│   ├── verify_otp.html # 6-digit OTP verification
│   ├── forgot_password.html # Password reset initiation
│   └── reset_password.html  # Set new password
```

---

## 📄 License
This project is open-source and available under the MIT License.