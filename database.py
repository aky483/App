import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, timedelta
import hashlib
import secrets
from urllib.parse import urlparse

def get_db_connection():
    url = urlparse(os.environ.get("DATABASE_URL"))
    return psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            auth_provider VARCHAR(50) NOT NULL,
            password_hash VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            credits INTEGER DEFAULT 5,
            total_cvs_generated INTEGER DEFAULT 0,
            avg_ats_score FLOAT DEFAULT 0.0
        )
    """)
    
    # Subscriptions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) REFERENCES users(email),
            plan VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'active',
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date TIMESTAMP,
            stripe_subscription_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # CV generations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cv_generations (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) REFERENCES users(email),
            job_description TEXT,
            original_resume TEXT,
            generated_cv TEXT,
            template_used VARCHAR(50),
            ats_score INTEGER,
            target_match INTEGER,
            processing_time FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # User sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) REFERENCES users(email),
            session_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Payments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) REFERENCES users(email),
            amount DECIMAL(10, 2) NOT NULL,
            type VARCHAR(20) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            stripe_payment_id VARCHAR(255),
            credits_purchased INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Discount codes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS discount_codes (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            discount_percent INTEGER NOT NULL,
            max_uses INTEGER DEFAULT 1,
            current_uses INTEGER DEFAULT 0,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

def get_user_data(email):
    """Get user data by email"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT * FROM users WHERE email = %s
    """, (email,))
    
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return dict(user) if user else None

def create_user(email, name, auth_provider, password_hash=None):
    """Create new user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO users (email, name, auth_provider, password_hash, last_login)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (email) DO UPDATE SET
        last_login = EXCLUDED.last_login
        RETURNING *
    """, (email, name, auth_provider, password_hash, datetime.now()))
    
    user = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    
    return user

def update_user_credits(email, credits):
    """Update user credits"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users SET credits = credits + %s WHERE email = %s
    """, (credits, email))
    
    conn.commit()
    cursor.close()
    conn.close()

def get_user_credits(email):
    """Get user's current credits"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT credits FROM users WHERE email = %s
    """, (email,))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return result[0] if result else 0

def save_cv_generation(user_email, job_description, original_resume, generated_cv, template_used, ats_score, target_match, processing_time):
    """Save CV generation record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO cv_generations (user_email, job_description, original_resume, generated_cv, template_used, ats_score, target_match, processing_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_email, job_description, original_resume, generated_cv, template_used, ats_score, target_match, processing_time))
    
    # Update user stats
    cursor.execute("""
        UPDATE users SET 
        total_cvs_generated = total_cvs_generated + 1,
        avg_ats_score = (
            SELECT AVG(ats_score) FROM cv_generations WHERE user_email = %s
        )
        WHERE email = %s
    """, (user_email, user_email))
    
    conn.commit()
    cursor.close()
    conn.close()

def save_user_session(user_email, session_data):
    """Save user session data for auto-save"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO user_sessions (user_email, session_data)
        VALUES (%s, %s)
        ON CONFLICT (user_email) DO UPDATE SET
        session_data = EXCLUDED.session_data,
        updated_at = CURRENT_TIMESTAMP
    """, (user_email, json.dumps(session_data)))
    
    conn.commit()
    cursor.close()
    conn.close()

def get_user_session(user_email):
    """Get user session data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT session_data FROM user_sessions WHERE user_email = %s
    """, (user_email,))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return json.loads(result[0]) if result else {}

def save_payment(user_email, amount, payment_type, stripe_payment_id, credits_purchased=0):
    """Save payment record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO payments (user_email, amount, type, stripe_payment_id, credits_purchased)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_email, amount, payment_type, stripe_payment_id, credits_purchased))
    
    conn.commit()
    cursor.close()
    conn.close()

def create_discount_code(code, discount_percent, max_uses=1, expires_at=None):
    """Create discount code"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO discount_codes (code, discount_percent, max_uses, expires_at)
        VALUES (%s, %s, %s, %s)
    """, (code, discount_percent, max_uses, expires_at))
    
    conn.commit()
    cursor.close()
    conn.close()

def validate_discount_code(code):
    """Validate discount code"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT * FROM discount_codes 
        WHERE code = %s 
        AND current_uses < max_uses 
        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
    """, (code,))
    
    discount = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return dict(discount) if discount else None

def use_discount_code(code):
    """Use discount code"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE discount_codes 
        SET current_uses = current_uses + 1
        WHERE code = %s
    """, (code,))
    
    conn.commit()
    cursor.close()
    conn.close()
