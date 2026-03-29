-- schema.sql
-- Database creation and table definitions for Money Mate

-- You should create the database manually using your postgres client:
-- CREATE DATABASE money_mate;
-- \c money_mate

CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE expense (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    category VARCHAR(50) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    note VARCHAR(200),
    payment_method VARCHAR(20) DEFAULT 'cash',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_expense_date ON expense(date);
CREATE INDEX idx_expense_category ON expense(category);
CREATE INDEX idx_expense_payment_method ON expense(payment_method);

CREATE TABLE budget (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uix_category_month_year UNIQUE (category, month, year)
);

CREATE INDEX idx_budget_month_year ON budget(month, year);

CREATE TABLE savings_goal (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    target_amount NUMERIC(10, 2) NOT NULL,
    current_amount NUMERIC(10, 2) DEFAULT 0,
    deadline DATE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE income (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    source VARCHAR(50) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    note VARCHAR(200),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_income_date ON income(date);

CREATE TABLE recurring_expense (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    frequency VARCHAR(20) NOT NULL, -- daily, weekly, monthly, yearly
    next_due DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
