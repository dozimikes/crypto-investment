from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from .models import Wallet,Withdraw, CryptoNetwork, Deposit, Trade, Cryptocurrency, Portfolio, Profile, ContactModel, Service
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from requests.exceptions import RequestException
import requests
import ccxt
import os
import time
from .utils import fetch_networks, generate_kucoin_signature
from django.conf import settings  # Ensure API keys are set in settings.py
from hashlib import sha256
import base64
import hmac


# class ContactForm(forms.ModelForm):
#     class Meta:
#         model = ContactModel
#         fields = ['name', 'email', 'message']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your name'}),
#             'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}),
#             'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your message here...', 'rows': 5}),
#         }


class WithdrawForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=0.00000001,
        label="Amount",
        widget=forms.NumberInput(attrs={'placeholder': 'Amount to withdraw'})
    )
    currency = forms.ChoiceField(
        choices=[('btc', 'BTC'), ('eth', 'ETH')],  # Add other cryptocurrencies as needed
        label="Currency"
    )
    withdrawal_address = forms.CharField(
        max_length=255,
        label="Withdrawal Address",
        widget=forms.TextInput(attrs={'placeholder': 'Enter your withdrawal address'})
    )
    network = forms.ChoiceField(
        choices=[],
        label="Network",
        required=True
    )
    transaction_fee = forms.DecimalField(
        max_digits=20,
        decimal_places=8,
        label="Transaction Fee",
        required=False,
        initial=0.0,
        widget=forms.NumberInput(attrs={'readonly': 'readonly'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        currency = self.data.get('currency') or None
        if currency:
            self.fields['network'].choices = self.get_network_choices(currency)
        else:
            self.fields['network'].choices = []

    def get_network_choices(self, currency):
        """Fetch available networks for the selected currency using KuCoin API."""
        api_url = f"https://api.kucoin.com/api/v1/currencies/{currency.upper()}"
        try:
            headers = self.get_kucoin_headers()
            response = requests.get(api_url, headers=headers)
            data = response.json()

            if response.status_code == 200 and data.get("code") == "200000":
                networks = data.get("data", {}).get("chains", [])
                return [(network["chainName"], network["chainName"]) for network in networks]
            else:
                return []
        except Exception as e:
            print(f"Error fetching networks for {currency}: {str(e)}")
            return []

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        currency = cleaned_data.get('currency')
        withdrawal_address = cleaned_data.get('withdrawal_address')
        network = cleaned_data.get('network')

        # Validate network selection
        if not network:
            raise forms.ValidationError("Please select a network for the withdrawal.")

        # Validate the withdrawal address
        if withdrawal_address and not self.is_valid_address(withdrawal_address, network):
            raise forms.ValidationError(f"Invalid withdrawal address for {currency.upper()} on {network}.")

        # Calculate transaction fee
        transaction_fee = self.calculate_transaction_fee(amount, currency, network)
        if transaction_fee > amount * 0.06:  # Ensure the fee does not exceed 6%
            raise forms.ValidationError("Transaction fee exceeds the allowable percentage.")
        cleaned_data['transaction_fee'] = transaction_fee

        # Process withdrawal via KuCoin API
        self.process_kucoin_withdrawal(currency, amount, withdrawal_address, network, transaction_fee)

        return cleaned_data

    def calculate_transaction_fee(self, amount, currency, network):
        """Calculate transaction fees using KuCoin API."""
        try:
            api_url = f"https://api.kucoin.com/api/v1/currencies/{currency.upper()}"
            headers = self.get_kucoin_headers()
            response = requests.get(api_url, headers=headers)
            data = response.json()

            if response.status_code == 200 and data.get("code") == "200000":
                chains = data.get("data", {}).get("chains", [])
                for chain in chains:
                    if chain["chainName"] == network:
                        return float(chain["withdrawalMinFee"])
            return 0.0
        except Exception as e:
            print(f"Error calculating fee for {currency}: {str(e)}")
            return 0.0

    def is_valid_address(self, address, network):
        """Validate the withdrawal address format based on the selected network."""
        # Example validation logic for addresses
        if network in ['ERC20', 'BEP20'] and not address.startswith('0x'):
            return False
        elif network == 'Bitcoin' and not len(address) >= 26:
            return False
        # Add more validation rules for other networks if needed
        return True

    def process_kucoin_withdrawal(self, currency, amount, address, network, fee):
        """Process the withdrawal using KuCoin API."""
        api_url = "https://api.kucoin.com/api/v1/withdrawals"
        headers = self.get_kucoin_headers()
        payload = {
            "currency": currency.upper(),
            "address": address,
            "amount": str(amount),
            "memo": None,  # Add memo if required
            "chain": network
        }
        try:
            response = requests.post(api_url, json=payload, headers=headers)
            if response.status_code != 200 or response.json().get("code") != "200000":
                raise forms.ValidationError("Failed to process withdrawal. Please try again later.")
        except Exception as e:
            raise forms.ValidationError(f"Error processing withdrawal: {e}")

    def get_kucoin_headers(self):
        """Generate headers for KuCoin API requests."""
        api_key = settings.KUCOIN_API_KEY
        api_secret = settings.KUCOIN_API_SECRET
        api_passphrase = settings.KUCOIN_API_PASSPHRASE
        timestamp = str(int(time.time() * 1000))

        str_to_sign = f"{timestamp}GET/api/v1/withdrawals"
        signature = base64.b64encode(
            hmac.new(api_secret.encode(), str_to_sign.encode(), sha256).digest()
        )

        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature.decode(),
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": api_passphrase,
            "KC-API-KEY-VERSION": "2"
        }
        return headers



class WalletForm(forms.ModelForm):
    class Meta:
        model = Wallet
        fields = ['user', 'balance', 'currency', 'address']  # Modify based on your model

    user = forms.CharField(
        max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    balance = forms.DecimalField(
        max_digits=20, decimal_places=8, required=True, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Wallet Balance'})
    )
    currency = forms.ChoiceField(
        choices=[('btc', 'Bitcoin'), ('eth', 'Ethereum'), ('usdt', 'Tether')], 
        required=True, widget=forms.Select(attrs={'class': 'form-control'})
    )
    address = forms.CharField(
        max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Wallet Address'})
    )

    def clean_balance(self):
        balance = self.cleaned_data['balance']
        if balance < 0:
            raise forms.ValidationError("Balance cannot be negative.")
        return balance


class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        required=True, label='Username', help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True, label='Email', help_text='Required. Enter a valid email address.',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        required=True, label='Password', help_text='Required. Enter a valid password.',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        required=True, label='Password confirmation', help_text='Enter the same password as before, for verification.',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class LoginForm(forms.Form):
    # Fields for login
    username = forms.CharField(
        max_length=150, 
        required=True, 
        widget=forms.TextInput(attrs={
            'placeholder': 'Username',
            'class': 'form-control'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control'
        })
    )


class SignupForm(forms.Form):
    # Fields for signup
    username = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Username',
            'class': 'form-control'
        })
    )
    full_name = forms.CharField(
        max_length=255, 
        required=True, 
        widget=forms.TextInput(attrs={
            'placeholder': 'Full Name',
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Email',
            'class': 'form-control'
        })
    )
    phone = forms.CharField(
        max_length=15, 
        required=True, 
        widget=forms.TextInput(attrs={
            'placeholder': 'Phone Number',
            'class': 'form-control'
        })
    )
    signup_password1 = forms.CharField(
        label="Password", 
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control'
        })
    )
    signup_password2 = forms.CharField(
        label="Confirm Password", 
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm Password',
            'class': 'form-control'
        })
    )
    referral = forms.CharField(
        max_length=20, 
        required=False, 
        widget=forms.TextInput(attrs={
            'placeholder': 'Referral Code (Optional)',
            'class': 'form-control'
        })
    )
    terms = forms.BooleanField(
        required=True, 
        error_messages={
            'required': 'You must agree to the terms and conditions to register.'
        },
        widget=forms.CheckboxInput(attrs={
            'class': 'custom-control-input'
        })
    )

    def clean(self):
        cleaned_data = super().clean()

        # Validate signup passwords match
        password1 = cleaned_data.get('signup_password1')
        password2 = cleaned_data.get('signup_password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        # Check if username already exists
        username = cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")

        # Check if email already exists
        email = cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        
        # Optional: Validate the referral code (if provided)
        referral_code = cleaned_data.get('referral')
        if referral_code:
            # You can add logic to validate the referral code here
            # For example: check if the referral code exists in the database
            pass
        
        return cleaned_data

    def save(self):
        # Save new user during signup
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['signup_password1'],
        )
        
        # Split full name into first_name and last_name
        full_name = data.get('full_name', '')
        name_parts = full_name.split(' ')
        user.first_name = name_parts[0]  # First part as first name
        user.last_name = ' '.join(name_parts[1:])  # Remaining parts as last name
        
        # If you have a referral code, assign it or process it here
        referral_code = data.get('referral')
        if referral_code:
            # You can assign the referral code to the user or process it
            pass
        
        user.save()
        return user
    
    

