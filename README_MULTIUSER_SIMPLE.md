# Multi-User Support for Meal Manager

The Meal Manager supports two distinct modes:

## 🔄 Two Operating Modes

### 📁 SQLite Mode (Local, Single User)
- **Perfect for**: Personal use on your own computer
- **Authentication**: None required
- **Users**: Single user
- **Database**: Local `pantry.db` file
- **Setup**: Zero configuration needed

### 🐘 PostgreSQL Mode (Multi-User)
- **Perfect for**: Hosting online for multiple users
- **Authentication**: User accounts with login/registration
- **Users**: Multiple users with secure data isolation
- **Database**: Shared PostgreSQL database with user_id scoping
- **Setup**: Requires PostgreSQL server

---

## 🚀 Quick Start

### SQLite Mode (Default)
```bash
# No setup required - just run!
python run_web_simple.py
```
✅ No authentication needed  
✅ Data stored locally  
✅ Perfect for personal use  

### PostgreSQL Mode
```bash
# 1. Set up PostgreSQL database
createdb meal_manager

# 2. Set environment variables
export PANTRY_BACKEND=postgresql
export PANTRY_DATABASE_URL=postgresql://username:password@localhost:5432/meal_manager

# 3. Run the application
python run_web_simple.py
```
✅ User registration/login  
✅ Secure data isolation  
✅ Multiple users supported  

---

## 🔒 How Multi-User Security Works

In PostgreSQL mode, all users share one database, but their data is completely isolated:

### Database Schema
```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- All data tables include user_id for isolation
CREATE TABLE recipes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    instructions TEXT NOT NULL,
    -- ... other columns
    UNIQUE(user_id, name)  -- Each user can have their own "Pasta Recipe"
);
```

### Security Features
- ✅ **Password Hashing**: Secure password storage using Werkzeug
- ✅ **Session Management**: Flask sessions for login state
- ✅ **Data Isolation**: Every query includes `WHERE user_id = ?`
- ✅ **SQL Injection Protection**: Parameterized queries throughout
- ✅ **XSS Protection**: Template output escaping
- ✅ **Foreign Key Constraints**: Database-level data integrity

### User Data Isolation
Each user sees only their own:
- Recipes
- Pantry items
- Preferences
- Meal plans
- Transaction history

**Example**: If Alice creates a recipe called "Pasta", and Bob creates a recipe called "Pasta", they are completely separate recipes that only each user can see.

---

## 📊 File Structure

### Core Files
- **`app_final.py`** - Main Flask application with authentication
- **`web_auth_simple.py`** - User management and authentication
- **`pantry_manager_shared.py`** - User-scoped database operations
- **`db_setup_shared.py`** - Database schema with user isolation
- **`run_web_simple.py`** - Application launcher

### Templates
- **`templates/auth/login.html`** - User login page
- **`templates/auth/register.html`** - User registration page
- **`templates/auth/profile_simple.html`** - User profile management

---

## 🛠️ Environment Variables

| Variable | SQLite Mode | PostgreSQL Mode | Description |
|----------|-------------|-----------------|-------------|
| `PANTRY_BACKEND` | `sqlite` (default) | `postgresql` | Database backend |
| `PANTRY_DATABASE_URL` | Not used | **Required** | PostgreSQL connection string |
| `FLASK_SECRET_KEY` | Auto-generated | **Recommended** | Session security key |
| `FLASK_ENV` | `development` | `development`/`production` | Flask environment |

---

## 🔧 Production Deployment

For production PostgreSQL deployment:

### 1. Secure Configuration
```bash
export FLASK_ENV=production
export FLASK_SECRET_KEY=$(openssl rand -base64 32)
export PANTRY_DATABASE_URL=postgresql://user:secure_password@host:5432/meal_manager
```

### 2. Use Production WSGI Server
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app_final:app
```

### 3. Security Checklist
- ✅ Use HTTPS (nginx/Apache with SSL)
- ✅ Set secure `FLASK_SECRET_KEY`
- ✅ Use strong database passwords
- ✅ Enable PostgreSQL SSL
- ✅ Set up regular database backups
- ✅ Monitor application logs

---

## 🚨 Important Notes

### Data Isolation Guarantee
In PostgreSQL mode, it is **impossible** for users to access each other's data because:
1. Every database query includes `WHERE user_id = ?` 
2. User ID comes from authenticated session
3. Database foreign key constraints enforce relationships
4. No queries exist that cross user boundaries

### Switching Modes
- **SQLite → PostgreSQL**: Export data, set up PostgreSQL, import to user account
- **PostgreSQL → SQLite**: Export user's data, import to local SQLite file

### Performance
- **SQLite**: Fast for single user, suitable for personal use
- **PostgreSQL**: Scales to thousands of users, suitable for hosting

---

## 🎯 Recommendations

### Choose SQLite Mode If:
- ✅ Personal use only
- ✅ Running locally on your computer
- ✅ Want zero configuration
- ✅ Don't need user accounts

### Choose PostgreSQL Mode If:
- ✅ Multiple users need access
- ✅ Hosting online
- ✅ Want user registration/login
- ✅ Need data backup/recovery
- ✅ Planning to scale

---

## 📞 Support

The multi-user system is designed to be simple and secure. If you encounter issues:

1. **Check environment variables** are set correctly
2. **Verify PostgreSQL connection** with `psql` command
3. **Review application logs** for error messages
4. **Test with a fresh database** to isolate issues

The shared database approach with user_id scoping is the industry standard for multi-user applications and provides excellent security and performance.