# Money Mate Database Schema Documentation

## Overview
This document describes all tables, columns, and relationships in the Money Mate PostgreSQL database.

---

## Tables Summary

| Table Name | Purpose | Records |
|------------|---------|---------|
| user | User authentication and profiles | User accounts |
| expense | Daily expense transactions | All expenses |
| budget | Monthly budget limits | Budget per category/month |
| savings_goal | Savings goals tracking | Financial goals |
| income | Income transactions | All income sources |
| recurring_expense | Recurring/subscription expenses | Subscriptions & bills |

---

## Table 1: USER
**Purpose:** Store user authentication and profile information

### Columns:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique user identifier |
| username | VARCHAR(80) | UNIQUE, NOT NULL | Login username |
| email | VARCHAR(120) | UNIQUE, NOT NULL | User email address |
| password_hash | VARCHAR(255) | NOT NULL | Hashed password (bcrypt) |
| created_at | TIMESTAMP | DEFAULT NOW | Account creation date |

### Indexes:
- `idx_user_username` on username
- `idx_user_email` on email

### Sample Data:
```sql
username: 'user'
email: 'user@moneymate.com'
password: 'passw0rd' (hashed)
```

---

## Table 2: EXPENSE
**Purpose:** Track all expense transactions

### Columns:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique expense ID |
| date | DATE | NOT NULL | Transaction date |
| category | VARCHAR(50) | NOT NULL | Expense category |
| amount | NUMERIC(10,2) | NOT NULL, >= 0 | Expense amount |
| note | VARCHAR(200) | NULLABLE | Optional description |
| payment_method | VARCHAR(20) | DEFAULT 'cash' | Payment type |
| created_at | TIMESTAMP | DEFAULT NOW | Record creation time |

### Payment Methods:
- cash
- credit_card
- debit_card
- bank_transfer
- digital_wallet

### Common Categories:
- Food & Dining
- Transportation
- Shopping
- Entertainment
- Bills & Utilities
- Healthcare
- Education
- Travel
- Personal Care
- Other

### Indexes:
- `idx_expense_date` on date
- `idx_expense_category` on category
- `idx_expense_payment_method` on payment_method
- `idx_expense_date_category` on (date, category)

### Sample Query:
```sql
-- Get total expenses by category this month
SELECT category, SUM(amount) as total
FROM expense
WHERE date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY category
ORDER BY total DESC;
```

---

## Table 3: BUDGET
**Purpose:** Set and track monthly budget limits per category

### Columns:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique budget ID |
| category | VARCHAR(50) | NOT NULL | Budget category |
| amount | NUMERIC(10,2) | NOT NULL, >= 0 | Budget limit |
| month | INTEGER | 1-12 | Month number |
| year | INTEGER | >= 2000 | Year |
| created_at | TIMESTAMP | DEFAULT NOW | Record creation time |

### Constraints:
- UNIQUE (category, month, year) - One budget per category per month
- month BETWEEN 1 AND 12
- year >= 2000

### Indexes:
- `idx_budget_month_year` on (month, year)
- `idx_budget_category` on category

### Sample Query:
```sql
-- Get current month's budgets with spending
SELECT 
    b.category,
    b.amount as budget,
    COALESCE(SUM(e.amount), 0) as spent,
    b.amount - COALESCE(SUM(e.amount), 0) as remaining
FROM budget b
LEFT JOIN expense e ON b.category = e.category 
    AND EXTRACT(MONTH FROM e.date) = b.month
    AND EXTRACT(YEAR FROM e.date) = b.year
WHERE b.month = EXTRACT(MONTH FROM CURRENT_DATE)
    AND b.year = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY b.id, b.category, b.amount;
```

---

## Table 4: SAVINGS_GOAL
**Purpose:** Track savings goals and progress

