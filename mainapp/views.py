import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import ccxt
import time
import uuid
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.hashers import make_password
from urllib.parse import urlencode
from django.contrib.auth.models import User
import logging
import random
import secrets
import logging
from pybit.unified_trading import HTTP
import pyotp
import hmac
import hashlib
import os
from dotenv import load_dotenv
import string
import json
from django.views.generic.edit import FormMixin
from django.http import JsonResponse
from django.core.mail import send_mail
import stripe
import paypalrestsdk
from decimal import Decimal
from django.utils import timezone
from decimal import Decimal
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist, ValidationError
from .models import Wallet
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from .forms import WithdrawForm, WalletForm, LoginForm, SignupForm, VerifyPhoneForm, PhoneNumberForm, CustomPasswordChangeForm, UpdateProfileForm, PasswordResetForm, ContactForm, CustomUserCreationForm, DepositForm, TradeForm, CryptocurrencyForm, ProfileForm, PortfolioForm
from .models import CryptoNetwork, Service, Deposit, Trade, Withdraw, Cryptocurrency, Portfolio, Profile, Referral, BlockchainTransaction, Transaction, InvestmentPlan, Staking, MarketData, Wallet, Transaction, Deposit, FiatDeposit
from .blockchain_service import send_crypto, get_wallet_balance, get_bitcoin_balance, get_ethereum_balance
from .mt5_helper import MetaTraderConnector
import MetaTrader5 as mt5
from .helpers import generate_referral_code
from django.db.utils import IntegrityError
from .services import fetch_market_data  # Ensure to import the service function
from datetime import datetime, timedelta
from .utils import fetch_deposit_address, process_crypto_payment, fetch_crypto_price, get_realtime_btc_to_usd_rate, process_deposit, process_withdrawal, process_deposit  # Including the new fiat deposit logic
import stripe
from urllib.parse import urlencode
from .payments import process_crypto_payment
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.utils.encoding import force_bytes, force_str
from coinbase.wallet.client import Client
from .models import Wallet, TwilioMessage
from django.urls import reverse, NoReverseMatch
from web3 import Web3
from django.conf import settings
import logging
from django.utils.timezone import now  # For timezone-aware datetime
import qrcode
from io import BytesIO
import base64


# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


load_dotenv()

# Print the value of the KUCOIN_API_KEY
print(os.getenv('KUCOIN_API_KEY'))

# Load environment variables
API_KEY = os.getenv('KUCOIN_API_KEY')  # KuCoin API Key
API_SECRET = os.getenv('KUCOIN_API_SECRET')  # KuCoin API Secret
API_PASSPHRASE = os.getenv('KUCOIN_API_PASSPHRASE')  # KuCoin API Passphrase
OWNER_WALLET_ADDRESSES = {
    "BTC": os.getenv("BTC_OWNER_WALLET"),
    "ETH:ERC20": os.getenv("ETH_ERC20_OWNER_WALLET"),
    "ETH:BEP20": os.getenv("ETH_BEP20_OWNER_WALLET"),
    "USDT:TRC20": os.getenv("USDT_TRC20_OWNER_WALLET"),
    "USDT:ERC20": os.getenv("USDT_ERC20_OWNER_WALLET"),
}


# Initialize Coinbase API client
coinbase_client = Client(settings.COINBASE_API_KEY, settings.COINBASE_API_SECRET)

# Initialize Stripe with the secret key
# stripe.api_key = settings.STRIPE_TEST_API_KEY

# Initialize Coinbase API
coinbase_client = Client(settings.COINBASE_API_KEY, settings.COINBASE_API_SECRET)

def about(request):
    return render(request, 'mainapp/about.html')


def services_view(request):
    try:
        # Fetch all active services from the database
        services = Service.objects.filter(is_active=True).order_by('title')  # Ordered by title for consistency
    except Service.DoesNotExist:
        # Handle the case where no services exist (unlikely but safe)
        services = []

    # Render the template with services
    return render(request, 'services.html', {'services': services})


def contact_view(request):
    """
    Handles the Contact Us page with a form submission feature.
    """
    logger.info("Contact view accessed.")

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            logger.info("Contact form submitted successfully.")
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')
    else:
        form = ContactForm()

    return render(request, 'contact.html', {'form': form})

def index(request): 
    try:
        if request.user.is_authenticated:
            # For authenticated users
            nav_links = [
                {"name": "Home", "url": reverse('index')},
                {"name": "About Us", "url": reverse('about')},
                {"name": "Services", "url": reverse('services')},
                {"name": "Contact Us", "url": reverse('contact')},
                {"name": "Dashboard", "url": reverse('dashboard')},
                {"name": "Wallet", "url": reverse('wallet')},
                {"name": "Logout", "url": reverse('logout_view')},  # Ensure name matches the URL pattern
            ]
        else:
            # For non-authenticated users
            nav_links = [
                {"name": "Home", "url": reverse('index')},
                {"name": "About Us", "url": reverse('about')},
                {"name": "Services", "url": reverse('services')},
                {"name": "Contact Us", "url": reverse('contact')},
                {"name": "Login", "url": reverse('login')},  # Update to use 'login' URL pattern
                {"name": "Register", "url": reverse('signup')},  # Update to use 'signup' URL pattern
            ]

        context = {"nav_links": nav_links}
        return render(request, 'index.html', context)
    except Exception as e:
        print(f"Error in index view: {e}")
        return render(request, 'error.html', {"message": "Something went wrong"})

# Updated subscription plan logic in views.py
@login_required
def select_plan(request):
    if request.method == 'POST':
        plan_name = request.POST.get('plan_name')
        min_amount = request.POST.get('min_amount')
        max_amount = request.POST.get('max_amount')
        interest_rate = request.POST.get('interest_rate')

        # Save the selected plan information in the session or database
        request.session['selected_plan'] = {
            'plan_name': plan_name,
            'min_amount': min_amount,
            'max_amount': max_amount,
            'interest_rate': float(interest_rate.replace('%', '')) / 100  # Convert to decimal
        }

        return JsonResponse({
            'message': f"Selected Plan: {plan_name}, Interest Rate: {interest_rate}%"
        })
    return redirect('index')


@login_required
def dashboard_view(request):
    """
    Dashboard view to display user portfolio, cryptocurrency data, wallet details, and MetaTrader 5 connection status.
    """

    # Initialize MetaTrader 5 connection
    if not mt5.initialize():
        mt5_status = "MetaTrader 5 connection failed"
    else:
        mt5_status = "Connected to MetaTrader 5"

    # Fetch top 10 cryptocurrencies by market cap
    crypto_api_url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 10,
        "page": 1,
        "sparkline": False,
    }
    try:
        response = requests.get(crypto_api_url, params=params)
        response.raise_for_status()
        top_10_crypto_data_global = response.json()
    except requests.RequestException as e:
        top_10_crypto_data_global = []
        print(f"Error fetching cryptocurrency data: {e}")

    # Fetch user portfolio
    user_portfolio = Portfolio.objects.filter(user=request.user).first()

    # Fetch user cryptocurrencies
    user_cryptocurrencies = Cryptocurrency.objects.filter(user=request.user)

    # Fetch user wallet details
    try:
        user_wallet = Wallet.objects.get(user=request.user)
    except Wallet.DoesNotExist:
        user_wallet = None

    # Fetch deposit and withdrawal transactions
    deposit_transactions = Transaction.objects.filter(user=request.user, transaction_type="deposit").order_by("-timestamp")
    withdrawal_transactions = Transaction.objects.filter(user=request.user, transaction_type="withdrawal").order_by("-timestamp")

    context = {
        "top_10_crypto_data_global": top_10_crypto_data_global,
        "mt5_status": mt5_status,
        "user_portfolio": user_portfolio,
        "user_cryptocurrencies": user_cryptocurrencies,
        "user_wallet": user_wallet,
        "deposit_transactions": deposit_transactions,
        "withdrawal_transactions": withdrawal_transactions,
    }

    return render(request, "dashboard.html", context)



