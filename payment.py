import streamlit as st
import stripe
import os
from datetime import datetime, timedelta
from database import get_db_connection, save_payment, update_user_credits, validate_discount_code, use_discount_code

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_default")

def process_payment(user_email, payment_type, amount, details):
    """Process payment with Stripe"""
    try:
        # Create Stripe payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency='usd',
            metadata={
                'user_email': user_email,
                'type': payment_type,
                'details': str(details)
            }
        )
        
        # In a real implementation, you would handle the payment confirmation
        # For now, we'll simulate successful payment
        payment_successful = True
        
        if payment_successful:
            if payment_type == "credits":
                # Add credits to user account
                update_user_credits(user_email, details)
                save_payment(user_email, amount, payment_type, intent.id, details)
                st.success(f"✅ Successfully purchased {details} credits!")
            
            elif payment_type == "subscription":
                # Create subscription
                create_subscription(user_email, details, intent.id)
                st.success(f"✅ Successfully subscribed to {details}!")
        
        return True
        
    except stripe.error.StripeError as e:
        st.error(f"❌ Payment failed: {str(e)}")
        return False

def create_subscription(user_email, plan, stripe_payment_id):
    """Create subscription record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate end date based on plan
    if "Annual" in plan:
        end_date = datetime.now() + timedelta(days=365)
    else:
        end_date = datetime.now() + timedelta(days=30)
    
    cursor.execute("""
        INSERT INTO subscriptions (user_email, plan, end_date, stripe_subscription_id)
        VALUES (%s, %s, %s, %s)
    """, (user_email, plan, end_date, stripe_payment_id))
    
    conn.commit()
    cursor.close()
    conn.close()

def check_subscription(user_email):
    """Check if user has active subscription"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT plan, end_date FROM subscriptions 
        WHERE user_email = %s 
        AND status = 'active' 
        AND end_date > CURRENT_TIMESTAMP
        ORDER BY end_date DESC
        LIMIT 1
    """, (user_email,))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if result:
        return {
            'plan': result[0],
            'next_billing': result[1].strftime('%Y-%m-%d')
        }
    return None

def apply_discount_code(user_email, code):
    """Apply discount code"""
    discount = validate_discount_code(code)
    
    if discount:
        # Use the discount code
        use_discount_code(code)
        
        # Apply discount (this would be used in the next payment)
        st.session_state.discount_applied = {
            'code': code,
            'discount_percent': discount['discount_percent']
        }
        
        return True
    
    return False

def get_stripe_public_key():
    """Get Stripe public key for frontend"""
    return os.getenv("STRIPE_PUBLIC_KEY", "pk_test_default")

def create_checkout_session(user_email, amount, payment_type, success_url, cancel_url):
    """Create Stripe checkout session"""
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'CVCraft {payment_type}',
                    },
                    'unit_amount': int(amount * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_email': user_email,
                'type': payment_type
            }
        )
        return session.url
    except Exception as e:
        st.error(f"❌ Error creating checkout session: {str(e)}")
        return None