### Columns:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique goal ID |
| name | VARCHAR(100) | NOT NULL | Goal name/description |
| target_amount | NUMERIC(10,2) | NOT NULL, > 0 | Target amount to save |
| current_amount | NUMERIC(10,2) | DEFAULT 0, >= 0 | Current saved amount |
| deadline | DATE | NULLABLE | Target completion date |
| created_at | TIMESTAMP | DEFAULT NOW | Goal creation date |

### Calculated Fields (in application):
- `progress_percentage` = (current_amount / target_amount) * 100
- `is_completed` = current_amount >= target_amount

### Indexes:
- `idx_savings_goal_deadline` on deadline
- `idx_savings_goal_name` on name

### Sample Query:
```sql
-- Get all active savings goals with progress
SELECT 
    name,
    target_amount,
    current_amount,
    ROUND((current_amount / target_amount * 100)::numeric, 2) as progress_pct,
    deadline,
    CASE 
        WHEN current_amount >= target_amount THEN 'Completed'
        WHEN deadline < CURRENT_DATE THEN 'Overdue'
        ELSE 'In Progress'
    END as status
FROM savings_goal
ORDER BY deadline ASC NULLS LAST;
```

---

## Table 5: INCOME
**Purpose:** Track all income transactions

### Columns:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique income ID |
| date | DATE | NOT NULL | Income date |
| source | VARCHAR(50) | NOT NULL | Income source |
| amount | NUMERIC(10,2) | NOT NULL, >= 0 | Income amount |
| note | VARCHAR(200) | NULLABLE | Optional description |
| created_at | TIMESTAMP | DEFAULT NOW | Record creation time |

### Common Income Sources:
- Salary
- Freelance
- Business
- Investment
- Gift
- Bonus
- Other

### Indexes:
- `idx_income_date` on date
- `idx_income_source` on source
- `idx_income_date_source` on (date, source)

### Sample Query:
```sql
-- Get monthly income vs expenses
SELECT 
    TO_CHAR(date, 'YYYY-MM') as month,
    SUM(amount) as total_income,
    (SELECT SUM(amount) FROM expense 
     WHERE TO_CHAR(date, 'YYYY-MM') = TO_CHAR(i.date, 'YYYY-MM')) as total_expenses,
    SUM(amount) - (SELECT COALESCE(SUM(amount), 0) FROM expense 
     WHERE TO_CHAR(date, 'YYYY-MM') = TO_CHAR(i.date, 'YYYY-MM')) as net_savings
FROM income i
GROUP BY TO_CHAR(date, 'YYYY-MM')
ORDER BY month DESC;
```

---

## Table 6: RECURRING_EXPENSE
**Purpose:** Manage recurring expenses and subscriptions

### Columns:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique recurring expense ID |
| name | VARCHAR(100) | NOT NULL | Expense name |
| category | VARCHAR(50) | NOT NULL | Category |
| amount | NUMERIC(10,2) | NOT NULL, >= 0 | Recurring amount |
| frequency | VARCHAR(20) | NOT NULL | Frequency type |
| next_due | DATE | NOT NULL | Next due date |
| is_active | BOOLEAN | DEFAULT TRUE | Active status |
| created_at | TIMESTAMP | DEFAULT NOW | Record creation time |

### Frequency Values:
- daily
- weekly
- monthly
- yearly

### Indexes:
- `idx_recurring_expense_next_due` on next_due
- `idx_recurring_expense_is_active` on is_active
- `idx_recurring_expense_category` on category

### Sample Query:
```sql
-- Get all active recurring expenses due this month
SELECT 
    name,
    category,
    amount,
    frequency,
    next_due,
    CASE 
        WHEN next_due < CURRENT_DATE THEN 'Overdue'
        WHEN next_due <= CURRENT_DATE + INTERVAL '7 days' THEN 'Due Soon'
        ELSE 'Upcoming'
    END as status
FROM recurring_expense
WHERE is_active = TRUE
    AND next_due <= DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month'
ORDER BY next_due ASC;
```