def crypto_chart(request):
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        params = {
            "vs_currency": "usd",
            "days": "1",
            "interval": "hourly"
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            return JsonResponse({"status": "error", "message": f"API error: {response.status_code}"}, status=500)

        data = response.json()
        prices = data.get("prices", [])
        if not prices:
            return JsonResponse({"status": "error", "message": "No price data found in the API response"}, status=404)

        chart_data = [
            {"timestamp": point[0] // 1000, "price": point[1]} for point in prices
        ]

        return JsonResponse({"status": "success", "data": chart_data})

    except requests.RequestException as e:
        return JsonResponse({"status": "error", "message": f"Request error: {str(e)}"}, status=500)
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Unexpected error: {str(e)}"}, status=500)
    
    


@login_required(login_url='login')
def place_trade(request):
    if request.method == 'POST':
        try:
            trade_amount = Decimal(request.POST.get('trade_amount', 0))
            if trade_amount <= 0:
                return JsonResponse({'error': 'Invalid trade amount.'}, status=400)

            wallet = Wallet.objects.get(user=request.user)
            if wallet.fiat_balance < trade_amount:
                return JsonResponse({'redirect_url': '/wallet/'}, status=400)

            if not mt5.initialize():
                return JsonResponse({'error': 'Failed to initialize MetaTrader 5 connection'}, status=500)

            symbol = 'EURUSD'
            lot_size = trade_amount / 1000
            price = mt5.symbol_info_tick(symbol).ask

            request_trade = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "slippage": 3,
                "magic": 234000,
                "comment": "Trade via Django",
                "type_filling": mt5.ORDER_FILLING_IOC,
                "type_time": mt5.ORDER_TIME_GTC,
            }

            result = mt5.order_send(request_trade)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return JsonResponse({'error': f'Trade failed: {result.comment}'}, status=500)

            return JsonResponse({'success': True, 'order': result.order, 'price': price, 'volume': lot_size})
        except Wallet.DoesNotExist:
            return JsonResponse({'redirect_url': '/wallet/'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=405)



@login_required
def profile_view(request):
    profile = Profile.objects.get(user=request.user)
    form = ProfileForm(instance=profile)

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile')  # Redirect to profile page after save

    return render(request, 'profile.html', {'form': form, 'profile': profile})

@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UpdateProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
        else:
            messages.error(request, "Please correct the error below.")
    else:
        form = UpdateProfileForm(instance=request.user)
    return render(request, 'update_profile.html', {'form': form})


# Twilio client setup (ensure to add your Twilio SID and Auth Token in your settings)
twilio_client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)
TWILIO_PHONE_NUMBER = settings.TWILIO_PHONE_NUMBER

def send_sms(phone_number, message):
    try:
        message = twilio_client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        return message.sid
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return None


def setup(request):
    user = request.user
    profile = user.profile

    if request.method == "POST":
        if 'update_phone' in request.POST:
            phone_number_form = PhoneNumberForm(request.POST)
            if phone_number_form.is_valid():
                phone_number = phone_number_form.cleaned_data['phone_number']
                profile.phone_number = phone_number
                profile.save()

                # Create and send a verification code via Twilio
                twilio_message = TwilioMessage.objects.create(
                    to_phone_number=phone_number,
                    from_phone_number='your_twilio_phone_number',  # Your Twilio number
                    message_body="Your 2FA verification code.",
                    twilio_message_sid='temp_sid',  # Temporary SID
                )

                verification_sid = twilio_message.send_verification_code()

                if verification_sid:
                    messages.success(request, "Phone number added successfully. A verification code has been sent to your phone.")
                else:
                    messages.error(request, "Failed to send verification code.")

            else:
                messages.error(request, "Invalid phone number.")

        return redirect('setup')

    # If not POST, prepare forms for display
    phone_number_form = PhoneNumberForm()

    return render(request, 'setup.html', {
        'phone_number_form': phone_number_form,
        'profile': profile,
    })



def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # After successful registration, redirect to the login page
    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form})



def send_verification_sms(request):
    # Assume the phone number is available in the user's profile
    to_phone_number = request.user.profile.phone_number
    # Create TwilioMessage instance
    twilio_message = TwilioMessage.objects.create(
        to_phone_number=to_phone_number,
        from_phone_number='your_twilio_phone_number',  # Replace with your Twilio number
        message_body="Your 2FA verification code.",
        twilio_message_sid='temp_sid',  # Temporary SID, will be updated after sending the message
    )

    # Send verification code via Twilio
    verification_sid = twilio_message.send_verification_code()
    if verification_sid:
        # Optionally, send a confirmation response
        return JsonResponse({'message': 'Verification code sent!', 'sid': verification_sid})
    else:
        return JsonResponse({'message': 'Failed to send verification code.'})
    
    

def verify_phone(request, user_id):
    user = User.objects.get(id=user_id)

    if request.method == 'POST':
        entered_code = request.POST.get('verification_code')
        if entered_code == user.phone_verification_code:
            user.phone_verified = True
            user.save()
            messages.success(request, "Phone number verified successfully!")
            return redirect('login')
        else:
            messages.error(request, "Invalid verification code.")
    
    return render(request, 'verify_phone.html', {'user': user})


def terms_conditions_view(request):
    return render(request, 'terms_conditions.html')  # Use an appropriate template

 
def logout_view(request):
    logout(request)
    return redirect('index')
   

# Generate random 6-digit phone verification code
def generate_phone_code():
    return str(random.randint(100000, 999999))

# Example Twilio SMS sending function
def send_sms(code, phone_number):
    client = Client('your_twilio_account_sid', 'your_twilio_auth_token')
    message = client.messages.create(
        body=f"Your verification code is {code}",
        from_='your_twilio_phone_number',
        to=phone_number
    )
    return message.sid


def signup_view(request):
    form = SignupForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            try:
                # Save the user but set them as inactive
                user = form.save(commit=False)
                user.is_active = False  # User must confirm email first
                user.save()

                # Generate email confirmation token
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = token_generator.make_token(user)

                # Build the email confirmation URL
                confirmation_url = request.build_absolute_uri(
                    f"/account/confirm-email/{uid}/{token}/"
                )

                # Send the confirmation email
                subject = "Confirm Your Email"
                message = render_to_string("email/confirmation_email.html", {
                    "user": user,
                    "confirmation_url": confirmation_url,
                })
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

                # Send phone verification code
                user.phone_verification_code = generate_phone_code()
                send_sms(user.phone_verification_code, user.phone_number)  # Implement `send_sms` with your SMS API
                user.save()

                # Success message
                messages.success(
                    request, 
                    "Account created successfully! Please confirm your email and phone to log in."
                )

                # Redirect to login page after successful signup
                return redirect('login')  # Change 'login' to the appropriate URL name if needed.

            except Exception as e:
                # Error handling
                messages.error(request, f"Signup failed: {str(e)}")
                return redirect('signup')  # If an error occurs, stay on signup page.

        else:
            # If form is invalid, display form errors
            messages.error(request, "There were errors in your form submission. Please correct them.")
            return render(request, 'signup.html', {'form': form})

    # If GET request, simply render the signup page
    return render(request, 'signup.html', {'form': form})


def confirm_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Email confirmed! You can now log in.")
        return redirect('login')
    else:
        messages.error(request, "Invalid confirmation link.")
        return redirect('login')


def login_view(request):
    # If the user is already authenticated, redirect to the dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    # Handle POST request for login
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('dashboard')  # Redirect to dashboard after successful login
            else:
                messages.error(request, 'Invalid username or password.')

    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})



def logout_view(request):
    logout(request)
    messages.success(request, 'You have successfully logged out!')
    return redirect('index')

