# Email Configuration for Forgot Password Feature

## Development Mode (Default)

By default, the application runs in **Development Mode** where OTPs are displayed in the console/terminal instead of being sent via email. This is perfect for testing without setting up email credentials.

### How it works:
1. When you request a password reset, the OTP will be printed in the terminal/console
2. Look for a message like this:
```
============================================================
🔐 DEVELOPMENT MODE - OTP FOR PASSWORD RESET
============================================================
Username: your_username
Email: user@example.com
OTP Code: 123456
Valid for: 10 minutes
============================================================
```
3. Copy the OTP and use it to verify

## Production Mode (Gmail Setup)

To enable actual email sending in production, follow these steps:

### Step 1: Enable 2-Factor Authentication
1. Go to your Google Account settings
2. Navigate to Security
3. Enable 2-Step Verification

### Step 2: Generate App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer" (or Other)
3. Click "Generate"
4. Copy the 16-character password

### Step 3: Set Environment Variables

#### On Windows (PowerShell):
```powershell
$env:MAIL_USERNAME="your-email@gmail.com"
$env:MAIL_PASSWORD="your-16-char-app-password"
```

#### On Windows (Command Prompt):
```cmd
set MAIL_USERNAME=your-email@gmail.com
set MAIL_PASSWORD=your-16-char-app-password
```

#### On Linux/Mac:
```bash
export MAIL_USERNAME="your-email@gmail.com"
export MAIL_PASSWORD="your-16-char-app-password"
```

### Step 4: Restart the Application
After setting the environment variables, restart the Flask application:
```bash
python app.py
```

## Testing the Feature

1. Go to http://127.0.0.1:5000/login
2. Click "Forgot Password?"
3. Enter your username
4. **Development Mode**: Check the terminal/console for the OTP
5. **Production Mode**: Check your email for the OTP
6. Enter the OTP to verify
7. Set your new password

## Troubleshooting

### Development Mode
- OTP not showing in console?
  - Make sure you're looking at the terminal where `python app.py` is running
  - The OTP is printed with a clear border for easy identification

### Production Mode (Email)
- Email not sending?
  - Verify environment variables are set correctly
  - Check that 2FA is enabled on your Google account
  - Ensure you're using an App Password, not your regular password
  - Check spam/junk folder for the OTP email
  - If email fails, the system automatically falls back to console mode

### OTP expired?
- OTPs are valid for 10 minutes
- Request a new OTP if expired

### No email associated with account?
- Users must have an email address in their account
- Update user email in the database if needed

## Alternative Email Providers

You can also use other SMTP providers by updating the configuration in `app.py`:

### For Outlook/Hotmail:
```python
app.config['MAIL_SERVER'] = 'smtp-mail.outlook.com'
app.config['MAIL_PORT'] = 587
```

### For Yahoo:
```python
app.config['MAIL_SERVER'] = 'smtp.mail.yahoo.com'
app.config['MAIL_PORT'] = 587
```

## Security Notes

- Never commit email credentials to version control
- Always use environment variables for sensitive data
- App passwords are more secure than regular passwords
- OTPs expire after 10 minutes for security
- Development mode is safe for testing but should not be used in production