---

## Database Relationships

Currently, the database uses a simple structure without foreign keys between tables. This is intentional for flexibility:

- **user** table is independent (for future multi-user support)
- **expense**, **income**, **budget**, **savings_goal**, **recurring_expense** are independent
- Relationships are managed at the application level

### Future Enhancements:
If you want to add user-specific data:
```sql
-- Add user_id to all tables
ALTER TABLE expense ADD COLUMN user_id INTEGER REFERENCES "user"(id);
ALTER TABLE income ADD COLUMN user_id INTEGER REFERENCES "user"(id);
ALTER TABLE budget ADD COLUMN user_id INTEGER REFERENCES "user"(id);
ALTER TABLE savings_goal ADD COLUMN user_id INTEGER REFERENCES "user"(id);
ALTER TABLE recurring_expense ADD COLUMN user_id INTEGER REFERENCES "user"(id);
```

---

## Common Queries

### 1. Dashboard Statistics
```sql
-- Get current month overview
SELECT 
    (SELECT COUNT(*) FROM expense WHERE date >= DATE_TRUNC('month', CURRENT_DATE)) as expense_count,
    (SELECT COALESCE(SUM(amount), 0) FROM expense WHERE date >= DATE_TRUNC('month', CURRENT_DATE)) as total_expenses,
    (SELECT COALESCE(SUM(amount), 0) FROM income WHERE date >= DATE_TRUNC('month', CURRENT_DATE)) as total_income,
    (SELECT COALESCE(SUM(amount), 0) FROM income WHERE date >= DATE_TRUNC('month', CURRENT_DATE)) - 
    (SELECT COALESCE(SUM(amount), 0) FROM expense WHERE date >= DATE_TRUNC('month', CURRENT_DATE)) as net_savings;
```

### 2. Top Spending Categories
```sql
SELECT 
    category,
    COUNT(*) as transaction_count,
    SUM(amount) as total_spent,
    AVG(amount) as avg_per_transaction
FROM expense
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY category
ORDER BY total_spent DESC
LIMIT 5;
```

### 3. Budget Performance
```sql
SELECT 
    b.category,
    b.amount as budget,
    COALESCE(SUM(e.amount), 0) as spent,
    ROUND(((COALESCE(SUM(e.amount), 0) / b.amount) * 100)::numeric, 2) as usage_pct
FROM budget b
LEFT JOIN expense e ON b.category = e.category 
    AND EXTRACT(MONTH FROM e.date) = b.month
    AND EXTRACT(YEAR FROM e.date) = b.year
WHERE b.month = EXTRACT(MONTH FROM CURRENT_DATE)
    AND b.year = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY b.category, b.amount
ORDER BY usage_pct DESC;
```

---

## Maintenance Queries

### Backup Database
```bash
pg_dump -U postgres money_mate > money_mate_backup.sql
```

### Restore Database
```bash
psql -U postgres money_mate < money_mate_backup.sql
```

### View Table Sizes
```sql
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Vacuum and Analyze
```sql
VACUUM ANALYZE;
```

---

## Security Considerations

1. **Password Storage**: Always use hashed passwords (werkzeug.security)
2. **SQL Injection**: Use parameterized queries (SQLAlchemy ORM handles this)
3. **Input Validation**: Validate all user inputs before database insertion
4. **Backup Strategy**: Regular automated backups
5. **User Permissions**: Use separate database user with limited privileges

---

## Performance Tips

1. **Indexes**: Already created on frequently queried columns
2. **Date Ranges**: Use indexed date columns for filtering
3. **Aggregations**: Use database aggregations instead of application-level
4. **Pagination**: Implement LIMIT/OFFSET for large result sets
5. **Connection Pooling**: Configure SQLAlchemy connection pool

---

**Last Updated:** March 2026
**Database Version:** PostgreSQL 12+
**Application:** Money Mate v2.0
