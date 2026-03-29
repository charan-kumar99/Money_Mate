# Money Mate - Deployment Guide

## Prerequisites
- GitHub account
- Neon account (free) - https://neon.tech
- Render account (free) - https://render.com

---

## Part 1: Setup Neon PostgreSQL Database (5 minutes)

### Step 1: Create Neon Account
1. Go to https://neon.tech
2. Click "Sign Up" (use GitHub to sign up - it's faster)
3. Verify your email

### Step 2: Create a New Project
1. Click "Create Project"
2. Project name: `money-mate`
3. Region: Choose closest to you
4. PostgreSQL version: 15 (default)
5. Click "Create Project"

### Step 3: Get Database Connection String
1. After project is created, you'll see the connection details
2. Copy the **Connection String** (it looks like this):
   ```
   postgresql://username:password@ep-xxx-xxx.region.aws.neon.tech/neondb?sslmode=require
   ```
3. **SAVE THIS** - you'll need it later!

### Step 4: Initialize Database Tables
1. Go to Neon dashboard → SQL Editor
2. Copy and paste this SQL:

```sql
-- Create users table
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL
);

-- Create expenses table
CREATE TABLE IF NOT EXISTS expense (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    category VARCHAR(100) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    note TEXT,
    payment_method VARCHAR(50) DEFAULT 'cash'
);

-- Create income table
CREATE TABLE IF NOT EXISTS income (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    source VARCHAR(100) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    note TEXT
);

-- Create budget table
CREATE TABLE IF NOT EXISTS budget (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL
);

-- Create savings_goal table
CREATE TABLE IF NOT EXISTS savings_goal (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    target_amount NUMERIC(10, 2) NOT NULL,
    current_amount NUMERIC(10, 2) DEFAULT 0,
    deadline DATE
);

-- Create recurring_expense table
CREATE TABLE IF NOT EXISTS recurring_expense (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    frequency VARCHAR(50) NOT NULL,
    next_due DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);
```

3. Click "Run" to execute
4. You should see "Success" messages

---

## Part 2: Push to GitHub (3 minutes)

### Step 1: Initialize Git (if not already done)
```bash
git init
git add .
git commit -m "Initial commit - Money Mate app"
```

### Step 2: Create GitHub Repository
1. Go to https://github.com
2. Click "+" → "New repository"
3. Repository name: `money-mate`
4. Make it **Public** or **Private** (your choice)
5. **DO NOT** initialize with README (we already have files)
6. Click "Create repository"

### Step 3: Push to GitHub
```bash
git remote add origin https://github.com/YOUR_USERNAME/money-mate.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

---

## Part 3: Deploy to Render (5 minutes)

### Step 1: Create Render Account
1. Go to https://render.com
2. Click "Get Started"
3. Sign up with GitHub (recommended)

### Step 2: Create New Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository: `money-mate`
3. Click "Connect"

### Step 3: Configure Web Service
Fill in these details:

- **Name**: `money-mate` (or any name you want)
- **Region**: Choose closest to you
- **Branch**: `main`
- **Root Directory**: (leave empty)
- **Runtime**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`
- **Instance Type**: `Free`

### Step 4: Add Environment Variables
Click "Advanced" → "Add Environment Variable"

Add these variables one by one:

1. **DATABASE_URL**
   - Value: (paste your Neon connection string from Part 1, Step 3)

2. **SECRET_KEY**
   - Value: `a3f9c2d5e6b7f8a9c0d1e2f3b4a5c6d7e8f9b0c1d2e3f4a5b6c7d8e9f0a1b2c3`

3. **GEMINI_API_KEY**
   - Value: `AIzaSyCEYd5sbnadVNlt0YCn8CofWKmNfTWREzs`

4. **MAIL_USERNAME**
   - Value: `charanchanu99@gmail.com`

5. **MAIL_PASSWORD**
   - Value: `lgdeecpvlfssactq`

### Step 5: Deploy!
1. Click "Create Web Service"
2. Wait 3-5 minutes for deployment
3. You'll see logs - wait for "Build successful" and "Deploy live"
4. Your app will be live at: `https://money-mate-xxxx.onrender.com`

---

## Part 4: Test Your Deployed App

1. Visit your Render URL: `https://money-mate-xxxx.onrender.com`
2. Click "Sign Up" to create an account
3. Test all features:
   - Add expenses
   - Create budgets
   - Set savings goals
   - Test forgot password (OTP will be sent to email!)

---

## Troubleshooting

### Build Failed?
- Check that `requirements.txt` is in the root directory
- Check that all dependencies are listed

### Database Connection Error?
- Verify DATABASE_URL is correct
- Make sure you ran the SQL commands in Neon
- Check that connection string includes `?sslmode=require`

### App Not Loading?
- Check Render logs for errors
- Verify all environment variables are set
- Make sure `Procfile` exists

### Email Not Sending?
- Verify MAIL_USERNAME and MAIL_PASSWORD are correct
- Check Gmail app password is valid

---

## Alternative: Deploy to Railway (Optional)

If you prefer Railway over Render:

1. Go to https://railway.app
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your `money-mate` repository
5. Add the same environment variables
6. Railway will auto-detect Python and deploy

---

## Updating Your Deployed App

When you make changes:

```bash
git add .
git commit -m "Your update message"
git push origin main
```

Render will automatically redeploy!

---

## Free Tier Limits

### Neon (Database)
- 0.5 GB storage
- 1 project
- Perfect for this app!

### Render (Hosting)
- 750 hours/month (enough for 1 app running 24/7)
- App sleeps after 15 min of inactivity
- Wakes up automatically when accessed (takes 30 seconds)

---

## Need Help?

If you encounter issues:
1. Check Render logs
2. Check Neon database connection
3. Verify all environment variables are set correctly

Your app is now live and accessible from anywhere! 🎉
