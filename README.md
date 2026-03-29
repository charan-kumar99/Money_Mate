# 💰 Money Mate - Personal Finance Management Web Application

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Visit%20App-brightgreen?style=for-the-badge&logo=render)](https://money-mate-e33v.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-316192?style=for-the-badge&logo=postgresql)](https://neon.tech/)

A comprehensive web application built with Flask, providing powerful personal finance management tools. Features include expense tracking, advanced analytics, budgeting, savings goals, income tracking, and recurring expense management with multi-currency support.

## 🚀 Live Demo

**Try it now:** [https://money-mate-e33v.onrender.com](https://money-mate-e33v.onrender.com)

> 🎯 Create an account and start managing your finances today!

## ✨ Key Features

### 1. Income Tracking 📈
- Track income from multiple sources (Salary, Freelance, Business, etc.)
- View total income vs expenses
- Calculate net savings automatically
- Monthly income trend charts

### 2. Recurring Expenses 🔄
- Manage subscriptions and recurring payments
- Track due dates with reminders
- Pause/activate recurring expenses
- Calculate total monthly recurring costs
- Visual indicators for due/overdue payments

### 3. Multi-Currency Support 💱
- Support for ₹ (INR), $ (USD), € (EUR), £ (GBP), ¥ (JPY)
- Easy currency switching from sidebar
- Currency preference stored in session

### 4. Enhanced Analytics 📊
- Income vs Expenses comparison charts
- 12-month trend analysis
- Category breakdown with percentages
- Payment method distribution
- Daily, weekly, and monthly averages

### 5. Improved Budget Management 💼
- Visual progress bars with color coding
- Total budget overview
- Real-time spending tracking
- Budget alerts (80%, 100% thresholds)

### 6. Enhanced Savings Goals 🎯
- Progress tracking with visual indicators
- Deadline management with countdown
- Multiple concurrent goals
- Completed goal celebrations
- Overall progress calculation

### 7. Better User Experience ✨
- Auto-dismissing flash messages
- Smooth animations and transitions
- Improved card layouts
- Better color scheme and gradients
- Loading states and error handling
- Responsive mobile design

### 8. Security Improvements 🔒
- CSRF protection on all forms
- Input sanitization
- SQL injection prevention
- XSS protection

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Step 1: Clone the Project
```bash
git clone https://github.com/charan-kumar99/Money_Mate.git
cd Money_Mate
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
# Install all dependencies from requirements.txt
pip install -r requirements.txt
```

### Step 4: Initialize Database
```bash
# Create migrations folder (if not exists)
flask db init

# Create migration
flask db migrate -m "Initial migration"

# Apply migration
flask db upgrade
```

### Step 5: Run the Application
```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000`

## 📁 Project Structure

```
Money_Mate/
├── app.py                 # Main application file
├── models.py              # Database models
├── requirements.txt       # Python dependencies
├── templates/
│   ├── base.html         # Base template
│   ├── index.html        # Dashboard
│   ├── analytics.html    # Analytics page
│   ├── budgets.html      # Budget management
│   ├── savings.html      # Savings goals
│   ├── income.html       # Income tracking
│   └── recurring.html    # Recurring expenses
├── static/
│   └── style.css         # Custom styles
├── migrations/           # Database migrations
└── instance/
    └── expenses.db       # SQLite database (auto-created)
```

## 🎨 Features Overview

### Dashboard
- Quick expense entry form
- Real-time statistics (Total, Income, Net Savings)
- Advanced filters (Category, Payment Method, Date Range, Search)
- Sortable expense list
- Top categories chart
- Monthly spending trend
- CSV export functionality

### Analytics
- Total income and expenses overview
- Income vs Expenses comparison (12 months)
- Category breakdown (pie chart)
- Payment methods distribution
- Detailed category statistics table
- Daily, weekly, and monthly averages

### Budget Management
- Create category-based budgets
- Visual progress indicators
- Budget alerts (color-coded)
- Total budget overview
- Monthly budget tracking
- Budget tips and suggestions

### Savings Goals
- Set multiple savings goals
- Track progress with visual bars
- Deadline management
- Overall savings progress
- Easy updates to current amounts
- Completion indicators

### Income Tracking
- Record income from various sources
- Monthly income trends
- Income vs Expenses comparison
- Net savings calculation
- Easy income management

### Recurring Expenses
- Track subscriptions and recurring payments
- Due date reminders
- Frequency management (Daily, Weekly, Monthly, Yearly)
- Pause/activate feature
- Visual due date indicators
- Total monthly recurring cost calculation

## 🔧 Configuration

### Change Secret Key (Important for Production!)
In `app.py`, change:
```python
app.config['SECRET_KEY'] = 'your_secret_key_here_change_in_production'
```
To a strong, random secret key:
```python
app.config['SECRET_KEY'] = 'your-actual-secret-key-here'
```

### Database Configuration
Default uses SQLite. To use PostgreSQL or MySQL:
```python
# PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/dbname'

# MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://username:password@localhost/dbname'
```

## 🎯 Usage Tips

### Best Practices
1. **Regular Updates**: Add expenses daily for accurate tracking
2. **Categorize Properly**: Use consistent category names
3. **Set Realistic Budgets**: Base budgets on historical spending
4. **Track Income**: Record all income sources for accurate net savings
5. **Review Analytics**: Check analytics monthly to identify spending patterns
6. **Use Recurring**: Set up all subscriptions and recurring payments
7. **Set Goals**: Create savings goals to stay motivated

### Quick Actions
- **Add Expense**: Use the left sidebar form on Dashboard
- **View Analytics**: Click Analytics in the sidebar
- **Set Budget**: Go to Budgets page and enter category + amount
- **Track Income**: Use Income page to record all income
- **Manage Subscriptions**: Use Recurring page for subscriptions

## 🐛 Troubleshooting

### Database Errors
```bash
# Reset database
flask db downgrade
flask db upgrade

# Or delete database and recreate (Windows)
del instance\expenses.db
flask db upgrade

# Linux/Mac
rm instance/expenses.db
flask db upgrade
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### Port Already in Use
```python
# In app.py, change the port
if __name__ == "__main__":
    app.run(debug=True, port=5001)  # Change 5000 to 5001
```

## 🔐 Security Notes

### Web Application Security
- ✅ CSRF protection enabled on all forms
- ✅ SQL injection prevention through SQLAlchemy ORM
- ✅ Input validation and sanitization
- ✅ Secure session management
- ✅ XSS protection

### Production Considerations
- ⚠️ Change SECRET_KEY in production
- ⚠️ Set debug=False in production
- ⚠️ Use HTTPS/SSL in production
- ⚠️ Implement proper error logging
- ⚠️ Use a production-grade database (PostgreSQL/MySQL)
- ⚠️ Set up proper backup strategies

## 📱 Browser Support

- ✅ Chrome (Recommended)
- ✅ Firefox
- ✅ Safari
- ✅ Edge
- ✅ Mobile browsers (Responsive design)

## 🎨 Customization

### Change Theme Colors
Edit `static/style.css`:
```css
:root {
    --primary: #6366f1;        /* Primary color */
    --success: #10b981;         /* Success color */
    --danger: #ef4444;          /* Danger color */
    --background: #0f172a;      /* Background color */
}
```

### Add New Categories
Categories are dynamically created. Just type a new category name when adding an expense!

### Payment Methods
Available payment methods:
- Cash
- Credit Card
- Debit Card
- Bank Transfer
- Digital Wallet

## 📈 Future Enhancements (Roadmap)

- [ ] User authentication and multi-user support
- [ ] Email notifications for budgets and due dates
- [ ] PDF export for reports
- [ ] Mobile app (React Native/Flutter)
- [ ] Bank account integration
- [ ] Receipt photo upload
- [ ] Advanced forecasting and predictions
- [ ] Shared budgets for families
- [ ] Tax calculation features
- [ ] Investment tracking

## 📄 License

This project is open source and available for personal and commercial use.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 👨‍💻 Author

Created with ❤️ by Charan Kumar for better financial management

## 📞 Support

If you encounter any issues:
1. Check the Troubleshooting section
2. Ensure all dependencies are installed correctly
3. Verify database migrations are applied
4. Check the console for error messages

## 🎉 Acknowledgments

- Flask Framework
- Bootstrap 5
- Font Awesome Icons
- Chart.js
- SQLAlchemy

---

**Version:** 2.0.0  
**Last Updated:** January 2025  
**Status:** ✅ Production Ready

Happy expense tracking! 💰📊✨