def password_reset_view(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save(request=request)
            messages.success(request, "Password reset email sent.")
            return redirect('login')
        else:
            messages.error(request, "Invalid email address.", extra_tags='danger')
    else:
        form = PasswordResetForm()

    return render(request, 'password_reset.html', {'form': form})

# ============== Portfolio Views ============== #

@login_required(login_url="login")
def portfolio_view(request):
    current_user = request.user

    # Retrieve the user's cryptocurrencies and associated portfolio
    user_cryptocurrencies = Cryptocurrency.objects.filter(user=current_user)

    # Calculate the total value of the portfolio
    total_value = 0
    portfolio_breakdown = []
    for crypto in user_cryptocurrencies:
        # Assuming `crypto` has fields: 'amount' and 'current_price'
        current_value = crypto.amount * crypto.current_price
        total_value += current_value

        portfolio_breakdown.append({
            'name': crypto.name,
            'amount': crypto.amount,
            'current_price': crypto.current_price,
            'current_value': current_value,
            'percent_of_portfolio': (current_value / total_value) * 100 if total_value > 0 else 0
        })

    # Fetch the most recent transactions for the user, order by 'timestamp' instead of 'date'
    recent_transactions = Transaction.objects.filter(user=current_user).order_by('-timestamp')[:5]

    # Portfolio performance: Assuming portfolio has a 'created' date and we track value over time
    portfolio = Portfolio.objects.filter(user=current_user).first()
    if portfolio:
        # Assuming Portfolio model has a 'created' timestamp and a 'total_value' field
        portfolio_history = Portfolio.objects.filter(user=current_user).order_by('created')
    else:
        portfolio_history = []

    # Context to pass to the template
    context = {
        'current_user': current_user,
        'user_cryptocurrencies': user_cryptocurrencies,
        'portfolio_breakdown': portfolio_breakdown,
        'total_value': total_value,
        'portfolio_history': portfolio_history,
        'recent_transactions': recent_transactions
    }
    return render(request, 'portfolio.html', context)


def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Save the form to the database or handle the data
            form.save()

            # Send a success message
            messages.success(request, "Your message has been sent successfully!")
            return redirect('contact')  # Redirect to the contact page or another page
        else:
            # Handle form errors
            messages.error(request, "There was an error sending your message. Please try again.")
    else:
        form = ContactForm()

    return render(request, 'contact.html', {'form': form})


def create_portfolio(request):
    if request.method == 'POST':
        form = PortfolioForm(request.POST)
        if form.is_valid():
            # Save the portfolio instance, the total_value will be calculated automatically in the form's clean() method
            form.save()
            messages.success(request, 'Portfolio created successfully!')
            return redirect('portfolio')  # Redirect to portfolio page or another success page
        else:
            # If form is not valid, show error messages
            messages.error(request, 'There was an error creating your portfolio. Please check the form and try again.')
    else:
        form = PortfolioForm()

    # Render the form page
    return render(request, 'portfolio_form.html', {'form': form})


def delete_from_portfolio_view(request, pk):
    # Fetch the cryptocurrency object based on its primary key and ensure it's the current user's asset
    crypto_currency = get_object_or_404(Cryptocurrency, pk=pk, user=request.user)

    # Delete the cryptocurrency from the user's portfolio
    crypto_currency.delete()

    # Show a success message indicating the cryptocurrency has been removed
    messages.success(request, f'{crypto_currency.name} has been deleted from your portfolio.')

    # Redirect to the portfolio page after deletion
    return redirect('portfolio')


# ============== Trade Views ============== #

def trade_view(request):
    form = TradeForm(request.POST or None)
    if form.is_valid():
        trade = form.save(commit=False)
        trade.user = request.user
        trade.status = 'PENDING'
        trade.save()
        messages.success(request, f"Trade {trade.order_type} {trade.token} initiated.")
        return redirect('trade-status', trade_id=trade.id)
    return render(request, 'trade.html', {'form': form})


def trade_status(request, trade_id):
    # Fetch the trade object or return 404 if not found
    trade = get_object_or_404(Trade, id=trade_id, user=request.user)

    context = {
        'trade': trade,
    }
    return render(request, 'trade_status.html', context)



# ============== Initiate Trade =================== #


@login_required
def initiate_trade(request):
    """
    View to handle trade initiation. Simulates a trade with profit or loss, 
    based on the user's selected subscription plan interest rate.
    """
    if request.method == 'POST':
        try:
            # Get the user's wallet
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            return JsonResponse({'error': 'Wallet does not exist. Please create a wallet first.'}, status=404)

        # Check if a subscription plan is selected
        selected_plan = request.session.get('selected_plan')
        if not selected_plan:
            return JsonResponse({'error': 'Please select a subscription plan first.'}, status=400)

        # Retrieve the plan's interest rate and limits
        interest_rate = Decimal(selected_plan.get('interest_rate', 0))
        min_amount = Decimal(selected_plan.get('min_amount', 0))
        max_amount = Decimal(selected_plan.get('max_amount', 0))

        # Ensure trade amount is valid
        trade_amount = Decimal(request.POST.get('trade_amount', 0))
        if trade_amount < min_amount or trade_amount > max_amount:
            return JsonResponse({'error': f'Trade amount must be between {min_amount} and {max_amount}.'}, status=400)

        if wallet.balance < trade_amount:
            return JsonResponse({'error': 'Insufficient wallet balance.'}, status=400)

        # Calculate the trade profit based on interest rate and duration (5 days)
        trade_profit = trade_amount * (interest_rate / 100) * 5

        # Update wallet balance
        wallet.balance += trade_profit
        wallet.save()

        # Log the transaction
        transaction = Transaction.objects.create(
            user=request.user,
            type='Trade',
            amount=trade_profit,
            timestamp=timezone.now()
        )

        return JsonResponse({
            'message': 'Trade executed successfully.',
            'trade_amount': float(trade_amount),
            'profit': float(trade_profit),
            'updated_balance': float(wallet.balance)
        })

    return JsonResponse({'error': 'Invalid request method.'}, status=405)


# ============== Deposit Views ============== #
# Initialize Stripe and PayPal SDKs
stripe.api_key = 'your_stripe_secret_key'
paypalrestsdk.configure({
    'mode': 'sandbox',  # Change to 'live' for production
    'client_id': 'your_paypal_client_id',
    'client_secret': 'your_paypal_client_secret',
    
})

# Example for fetching crypto price from CoinGecko API
def get_crypto_price(crypto_symbol="btc"):
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={crypto_symbol}&vs_currencies=usd'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()[crypto_symbol]['usd']
    return None

def generate_crypto_address():
    """Generate a random crypto address"""
    # Simulating a crypto address (e.g., Ethereum address format)
    return "0x" + secrets.token_hex(20)  # Generates a 40-character address, similar to Ethereum

# Initialize Web3 for Ethereum
web3 = Web3(Web3.HTTPProvider(settings.WEB3_PROVIDER_URL))


def get_wallet_balance(address):
    """Fetch the balance of a wallet."""
    balance_wei = web3.eth.get_balance(Web3.toChecksumAddress(address))
    return web3.fromWei(balance_wei, 'ether')


@login_required
def get_networks(request):
    """
    Return available networks for a selected cryptocurrency, based on OWNER_WALLET_ADDRESSES.
    """
    coin = request.GET.get("coin", "").upper()  # Normalize coin input to uppercase
    logging.debug(f"Fetching networks for coin: {coin}")

def fetch_networks(request, coin):
    """
    Fetch available networks for a given coin based on OWNER_WALLET_ADDRESSES.
    """
    try:
        # Parse the keys in OWNER_WALLET_ADDRESSES to derive the supported networks
        available_networks = {}
        for key, wallet_address in OWNER_WALLET_ADDRESSES.items():
            if wallet_address:  # Include only if wallet address is set
                if ":" in key:
                    base_coin, network = key.split(":")
                    available_networks.setdefault(base_coin, []).append({"name": network, "code": network})
                else:
                    available_networks.setdefault(key, []).append({"name": key, "code": key})

        # Check if the coin exists and return its networks
        if coin in available_networks:
            logging.debug(f"Networks found for {coin}: {available_networks[coin]}")
            return JsonResponse({"status": "success", "networks": available_networks[coin]})

        # Handle invalid coin input
        logging.error(f"Invalid coin: {coin}")
        return JsonResponse({"status": "error", "message": "Invalid coin provided"}, status=400)

    except Exception as e:
        logging.error(f"Error fetching networks: {str(e)}")
        return JsonResponse({"status": "error", "message": "Internal Server Error"}, status=500)


def get_binance_data(request):
    try:
        response = requests.get('https://api.binance.com/api/v3/exchangeInfo')
        if response.status_code == 200:
            data = response.json()
            coins = []

            # Extract relevant coin and network data
            for symbol_info in data.get('symbols', []):
                if symbol_info['isSpotTradingAllowed']:
                    coin = symbol_info['baseAsset']
                    networks = [{'network': s['network'], 'coin': coin} for s in symbol_info.get('permissions', [])]
                    coins.append({'symbol': coin, 'networks': networks})

            return JsonResponse({'status': 'success', 'coins': coins})
        else:
            return JsonResponse({'status': 'error', 'message': 'Failed to fetch Binance data'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


# Accessing environment variables
deposit_addresses = os.getenv("OWNER_WALLET_ADDRESSES")


def generate_qr_code(address):
    qr = qrcode.make(address)
    img_io = BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io


@login_required
def deposit_view(request):
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data.get('amount')
            crypto_currency = form.cleaned_data.get('crypto_currency')
            network = form.cleaned_data.get('network')
            account_type = form.cleaned_data.get('account_type')

            try:
                # Fetch real-time crypto price
                crypto_price = fetch_crypto_price(crypto_currency)
                if not crypto_price:
                    raise Exception(f"Unable to fetch price for {crypto_currency}.")

                # Fetch deposit address from KuCoin
                deposit_address, memo_tag = fetch_kucoin_deposit_address(crypto_currency, network)
                if not deposit_address:
                    raise Exception(f"Unable to fetch deposit address for {crypto_currency} on {network}.")

                # Generate QR Code for the deposit address
                qr_code_img = generate_qr_code(deposit_address)

                # Calculate deposit value in USD
                deposit_in_usd = amount * crypto_price
                MINIMUM_DEPOSIT_AMOUNT = 100  # Minimum deposit amount in USD
                if deposit_in_usd < MINIMUM_DEPOSIT_AMOUNT:
                    messages.error(
                        request,
                        f"Minimum deposit is ${MINIMUM_DEPOSIT_AMOUNT} (\u2248 {MINIMUM_DEPOSIT_AMOUNT / crypto_price:.6f} {crypto_currency})."
                    )
                    return render(request, 'deposit.html', {'form': form})

                # Calculate transaction fee (0.8%)
                TRANSACTION_FEE_PERCENTAGE = 0.008
                transaction_fee = amount * TRANSACTION_FEE_PERCENTAGE
                available_balance = amount - transaction_fee

                # Determine the owner wallet address for transaction fee
                owner_wallet_key = f"{crypto_currency}:{network}" if network else crypto_currency
                owner_wallet_address = settings.OWNER_WALLET_ADDRESSES.get(owner_wallet_key)
                if not owner_wallet_address:
                    raise Exception(f"Owner wallet address not configured for {crypto_currency} on {network}.")

                # Send transaction fee to owner's wallet
                if not process_crypto_payment(crypto_currency, transaction_fee, owner_wallet_address):
                    raise Exception("Fee transfer failed.")

                # Save deposit details
                Deposit.objects.create(
                    user=request.user,
                    amount=amount,
                    crypto_currency=crypto_currency,
                    network=network,
                    account_type=account_type,
                    transaction_fee=transaction_fee,
                    available_balance=available_balance,
                    deposit_address=deposit_address,
                    memo_tag=memo_tag,
                    created_at=now(),
                )

                messages.success(
                    request,
                    f"Deposit successful! Available Balance: {available_balance:.6f} {crypto_currency} (\u2248 ${available_balance * crypto_price:.2f})."
                )
                # Return both QR code and owner wallet address to the confirmation page
                return render(request, 'deposit.html', {
                    'form': form, 
                    'qr_code_img': qr_code_img,
                    'owner_wallet_address': owner_wallet_address,
                    'deposit_address': deposit_address
                })

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

    else:
        form = DepositForm()

    return render(request, 'deposit.html', {'form': form})


owner_wallet_addresses = settings.OWNER_WALLET_ADDRESSES


COIN_NAME_MAPPING = {
    'BTC': 'bitcoin',
    'ETH': 'ethereum',
    'SOL': 'solana',
    'USDT': 'tether',
    'TRX': 'tron'
}

def get_coin_price_from_coingecko(coin):
    full_name = COIN_NAME_MAPPING.get(coin.upper())
    if not full_name:
        logging.error(f"Coin name mapping not found for: {coin}")
        return None

    url = f'https://api.coingecko.com/api/v3/simple/price?ids={full_name}&vs_currencies=usd'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise error for HTTP issues
        data = response.json()
        
        if full_name in data:
            return data[full_name]['usd']
        else:
            logging.error(f"Coin {full_name} not found in CoinGecko data: {data}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching coin price from CoinGecko: {str(e)}")
        return None



def generate_kucoin_headers(api_key, api_secret, api_passphrase, method, endpoint, body=""):
    """
    Generate KuCoin API headers with proper signature and encryption.
    """
    timestamp = str(int(time.time() * 1000))  # Current timestamp in milliseconds
    prehash = f"{timestamp}{method.upper()}{endpoint}{body}"
    
    # Sign the request
    signature = base64.b64encode(
        hmac.new(api_secret.encode(), prehash.encode(), hashlib.sha256).digest()
    )

    # Encrypt the passphrase
    encrypted_passphrase = base64.b64encode(
        hmac.new(api_secret.encode(), api_passphrase.encode(), hashlib.sha256).digest()
    )

    return {
        "KC-API-KEY": api_key,
        "KC-API-SIGN": signature.decode(),
        "KC-API-TIMESTAMP": timestamp,
        "KC-API-PASSPHRASE": encrypted_passphrase.decode(),
    }


def fetch_deposit_details(request, coin, network):
    """
    Fetch deposit details for the specified coin and network using the KuCoin API.
    """
    base_url = "https://api.kucoin.com"
    endpoint = f"/api/v1/deposit-addresses?currency={coin.upper()}&chain={network}"
    
    # Generate headers for the KuCoin API
    headers = generate_kucoin_headers(
        api_key=settings.KUCOIN_API_KEY,
        api_secret=settings.KUCOIN_API_SECRET,
        api_passphrase=settings.KUCOIN_API_PASSPHRASE,
        method="GET",
        endpoint=endpoint
    )

    try:
        # Make the API request
        response = requests.get(f"{base_url}{endpoint}", headers=headers)

        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "200000":
                # Extract deposit details
                deposit_address = data["data"]["address"]
                memo_tag = data["data"].get("memo", "")  # Memo is optional
                amount_to_deposit = "0.01"  # Placeholder, set dynamically if needed
                transaction_fee = "0.0005"  # Placeholder fee
                equivalent_value = 100  # Placeholder, fetch the live price if required

                return JsonResponse({
                    "status": "success",
                    "deposit_address": deposit_address,
                    "memo_tag": memo_tag,
                    "amount_to_deposit": f"${amount_to_deposit}",  # USD sign added
                    "transaction_fee": transaction_fee,
                    "equivalent_value": f"{equivalent_value} {coin.upper()}",
                })

            return JsonResponse({
                "status": "error",
                "message": f"KuCoin API returned an error: {data.get('msg', 'Unknown error')}"
            }, status=400)

        # Handle API response errors
        return JsonResponse({
            "status": "error",
            "message": f"Failed to fetch deposit details. KuCoin API response: {response.text}"
        }, status=response.status_code)

    except requests.exceptions.RequestException as e:
        # Handle network-related errors
        return JsonResponse({
            "status": "error",
            "message": f"Network error: {str(e)}"
        }, status=500)


def fetch_crypto_price(crypto_currency):
    """
    Fetch the real-time price of the cryptocurrency in USD.
    """
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={crypto_currency.lower()}&vs_currencies=usd"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data[crypto_currency.lower()]['usd']
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None


def fetch_kucoin_deposit_address(crypto_currency, network):
    """
    Fetch the deposit address for the specified cryptocurrency and network from KuCoin.
    """
    url = "https://api.kucoin.com/api/v1/deposit-address"
    params = {
        'currency': crypto_currency,
        'chain': network
    }
    headers = {
        'KC-API-KEY': settings.KUCOIN_API_KEY,
        'KC-API-SECRET': settings.KUCOIN_API_SECRET,
        'KC-API-PASSPHRASE': settings.KUCOIN_API_PASSPHRASE,
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        # Log the response for debugging
        logger.debug(f"API response: {response.text}")
        
        if response.status_code == 200 and data['code'] == '200000':
            address_info = data['data']
            return address_info.get('address'), address_info.get('memo')
        else:
            logger.error(f"Error fetching deposit address for {crypto_currency} on {network}: {data.get('msg', 'Unknown error')}")
            return None, None
    except Exception as e:
        logger.error(f"Error fetching deposit address for {crypto_currency} on {network}: {e}")
        return None, None


def process_crypto_payment(crypto_currency, amount, recipient_address):
    """
    Simulate sending cryptocurrency to the recipient.
    """
    try:
        # In a production system, implement the actual logic to send funds
        logger.info(f"Simulated sending {amount} {crypto_currency} to {recipient_address}.")
        return True
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        return False



def process_crypto_payment(crypto_currency, amount, recipient_address, memo=None):
    """
    Send cryptocurrency to the recipient using the KuCoin API.
    
    Args:
        crypto_currency (str): The currency to be sent (e.g., 'BTC', 'ETH').
        amount (float): The amount to be sent.
        recipient_address (str): The recipient's wallet address.
        memo (str): Optional memo for the transaction (required for some coins like XLM, XRP).
    
    Returns:
        bool: True if the transfer was successful, False otherwise.
    """
    try:
        # Construct the withdrawal payload
        withdrawal_data = {
            "currency": crypto_currency,
            "address": recipient_address,
            "amount": str(amount),  # Amount as a string
            "chain": "",  # Optional: Specify the chain if required (e.g., ERC20, TRC20)
        }

        if memo:
            withdrawal_data["memo"] = memo  # Add memo if needed for the currency

        # Send the withdrawal request to KuCoin
        response = exchange.privatePostWithdrawals(withdrawal_data)
        
        if response.get("code") == "200000":
            logger.info(f"Successfully sent {amount} {crypto_currency} to {recipient_address}.")
            return True
        else:
            error_message = response.get("msg", "Unknown error occurred during withdrawal.")
            logger.error(f"Failed to send funds: {error_message}")
            return False
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        return False

logger = logging.getLogger(__name__)  # Ensure logger is properly configured

def fetch_coins(request):
    """
    Fetch available coins from the KuCoin API using the /api/v1/currencies endpoint.
    """
    base_url = "https://api.kucoin.com"
    endpoint = "/api/v1/currencies"
    headers = {
        'KC-API-KEY': settings.KUCOIN_API_KEY,
        'KC-API-SECRET': settings.KUCOIN_API_SECRET,
        'KC-API-PASSPHRASE': settings.KUCOIN_API_PASSPHRASE,
    }

    try:
        # Make the request to KuCoin API
        logger.debug(f"Sending request to: {base_url}{endpoint}")
        response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=10)
        
        # Log the response for debugging
        logger.debug(f"Response Status: {response.status_code}, Response Text: {response.text}")

        # Handle successful response
        if response.status_code == 200:
            try:
                data = response.json()
            except ValueError:
                logger.error("Failed to parse JSON response")
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON response from API'}, status=500)

            currencies = data.get("data", [])
            logger.debug(f"Parsed Currencies: {currencies}")

            # Set default coins to filter
            default_coins = ["USDT", "BTC", "ETH", "SOL", "TRX"]
            coins = [
                {"symbol": currency.get("currency", ""), "name": currency.get("fullName", "")}
                for currency in currencies
                if currency.get("currency") in default_coins
            ]

            if not coins:
                logger.warning("Default coins not found in the API response")
                return JsonResponse({'status': 'error', 'message': 'No default coins found'}, status=404)

            return JsonResponse({'status': 'success', 'coins': coins}, status=200)

        # Handle API errors
        else:
            logger.error(f"API Error: {response.status_code}, {response.text}")
            return JsonResponse({'status': 'error', 'message': f"API request failed with status {response.status_code}"}, status=500)

    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return JsonResponse({'status': 'error', 'message': 'Request timed out'}, status=504)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return JsonResponse({'status': 'error', 'message': 'Connection error. Please try again later.'}, status=503)

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {e}")
        return JsonResponse({'status': 'error', 'message': f"Network error: {str(e)}"}, status=500)



def fetch_networks(request, coin):
    """
    Fetch available networks for a given coin using KuCoin API.
    Includes default network mappings for selected coins.
    """
    logging.debug(f"Received request for networks of coin: {coin}")

    # KuCoin API details
    base_url = "https://api.kucoin.com"
    endpoint = f"/api/v1/currencies/{coin.upper()}"  # Normalize coin to uppercase
    headers = {
        'KC-API-KEY': settings.KUCOIN_API_KEY,
        'KC-API-SECRET': settings.KUCOIN_API_SECRET,
        'KC-API-PASSPHRASE': settings.KUCOIN_API_PASSPHRASE,
    }

    # Validate API credentials
    if not all([settings.KUCOIN_API_KEY, settings.KUCOIN_API_SECRET, settings.KUCOIN_API_PASSPHRASE]):
        logging.error("Missing KuCoin API credentials in settings.")
        return JsonResponse({'status': 'error', 'message': 'API credentials not configured'}, status=500)

    # Default networks for known coins
    default_networks = {
        "BTC": ["BTC"],  # Bitcoin
        "ETH": ["ERC20", "BEP20", "POLYGON"],  # Ethereum
        "USDT": ["ERC20", "TRC20", "BEP20"],  # Tether
        "SOL": ["SOL"],  # Solana
        "TRX": ["TRC20", "BEP20"],  # TRON
    }

    # Return default networks if coin exists in predefined list
    if coin.upper() in default_networks:
        networks = [{"name": network, "code": network} for network in default_networks[coin.upper()]]
        logging.debug(f"Returning default networks for {coin}: {networks}")
        return JsonResponse({'status': 'success', 'networks': networks})

    try:
        # Call KuCoin API to fetch networks for the specified coin
        url = f"{base_url}{endpoint}"
        logging.debug(f"Making API request to {url} with headers: {headers}")

        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise error for HTTP 4xx/5xx responses

        data = response.json()
        logging.debug(f"API response: {data}")

        # Extract network data from the API response
        networks_data = data.get("data", {}).get("chains", [])
        networks = [{"name": net.get("chainName", ""), "code": net.get("chain", "")} for net in networks_data]

        if not networks:
            logging.warning(f"No networks found for coin: {coin}")
            return JsonResponse({'status': 'error', 'message': 'No networks found for this coin'}, status=404)

        logging.debug(f"Returning networks for {coin}: {networks}")
        return JsonResponse({'status': 'success', 'networks': networks})

    except requests.exceptions.RequestException as e:
        # Handle network-related errors
        logging.error(f"Network error while fetching networks for {coin}: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f"Network error: {str(e)}"}, status=500)

    except Exception as e:
        # Handle unexpected errors
        logging.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)




def fetch_symbols():
    """
    Fetch all tradable symbols (trading pairs) from the KuCoin API.
    """
    base_url = "https://api.kucoin.com"
    endpoint = "/api/v1/symbols"

    try:
        # Make the request to KuCoin API
        response = requests.get(f"{base_url}{endpoint}")
        response.raise_for_status()  # Raise an error for 4xx or 5xx responses
        data = response.json()

        # Check if the response contains symbol data
        symbols_data = data.get('data', [])
        if not symbols_data:
            print("No symbol data found in KuCoin API response")
            return []

        # Extract and return the list of trading pairs (symbols)
        symbols = [
            {
                "symbol": item["symbol"],
                "base_currency": item["baseCurrency"],
                "quote_currency": item["quoteCurrency"],
                "enable_trading": item["enableTrading"]
            }
            for item in symbols_data
        ]
        return symbols

    except requests.exceptions.RequestException as e:
        # Handle network-related errors or request exceptions
        print(f"Network error: {str(e)}")
        return []

def fetch_symbols_with_retry(max_retries=5, retry_delay=5):
    """
    Fetch all tradable symbols (trading pairs) from the KuCoin API with retry logic.
    """
    base_url = "https://api.kucoin.com"
    endpoint = "/api/v1/symbols"
    attempt = 0

    while attempt < max_retries:
        try:
            print(f"Attempt {attempt + 1} of {max_retries}...")
            response = requests.get(f"{base_url}{endpoint}")
            response.raise_for_status()  # Raise an error for 4xx or 5xx responses

            # Parse and return the data if successful
            data = response.json()
            symbols_data = data.get('data', [])
            if not symbols_data:
                print("No symbol data found in KuCoin API response")
                return []

            symbols = [
                {
                    "symbol": item["symbol"],
                    "base_currency": item["baseCurrency"],
                    "quote_currency": item["quoteCurrency"],
                    "enable_trading": item["enableTrading"]
                }
                for item in symbols_data
            ]
            return symbols

        except requests.exceptions.RequestException as e:
            attempt += 1
            print(f"Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Could not fetch symbols.")
                return []

# Example usage
if __name__ == "__main__":
    symbols = fetch_symbols_with_retry()
    if symbols:
        print(f"Fetched {len(symbols)} symbols successfully.")
    else:
        print("Failed to fetch symbols.")



def monitor_transactions():
    """Function to monitor incoming transactions."""
    for user_wallet in Wallet.objects.all():
        for crypto, details in user_wallet.crypto_balance.items():
            wallet_address = details["wallet_address"]
            balance = web3.eth.get_balance(wallet_address)

            # Convert balance from Wei to Ether (or the relevant cryptocurrency unit)
            new_balance = Web3.fromWei(balance, 'ether')

            # Check if there's a new deposit
            if new_balance > details["balance"]:
                deposit_amount = new_balance - details["balance"]
                details["balance"] = new_balance
                user_wallet.crypto_balance[crypto] = details
                user_wallet.save()

                # Record the transaction
                Transaction.objects.create(
                    user=user_wallet.user,
                    amount=deposit_amount,
                    currency="CRYPTO",
                    crypto_type=crypto,
                    wallet_address=wallet_address,
                )


# @csrf_exempt
# def create_paypal_order(request):
#     """
#     Creates a PayPal order and returns the order ID.
#     """
#     try:
#         data = json.loads(request.body)
#         amount = data.get('amount')
#         currency = data.get('currency', 'USD')

#         if not amount or float(amount) <= 0:
#             return JsonResponse({'error': 'Invalid amount.'}, status=400)

#         access_token = get_paypal_access_token()
#         headers = {"Authorization": f"Bearer {access_token}"}
#         order_data = {
#             "intent": "CAPTURE",
#             "purchase_units": [{
#                 "amount": {
#                     "currency_code": currency,
#                     "value": str(amount)
#                 }
#             }],
#         }

#         response = requests.post(
#             f"{PAYPAL_API_BASE}/v2/checkout/orders",
#             json=order_data,
#             headers=headers,
#         )
#         response.raise_for_status()
#         order = response.json()

#         return JsonResponse({
#             'id': order['id'],
#             'links': order['links'],
#         })
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)

# @csrf_exempt
# def capture_paypal_order(request, order_id):
#     """
#     Captures a PayPal order.
#     """
#     try:
#         access_token = get_paypal_access_token()
#         headers = {"Authorization": f"Bearer {access_token}"}
#         response = requests.post(
#             f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
#             headers=headers,
#         )
#         response.raise_for_status()
#         capture_data = response.json()
#         return JsonResponse(capture_data)
#     except Exception as e:
#         return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    endpoint_secret = 'your-stripe-endpoint-secret'
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        session_id = session.get('id')
        # Update deposit status to completed
        deposit = FiatDeposit.objects.get(transaction_reference=session_id)
        deposit.status = 'completed'
        deposit.save()

    return HttpResponse(status=200)

@csrf_exempt
def coinbase_webhook(request):
    payload = request.body
    signature = request.META.get('HTTP_CB_SIGNATURE')
    # Verify Coinbase webhook signature here (you can use HMAC)
    
    # Process the deposit confirmation from Coinbase
    if 'event' in payload:
        event = payload['event']
        if event['type'] == 'deposit':
            # Handle deposit event
            # e.g., Update the deposit record to 'completed'
            deposit = Deposit.objects.get(deposit_address=event['data']['address'])
            deposit.status = 'completed'
            deposit.save()

    return HttpResponse(status=200)


@login_required
def deposit_success(request):
    """
    View to handle the success response after Stripe payment.
    """
    # Here we handle the completion of the fiat deposit after successful payment
    session_id = request.GET.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)
    if session.payment_status == 'paid':
        fiat_deposit = FiatDeposit.objects.get(transaction_reference=session_id)
        fiat_deposit.status = 'completed'
        fiat_deposit.save()

        # Create a transaction record for the deposit
        Transaction.objects.create(
            user=request.user,
            transaction_type='deposit',
            amount=fiat_deposit.amount,
            currency=fiat_deposit.currency,
            status='completed',
            transaction_fee=0.0
        )

    return render(request, 'deposit_success.html', {'status': 'completed'})


@login_required
def deposit_cancel(request):
    """
    View to handle the cancel response from Stripe.
    """
    return render(request, 'deposit_cancel.html')


@login_required(login_url="login")
def deposit_status_view(request, tx_hash):
    from .blockchain_service import get_transaction_status
    status = get_transaction_status(tx_hash)
    return render(request, 'deposit-status.html', {'tx_hash': tx_hash, 'status': status})


# ============== Withdrawal Views ============== #

# Define a constant fee for simplicity (this can be dynamic based on currency or other parameters)
def kucoin_api_request(endpoint, data=None, method='POST'):
    """Helper function to interact with the KuCoin API."""
    url = f"https://api.kucoin.com{endpoint}"
    nonce = str(int(time.time() * 1000))
    api_key = settings.KUCOIN_API_KEY
    secret_key = settings.KUCOIN_SECRET_KEY
    passphrase = settings.KUCOIN_PASSPHRASE
    headers = {
        'KC-API-KEY': api_key,
        'KC-API-TIMESTAMP': nonce,
        'KC-API-PASSPHRASE': passphrase,
        'KC-API-SIGN': generate_signature(nonce, method, url, data, secret_key),
    }

    if method == 'POST':
        response = requests.post(url, json=data, headers=headers)
    else:
        response = requests.get(url, params=data, headers=headers)

    return response.json()

def generate_signature(nonce, method, url, data, secret_key):
    """Generate KuCoin API signature."""
    body = json.dumps(data) if data else ''
    str_to_sign = f"{nonce}{method}{url}{body}"
    signature = hmac.new(bytes(secret_key, 'utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(signature).decode('utf-8')

def withdraw(request):
    """
    Handle cryptocurrency withdrawal requests to KuCoin.
    """
    if request.method == 'POST':
        form = WithdrawForm(request.POST)
        
        if form.is_valid():
            # Extract cleaned data from the form
            amount = form.cleaned_data['amount']
            currency = form.cleaned_data['currency']
            withdrawal_address = form.cleaned_data['withdrawal_address']
            network = form.cleaned_data['network']
            
            # Calculate transaction fee (0.8% of the amount)
            transaction_fee = round(amount * 0.008, 8)  # Rounded to 8 decimal places
            
            # Validate the withdrawal amount
            if amount <= 0:
                return JsonResponse({'status': 'error', 'message': 'Invalid withdrawal amount.'})

            # Ensure that the user selected a valid network
            if not network:
                return JsonResponse({'status': 'error', 'message': 'Please select a network for the withdrawal.'})

            # Prepare the data for KuCoin API
            withdrawal_data = {
                "currency": currency,
                "amount": amount,
                "address": withdrawal_address,
                "memo": "",  # Optional, can be added depending on the coin
                "network": network
            }

            # Call KuCoin API to initiate withdrawal
            try:
                response = kucoin_api_request('/api/v1/withdrawals', withdrawal_data)
                
                if response.get('code') == '200000':
                    withdrawal_id = response['data']['withdrawalId']
                    return JsonResponse({
                        'status': 'success',
                        'withdrawal_id': withdrawal_id,
                        'message': 'Withdrawal successful.',
                        'transaction_fee': transaction_fee
                    })
                else:
                    return JsonResponse({'status': 'error', 'message': response.get('msg', 'Failed to withdraw.')})
            except Exception as e:
                logging.error(f"Error processing KuCoin withdrawal: {str(e)}")
                return JsonResponse({'status': 'error', 'message': 'An error occurred while processing the withdrawal.'})

        else:
            # If form is not valid, return errors
            return JsonResponse({'status': 'error', 'message': form.errors})

    else:
        # Initialize the form for a GET request (render the empty form)
        form = WithdrawForm()

    return render(request, 'withdraw.html', {'form': form})


def get_kucoin_data(request, coin_type=None):
    coins = ['BTC', 'ETH', 'USDT', 'SOL', 'TRX']
    
    # If a specific coin is requested, filter by that coin
    if coin_type and coin_type in coins:
        coins = [coin_type]

    url = "https://api.kucoin.com/api/v1/currencies"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        coin_data = []
        for item in data.get('data', []):
            if item['currency'] in coins:
                networks = item.get('chains', [])
                coin_data.append({
                    'symbol': item['currency'],
                    'networks': networks
                })

        return JsonResponse({'status': 'success', 'coins': coin_data})

    except requests.exceptions.RequestException as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def calculate_transaction_fee(amount, currency):
    """Calculate the transaction fee based on the currency."""
    if currency.lower() in ['btc', 'eth']:  # Assuming crypto has a fee of 0.6%
        return amount * TRANSACTION_FEE_PERCENTAGE
    else:
        # Example: No fee for fiat (expand based on your fiat logic)
        return 0.0


def process_crypto_withdrawal(user, amount, currency, withdrawal_address, transaction_fee_percentage=0.6):
    """
    Process a cryptocurrency withdrawal (subtracts fee, updates wallet).
    
    Args:
        user: The user requesting the withdrawal.
        amount: The amount of cryptocurrency to withdraw.
        currency: The cryptocurrency type (e.g., 'BTC', 'ETH').
        withdrawal_address: The withdrawal address for the cryptocurrency.
        transaction_fee_percentage: The percentage fee for the withdrawal. Default is 0.6%.

    Returns:
        Withdrawal object: The created withdrawal object with transaction details.
    
    Raises:
        ValidationError: If the user has insufficient funds.
    """
    wallet = user.wallet
    balance = wallet.get_balance(currency)

    # Calculate transaction fee as a percentage of the withdrawal amount
    transaction_fee = amount * (transaction_fee_percentage / 100)

    # Check if there are enough funds to cover the withdrawal and the transaction fee
    if amount + transaction_fee > balance:
        raise ValidationError('Insufficient funds.')

    # Create a transaction and log it
    try:
        tx_hash = send_crypto(wallet.wallet_address, wallet.private_key, withdrawal_address, amount)
    except Exception as e:
        # Handle transaction failure (e.g., API failure or insufficient network funds)
        raise ValidationError(f"Transaction failed: {str(e)}")

    # Deduct the withdrawal amount and transaction fee from the wallet
    wallet.debit_balance(currency, amount + transaction_fee)  # Adjust wallet balance (subtract fee + withdrawal amount)
    wallet.save()

    # Log the transaction in the Withdrawal model
    withdrawal = Withdrawal.objects.create(
        user=user,
        amount=amount,
        currency=currency,
        withdrawal_address=withdrawal_address,
        status='pending',  # The status will be updated later after the transaction is confirmed
        tx_hash=tx_hash,
        fee=transaction_fee,
    )

    return withdrawal


def process_fiat_withdrawal(user, amount, currency, withdrawal_address, transaction_fee):
    """
    Placeholder function for fiat withdrawal (add actual logic for payment gateway).
    """
    wallet = user.wallet
    balance = wallet.get_balance(currency)

    if amount + transaction_fee > balance:
        raise ValidationError('Insufficient funds.')

    # Example: Deduct from wallet and process fiat withdrawal
    wallet.debit_balance(currency, amount + transaction_fee)
    wallet.save()

    # Log fiat transaction (you would integrate a payment gateway here)
    withdrawal = Withdrawal.objects.create(
        user=user,
        amount=amount,
        currency=currency,
        withdrawal_address=withdrawal_address,
        status='pending',  # Status may be updated once the payment gateway processes the withdrawal
        fee=transaction_fee,
    )

    return withdrawal


def send_crypto(sender_address, private_key, recipient_address, amount):
    """Simulate sending cryptocurrency (use real blockchain API in production)."""
    nonce = web3.eth.getTransactionCount(Web3.toChecksumAddress(sender_address))
    tx = {
        'nonce': nonce,
        'to': Web3.toChecksumAddress(recipient_address),
        'value': web3.toWei(amount, 'ether'),
        'gas': 21000,
        'gasPrice': web3.toWei('50', 'gwei'),
    }
    signed_tx = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return tx_hash.hex()


def process_deposit(user, amount, currency):
    """
    Process a cryptocurrency deposit via Coinbase.
    """
    # Create a new deposit entry
    deposit = Deposit.objects.create(
        user=user,
        amount=amount,
        currency=currency,
        deposit_address=user.wallet.wallet_address,
        status='pending'
    )

    # Get a new deposit address from Coinbase
    wallet = coinbase_client.get_account(currency)
    payment_address = wallet.create_address()

    # Update the deposit address and save the record
    deposit.deposit_address = payment_address.address
    deposit.save()

    return deposit


def process_fiat_deposit(user, amount, currency, payment_method, session_reference):
    """
    Process a fiat deposit via a payment gateway (Stripe).
    """
    fiat_deposit = FiatDeposit.objects.create(
        user=user,
        amount=amount,
        currency=currency,
        payment_method=payment_method,
        status='pending',
        transaction_reference=session_reference
    )

    # Record the fiat deposit as a transaction
    Transaction.objects.create(
        user=user,
        transaction_type='deposit',
        amount=amount,
        currency=currency,
        status='pending',
        transaction_fee=0.0
    )

    return fiat_deposit


def process_withdrawal(user, amount, currency, withdrawal_address):
    """
    Process cryptocurrency and fiat withdrawals.
    """
    if currency.lower() in ['btc', 'eth']:  # Handle crypto withdrawal via Coinbase
        # Logic for crypto withdrawal using Coinbase API or blockchain SDK
        withdrawal = Withdrawal.objects.create(
            user=user,
            amount=amount,
            currency=currency,
            withdrawal_address=withdrawal_address,
            status='pending'
        )
        return withdrawal
    else:
        # Logic for fiat withdrawal via bank transfer or other methods
        withdrawal = Withdrawal.objects.create(
            user=user,
            amount=amount,
            currency=currency,
            withdrawal_address=withdrawal_address,
            status='pending'
        )
        return withdrawal

@login_required
def transaction_history_view(request):
    transactions = Transaction.objects.filter(user=request.user).order_by('-timestamp')

    try:
        crypto_data = crypto_chart(request)
    except Exception as e:
        crypto_data = {"status": "error", "message": str(e)}

    return render(request, 'transaction_history.html', {
        'transactions': transactions,
        'crypto_data': crypto_data
    })



# ============== Helper Functions ============== #

# Constants for withdrawal logic
TRANSACTION_FEE_PERCENTAGE = 0.008  # 0.8%

@login_required(login_url="login")
def wallet(request):
    """
    View for displaying and updating the wallet, and handling withdrawals.
    """
    wallet = Wallet.objects.get(user=request.user)

    if request.method == 'POST' and 'withdraw' in request.POST:
        # Handle withdrawal logic
        amount = float(request.POST.get('amount'))  # Withdrawal amount
        currency = request.POST.get('currency')  # Currency (BTC, ETH, USDT)

        # Ensure the user is trying to withdraw a valid amount
        if amount <= 0:
            return JsonResponse({'status': 'error', 'message': 'Invalid withdrawal amount.'})

        # Calculate the transaction fee (0.8%)
        transaction_fee = amount * TRANSACTION_FEE_PERCENTAGE
        total_withdrawal_amount = amount + transaction_fee

        # Ensure the user has sufficient funds
        available_balance = wallet.get_balance(currency)
        if available_balance < total_withdrawal_amount:
            return JsonResponse({'status': 'error', 'message': f'Insufficient balance. Available: {available_balance} {currency.upper()}.'})

        # Deduct the amount and the fee from the wallet
        wallet.debit_balance(currency, total_withdrawal_amount)

        # Process the withdrawal via KuCoin API
        withdrawal_success = process_kucoin_withdrawal(request.user, amount, currency, transaction_fee)
        if not withdrawal_success:
            return JsonResponse({'status': 'error', 'message': 'Withdrawal processing failed. Please try again later.'})

        return JsonResponse({'status': 'success', 'message': f'Withdrawal of {amount} {currency.upper()} successful.'})

    # Handle form submission for updating wallet balance (admin functionality or user balance management)
    if request.method == 'POST' and 'update_wallet' in request.POST:
        form = WalletForm(request.POST, instance=wallet)
        if form.is_valid():
            form.save()  # Save the updated wallet information
            return redirect('wallet')  # Redirect to the wallet page
    else:
        form = WalletForm(instance=wallet)  # Pre-populate the form with the user's current wallet data

    return render(request, 'wallet.html', {'form': form, 'wallet': wallet})


def process_kucoin_withdrawal(user, amount, currency, transaction_fee):
    """
    Processes the withdrawal using the KuCoin API.
    """
    # KuCoin API credentials
    API_KEY = os.getenv('KUCOIN_API_KEY')
    API_SECRET = os.getenv('KUCOIN_API_SECRET')
    API_PASSPHRASE = os.getenv('KUCOIN_API_PASSPHRASE')

    if not (API_KEY and API_SECRET and API_PASSPHRASE):
        print("KuCoin API credentials are not set.")
        return False

    # Initialize KuCoin client
    client = KuCoinClient(API_KEY, API_SECRET, API_PASSPHRASE)

    try:
        # Define the withdrawal address (for simplicity, using a placeholder here)
        withdrawal_address = OWNER_WALLET_ADDRESSES.get(currency.upper())
        if not withdrawal_address:
            print(f"Withdrawal address not configured for {currency.upper()}.")
            return False

        # Process the withdrawal via KuCoin API
        response = client.create_withdrawal(
            currency=currency,
            amount=amount,
            address=withdrawal_address,
            fee=transaction_fee
        )

        if response.get("code") == "200000":
            print(f"KuCoin withdrawal successful for {user.username}: {amount} {currency.upper()}.")
            return True
        else:
            print(f"KuCoin withdrawal failed: {response.get('msg')}")
            return False

    except Exception as e:
        print(f"Error processing KuCoin withdrawal: {e}")
        return False


@login_required(login_url="login")
def update_wallet(request):
    wallet = Wallet.objects.get(user=request.user)
    
    if request.method == 'POST':
        form = WalletForm(request.POST, instance=wallet)
        if form.is_valid():
            form.save()
            return redirect('wallet')  # Redirect to the wallet view after successful update
    else:
        form = WalletForm(instance=wallet)
    
    return render(request, 'update_wallet.html', {'form': form})



def error_page(request):
    """
    View to render a custom error page.
    """
    return render(request, 'error_page.html', {'error_message': 'An unexpected error occurred. Please try again later.'})


def connect_wallet_view(request):
    if request.method == 'POST':
        wallet_address = request.POST.get('wallet_address')

        if len(wallet_address) == 42:  # Ethereum
            balance = get_ethereum_balance(wallet_address)
        elif len(wallet_address) == 34:  # Bitcoin
            balance = get_bitcoin_balance(wallet_address)
        else:
            messages.error(request, 'Invalid wallet address format.')
            return redirect('connect_wallet')

        if balance:
            messages.success(request, f"Wallet connected successfully! Balance: {balance}")
        else:
            messages.error(request, 'Could not connect to the blockchain.')
        
        return redirect('dashboard')
    return render(request, 'wallet/connect_wallet.html')


@login_required(login_url="login")
def fund_wallet(request):
    """
    View to fund the user's wallet via a deposit (either crypto or fiat).
    """
    if request.method == 'POST':
        currency = request.POST.get('currency')
        amount = Decimal(request.POST.get('amount', 0))

        if amount <= 0:
            return JsonResponse({'error': 'Invalid deposit amount.'}, status=400)

        # Get or create wallet for the user
        wallet, created = Wallet.objects.get_or_create(user=request.user)

        # Simulate funding (add the amount to the wallet)
        if currency.lower() == 'btc':
            wallet.balance_btc += amount
        elif currency.lower() == 'eth':
            wallet.balance_eth += amount
        else:
            wallet.balance_usd += amount  # For fiat

        wallet.save()

        return JsonResponse({
            'message': f'Wallet funded successfully. New balance: {wallet.balance}',
            'new_balance': float(wallet.balance)
        })

    return JsonResponse({'error': 'Invalid request method.'}, status=405)




# Function to handle the MT5 connection
# Connect to MetaTrader 5
# Connect to MetaTrader 5
def connect_to_mt5(request):
    if not mt5.initialize():
        return JsonResponse({"status": "error", "message": "MetaTrader 5 connection failed: " + mt5.last_error()[1]})
    return JsonResponse({"status": "success", "message": "Connected to MetaTrader 5"})

# Get account info
def get_account_info(request):
    account_info = mt5.account_info()
    if account_info is None:
        return JsonResponse({"status": "error", "message": "Failed to retrieve account info: " + mt5.last_error()[1]})
    return JsonResponse({"status": "success", "data": account_info._asdict()})

# Get MetaTrader 5 chart data
def get_mt5_chart(request):
    symbol = request.GET.get("symbol", "EURUSD")
    timeframe = int(request.GET.get("timeframe", mt5.TIMEFRAME_H1))

    try:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

    if rates is None:
        return JsonResponse({"status": "error", "message": "Failed to retrieve chart data: " + mt5.last_error()[1]})

    chart_data = [{
        "time": datetime.utcfromtimestamp(int(rate[0])).strftime('%Y-%m-%d %H:%M:%S'),  # Convert timestamp to readable format
        "open": float(rate[1]),
        "high": float(rate[2]),
        "low": float(rate[3]),
        "close": float(rate[4])
    } for rate in rates]

    return JsonResponse({"status": "success", "data": chart_data})

# Place trade
# def place_trade(request):
#     if not mt5.initialize():
#         return JsonResponse({"status": "error", "message": "MetaTrader 5 initialization failed: " + mt5.last_error()[1]})

#     trade_request = {
#         "action": mt5.TRADE_ACTION_DEAL,
#         "symbol": "EURUSD",
#         "volume": 0.1,
#         "type": mt5.ORDER_TYPE_BUY,
#         "price": mt5.symbol_info_tick("EURUSD").ask,
#         "deviation": 20,
#         "magic": 234000,
#         "comment": "Python script trade",
#         "type_time": mt5.ORDER_TIME_GTC,
#         "type_filling": mt5.ORDER_FILLING_IOC,
#     }

#     result = mt5.order_send(trade_request)

#     if result.retcode != mt5.TRADE_RETCODE_DONE:
#         return JsonResponse({"status": "error", "message": f"Trade failed: {result.comment}"})

#     return JsonResponse({"status": "success", "trade_details": result._asdict()})

# Home view
# def home_view(request):
#     api_url = "https://api.coingecko.com/api/v3/coins/markets"
#     params = {
#         "vs_currency": "usd",
#         "order": "market_cap_desc",
#         "per_page": 10,
#         "page": 1,
#         "sparkline": False,
#     }

#     try:
#         response = requests.get(api_url, params=params)
#         response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
#         top_10_crypto_data_global = response.json()

#         # Transform the data to match the template's expectations
#         formatted_data = [
#             {
#                 "symbol": crypto["symbol"].upper(),
#                 "name": crypto["name"],
#                 "current_price": crypto["current_price"],
#                 "market_cap": crypto["market_cap"],
#                 "price_change_percentage_24h": crypto["price_change_percentage_24h"],
#             }
#             for crypto in top_10_crypto_data_global
#         ]
#     except requests.RequestException as e:
#         # Log the error and provide a fallback
#         print(f"Error fetching data from CoinGecko: {e}")
#         formatted_data = []

#     context = {
#         "top_10_crypto_data_global": formatted_data,
#     }
#     return render(request, "home.html", context)


#========================= Dashboard View ================================

def signup_with_referrer_view(request, referral_code):
    # Handle the referral code logic
    try:
        referrer = Profile.objects.get(referral_code=referral_code)
    except Profile.DoesNotExist:
        referrer = None

    form = CustomUserCreationForm(request.POST or None)
    if form.is_valid():
        user = form.save(commit=False)
        user.password = make_password(form.cleaned_data['password1'])
        user.email = form.cleaned_data['email']
        user.save()

        # Optionally associate the referrer with the new user
        if referrer:
            user.profile.referrer = referrer
            user.profile.save()

        messages.success(request, 'You have successfully signed up!', extra_tags='success')
        return redirect('login')

    return render(request, 'login.html', {'form': form, 'referral_code': referral_code})


def search_view(request):
    query = request.GET.get('q', '')  # Get the search query from the request
    cryptocurrencies = Cryptocurrency.objects.filter(name__icontains=query)  # Search for cryptocurrencies by name

    context = {
        'cryptocurrencies': cryptocurrencies,
        'query': query
    }

    return render(request, 'search.html', context)


@login_required(login_url="login")
def add_to_portfolio_view(request):
    if request.method == 'POST':
        form = CryptocurrencyForm(request.POST)
        if form.is_valid():
            # Process form and add cryptocurrency to the user's portfolio
            crypto = form.save(commit=False)
            crypto.user = request.user
            crypto.save()

            # Optionally, update the user's portfolio
            portfolio, created = Portfolio.objects.get_or_create(user=request.user)
            portfolio.cryptocurrencies.add(crypto)

            messages.success(request, f"{crypto.name} has been added to your portfolio!")
            return redirect('portfolio')
    else:
        form = CryptocurrencyForm()

    return render(request, 'add_to_portfolio.html', {'form': form})

def add_cryptocurrency(request):
    if request.method == 'POST':
        form = CryptocurrencyForm(request.POST)
        if form.is_valid():
            form.save()
    else:
        form = CryptocurrencyForm()
    return render(request, 'add_cryptocurrency.html', {'form': form})


def is_admin(user):
    return user.is_superuser  # Only allow superusers to access this view

@user_passes_test(is_admin)
def admin_transaction_view(request):
    transactions = Transaction.objects.all().order_by('-created_at')
    return render(request, 'admin_transactions.html', {'transactions': transactions})



# View to handle trade execution (Buy, Sell, Hold)
@login_required
def execute_trade(request, symbol, transaction_type):
    wallet = Wallet.objects.get(user=request.user)
    amount = Decimal(request.POST.get('amount', 0))

    if transaction_type == 'buy':
        if wallet.fiat_balance < amount:
            messages.error(request, "Insufficient fiat balance.")
            return redirect('trade')

        wallet.fiat_balance -= amount + (amount * Decimal('0.005'))
        wallet.crypto_balance += (amount - (amount * Decimal('0.005'))) / fetch_market_data(symbol).price
    elif transaction_type == 'sell':
        if wallet.crypto_balance < amount:
            messages.error(request, "Insufficient crypto balance.")
            return redirect('trade')

        wallet.crypto_balance -= amount + (amount * Decimal('0.005'))
        wallet.fiat_balance += (amount - (amount * Decimal('0.005'))) * fetch_market_data(symbol).price

    wallet.save()

    Transaction.objects.create(
        user=request.user,
        transaction_type=transaction_type,
        amount=amount,
        status='completed',
        symbol=symbol,
    )

    # Display readonly MetaTrader chart
    mt5_chart_data = crypto_chart(request)

    messages.success(request, f"Successfully executed {transaction_type} for {amount} {symbol}.")
    return render(request, 'dashboard.html', {'mt5_chart_data': mt5_chart_data})



# View to create an automated investment plan
@login_required(login_url="login")
def create_investment_plan(request, symbol, amount, frequency):
    if frequency == 'weekly':
        next_purchase = datetime.now() + timedelta(weeks=1)
    elif frequency == 'monthly':
        next_purchase = datetime.now() + timedelta(weeks=4)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid frequency'})

    investment_plan = InvestmentPlan.objects.create(
        user=request.user,
        symbol=symbol,
        amount_per_interval=amount,
        frequency=frequency,
        next_purchase=next_purchase
    )

    return JsonResponse({
        'status': 'success',
        'plan_id': investment_plan.id,
        'message': f'Automated investment plan for {symbol} created.'
    })

# View to stake cryptocurrency
@login_required(login_url="login")
def stake_crypto(request, symbol, amount, staking_duration):
    # Check if the user has enough balance to stake
    user_balance = request.user.portfolio.get_balance(symbol)  # Assuming a method to get portfolio balance
    if user_balance < amount:
        return JsonResponse({'status': 'error', 'message': 'Insufficient balance to stake'})

    # Create staking record
    staking = Staking.objects.create(
        user=request.user,
        symbol=symbol,
        amount_staked=amount,
        staking_duration=staking_duration,  # Duration in days
        interest_rate=5.0  # Placeholder interest rate
    )

    # Update the user's portfolio by deducting staked amount
    request.user.portfolio.update_balance(symbol, -amount)  # Assuming a method to update balance

    return JsonResponse({
        'status': 'success',
        'staking_id': staking.id,
        'message': f'{amount} {symbol} successfully staked for {staking_duration} days.'
    })


class ProfitLossAnalysisView(View):
    def get(self, request):
        user = request.user
        portfolios = Portfolio.objects.filter(user=user)
        
        results = []
        for portfolio in portfolios:
            gain_loss = float(portfolio.current_value) - float(portfolio.total_invested)
            results.append({
                'asset_name': portfolio.asset_name,
                'total_invested': float(portfolio.total_invested),
                'current_value': float(portfolio.current_value),
                'gain_loss': gain_loss
            })
        
        return render(request, 'analytics/profit_loss_analysis.html', {'data': results})


class TaxReportingView(View):
    def get(self, request):
        user = request.user
        transactions = Transaction.objects.filter(user=user)
        
        return render(request, 'analytics/tax_reporting.html', {'transactions': transactions})


class PerformanceMetricsView(View):
    def get(self, request):
        user = request.user
        portfolios = Portfolio.objects.filter(user=user)
        
        performance_data = []
        for portfolio in portfolios:
            avg_buy_price = float(portfolio.total_invested) / float(portfolio.total_units) if portfolio.total_units > 0 else 0
            roi = (float(portfolio.current_value) - float(portfolio.total_invested)) / float(portfolio.total_invested) * 100 if portfolio.total_invested > 0 else 0
            
            performance_data.append({
                'asset_name': portfolio.asset_name,
                'average_buy_price': avg_buy_price,
                'total_roi': roi,
                'current_value': float(portfolio.current_value),
                'total_units': float(portfolio.total_units)
            })
        
        return render(request, 'analytics/performance_metrics.html', {'data': performance_data})