class PhoneNumberForm(forms.Form):
    phone_number = forms.CharField(
        max_length=15, 
        required=True, 
        help_text="Enter your phone number.",
        widget=forms.TextInput(attrs={'placeholder': 'Phone Number', 'class': 'form-control'})
    )

class VerifyPhoneForm(forms.Form):
    verification_code = forms.CharField(
        max_length=6, 
        required=True, 
        help_text="Enter the verification code sent to your phone.",
        widget=forms.TextInput(attrs={'placeholder': 'Verification Code', 'class': 'form-control'})
    )


import requests
from django import forms
from .models import Deposit

class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ['user', 'crypto_currency', 'network', 'deposit_address', 'memo_tag', 'transaction_fee']

    # Cryptocurrency selection
    CRYPTO_CURRENCIES = (
        ('bitcoin', 'Bitcoin'),
        ('ethereum', 'Ethereum'),
        ('litecoin', 'Litecoin'),
        ('ripple', 'Ripple'),
        ('cardano', 'Cardano'),
        ('polkadot', 'Polkadot'),
        ('binancecoin', 'Binance Coin'),
        ('dogecoin', 'Dogecoin'),
        ('solana', 'Solana'),
        ('avalanche', 'Avalanche'),
    )

    crypto_currency = forms.ChoiceField(
        choices=CRYPTO_CURRENCIES,
        widget=forms.Select,
        label="Cryptocurrency"
    )

    network = forms.ChoiceField(
        choices=[],  # This will be populated dynamically based on the selected cryptocurrency
        widget=forms.Select,
        label="Network"
    )

    deposit_address = forms.CharField(
        max_length=255,
        label="Deposit Address",
        widget=forms.TextInput(attrs={'readonly': 'readonly'})  # Read-only until confirmed
    )

    memo_tag = forms.CharField(
        max_length=255,
        required=False,
        label="Memo/Tag (if required)"
    )

    transaction_fee = forms.DecimalField(
        max_digits=20,
        decimal_places=8,
        label="Transaction Fee",
        required=False,
        initial=0.0,
        disabled=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        crypto_currency = self.data.get('crypto_currency') or None
        if crypto_currency:
            self.fields['network'].choices = self.get_network_choices(crypto_currency)
        else:
            self.fields['network'].choices = []

    def get_network_choices(self, crypto_currency):
        """Fetch network options based on selected cryptocurrency."""
        network_choices = self.fetch_network_data(crypto_currency)
        return [(network, network) for network in network_choices]

    def fetch_network_data(self, crypto_currency):
        """Fetch supported networks for the selected cryptocurrency using KuCoin API."""
        url = f"https://api.kucoin.com/api/v1/currencies/{crypto_currency.upper()}"
        try:
            response = requests.get(url)
            data = response.json()

            if response.status_code == 200 and data.get("code") == "200000":
                networks = data.get("data", {}).get("chains", [])
                return [network["chainName"] for network in networks]
            else:
                return []
        except Exception as e:
            return []


class PasswordResetForm(forms.Form):
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email address',
            'class': 'form-control',
        })
    )


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactModel
        fields = ['name', 'email', 'message']  # Removed 'subject'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your Message'}),
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['is_2fa_enabled']

    referral_link = forms.URLField(widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        user = kwargs.get('instance').user if kwargs.get('instance') else None
        super(ProfileForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['referral_link'].initial = user.profile.referral_link
            


class UpdateProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class TradeForm(forms.ModelForm):
    class Meta:
        model = Trade
        fields = ['token', 'amount', 'order_type']

    token = forms.ChoiceField(
        choices=[('BTC', 'Bitcoin (BTC)'), ('ETH', 'Ethereum (ETH)'), ('USDT', 'Tether (USDT)')],
        label='Select Token', widget=forms.Select(attrs={'class': 'form-control'})
    )
    amount = forms.DecimalField(
        max_digits=20, decimal_places=8, label='Amount to Trade',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.00000001'})
    )
    order_type = forms.ChoiceField(
        choices=[('BUY', 'Buy'), ('SELL', 'Sell')],
        label='Order Type', widget=forms.Select(attrs={'class': 'form-control'})
    )


class CryptocurrencyForm(forms.ModelForm):
    class Meta:
        model = Cryptocurrency
        fields = ['name', 'symbol', 'price']


class PortfolioForm(forms.ModelForm):
    class Meta:
        model = Portfolio
        fields = ['user', 'asset_name', 'total_invested', 'total_units', 'current_value']  # Exclude 'total_value' since it is calculated

    asset_name = forms.CharField(
        max_length=100, required=True, label='Asset Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter asset name (e.g., Bitcoin)'})
    )
    total_invested = forms.DecimalField(
        max_digits=20, decimal_places=2, required=True, label='Total Invested',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total money invested in USD'})
    )
    total_units = forms.DecimalField(
        max_digits=20, decimal_places=8, required=True, label='Total Units',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Total units of the asset'})
    )
    current_value = forms.DecimalField(
        max_digits=20, decimal_places=2, required=True, label='Current Value (per unit)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Current value of 1 unit in USD'})
    )

    def clean(self):
        cleaned_data = super().clean()
        total_units = cleaned_data.get('total_units')
        current_value = cleaned_data.get('current_value')

        # Automatically calculate the total_value before saving
        if total_units is not None and current_value is not None:
            cleaned_data['total_value'] = total_units * current_value

        return cleaned_data