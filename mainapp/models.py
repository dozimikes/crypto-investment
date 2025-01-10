from django.contrib.auth.models import User, AbstractUser, Group, Permission
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import now
from django.utils.crypto import get_random_string
from django.conf import settings
from django import forms
import uuid
import random
import string
import ccxt
import logging
from decimal import Decimal
import requests


# Override the default User model to make the email unique
User._meta.get_field('email')._unique = True


# Contact Model
class ContactModel(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200, null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.subject}"


# Twilio Message Model
class TwilioMessage(models.Model):
    MESSAGE_STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('undelivered', 'Undelivered'),
    ]

    to_phone_number = models.CharField(max_length=15)
    from_phone_number = models.CharField(max_length=15)
    message_body = models.TextField()
    twilio_message_sid = models.CharField(max_length=255, unique=True)
    verification_sid = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=12, choices=MESSAGE_STATUS_CHOICES, default='queued')
    date_sent = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Message to {self.to_phone_number} - Status: {self.status}"


# Service Model
class Service(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, default="fas fa-chart-line")
    link = models.URLField(max_length=200, default="#")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


# Profile Model
def generate_referral_code():
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    while Profile.objects.filter(referral_code=code).exists():
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return code


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_2fa_enabled = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)
    referral_code = models.CharField(max_length=8, unique=True, default=generate_referral_code, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')

    def __str__(self):
        return self.user.username

    def get_referral_link(self):
        return f"{settings.SITE_URL}/referral/{self.referral_code}"    
    

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()


# Referal Model
class Referral(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals')

    def __str__(self):
        return f'{self.user.username} was referred by {self.referrer.username}'


# Cryptocurrency Model
class Cryptocurrency(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cryptocurrencies', null=True)
    id_from_api = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('user', 'name')

    def __str__(self):
        return f'{self.name} ({self.symbol})'

# Portfolio Model - updated to include missing fields
class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolios')
    asset_name = models.CharField(max_length=100, default='default_asset_name')
    total_invested = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    total_units = models.DecimalField(max_digits=20, decimal_places=8, default=0.00)
    current_value = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    created = models.DateTimeField(auto_now_add=True)  # Automatically set on creation
    last_updated = models.DateTimeField(auto_now=True)  # Automatically updated on save

    def save(self, *args, **kwargs):
        self.total_value = self.total_units * self.current_value
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} - Portfolio: {self.asset_name}'

    @property
    def portfolio_value(self):
        return self.calculate_total_value()

    def calculate_total_value(self):
        return self.total_units * self.current_value
    

class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance_btc = models.DecimalField(max_digits=20, decimal_places=8, default=0.0)
    balance_eth = models.DecimalField(max_digits=20, decimal_places=8, default=0.0)
    balance_usd = models.DecimalField(max_digits=20, decimal_places=2, default=0.0)
    fiat_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.0)  # New field

    def get_balance(self, currency):
        """Returns the balance for the specified currency (BTC, ETH, USD)."""
        currency = currency.lower()
        if currency == 'btc':
            return self.balance_btc
        elif currency == 'eth':
            return self.balance_eth
        elif currency == 'usd':
            return self.balance_usd
        return 0.0

    def debit_balance(self, currency, amount):
        """Deducts the specified amount from the user's balance for the given currency."""
        currency = currency.lower()
        if currency == 'btc':
            self.balance_btc -= amount
        elif currency == 'eth':
            self.balance_eth -= amount
        elif currency == 'usd':
            self.balance_usd -= amount
        self.save()

    def credit_balance(self, currency, amount):
        """Adds the specified amount to the user's balance for the given currency."""
        currency = currency.lower()
        if currency == 'btc':
            self.balance_btc += amount
        elif currency == 'eth':
            self.balance_eth += amount
        elif currency == 'usd':
            self.balance_usd += amount
        self.save()

    def calculate_withdrawal_fee(self, amount, currency):
        """Calculates the 0.6% withdrawal fee for the given currency and amount."""
        # Fee is 0.6% (0.006)
        withdrawal_fee_percentage = 0.006
        fee = amount * withdrawal_fee_percentage
        return fee

    def save(self, *args, **kwargs):
        # Automatically calculate fiat_balance based on BTC to USD rate
        # Ideally, fetch the current BTC-to-USD exchange rate from an API (this is just an example rate)
        BTC_TO_USD_RATE = 20000  # Example rate; replace with dynamic rate if possible
        self.fiat_balance = self.balance_btc * BTC_TO_USD_RATE  # Calculate fiat balance in USD
        super().save(*args, **kwargs)



logger = logging.getLogger(__name__)


class CryptoNetwork(models.Model):
    coin = models.CharField(max_length=100)  # e.g., Bitcoin, Ethereum
    network_name = models.CharField(max_length=100)  # e.g., Arbitrum, Optimism
    chain_id = models.IntegerField(null=True, blank=True)  # Optional Chain ID for the network
    description = models.TextField(null=True, blank=True)  # Optional description of the network

    def __str__(self):
        return f"{self.coin} - {self.network_name}"


class Withdraw(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=20, choices=[('BTC', 'Bitcoin'), ('ETH', 'Ethereum')])
    withdrawal_address = models.CharField(max_length=255)
    fee = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0.0'))  # Transaction fee
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )
    tx_hash = models.CharField(max_length=255, null=True, blank=True)  # Transaction hash for crypto withdrawals
    timestamp = models.DateTimeField(default=now)
    network = models.ForeignKey(CryptoNetwork, on_delete=models.SET_NULL, null=True, blank=True, related_name='withdrawals')

    def calculate_transaction_fee(self):
        """
        Calculate a 0.8% transaction fee.
        """
        return self.amount * Decimal('0.008')

    def send_fee_to_kucoin(self):
        """
        Send the transaction fee to the designated KuCoin account.
        """
        fee_address = settings.KUCOIN_FEE_ADDRESS
        try:
            # Use KuCoin API to send the fee
            url = "https://api.kucoin.com/api/v1/withdrawals"
            headers = self.get_kucoin_headers()
            payload = {
                "currency": self.currency,
                "address": fee_address,
                "amount": str(self.fee),
                "network": self.network.network_name,
            }
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()

            if response.status_code == 200 and response_data.get("code") == "200000":
                return True
            else:
                logger.error(f"Error sending fee: {response_data}")
                return False
        except Exception as e:
            logger.error(f"Error sending fee: {e}")
            return False

    def save(self, *args, **kwargs):
        """
        Override save to calculate the fee and send it to the designated KuCoin account.
        """
        self.fee = self.calculate_transaction_fee()
        super().save(*args, **kwargs)
        if self.status == 'completed':
            self.send_fee_to_kucoin()

    def __str__(self):
        return f"Withdraw of {self.amount} {self.currency} by {self.user.username} - {self.status}"

    @staticmethod
    def get_kucoin_headers():
        """
        Generate headers for KuCoin API requests.
        """
        api_key = settings.KUCOIN_API_KEY
        api_secret = settings.KUCOIN_API_SECRET
        api_passphrase = settings.KUCOIN_API_PASSPHRASE
        timestamp = str(int(time.time() * 1000))

        str_to_sign = f"{timestamp}GET/api/v1/withdrawals"
        signature = base64.b64encode(
            hmac.new(api_secret.encode(), str_to_sign.encode(), sha256).digest()
        )

        return {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature.decode(),
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": api_passphrase,
            "KC-API-KEY-VERSION": "2"
        }


class Deposit(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    crypto_currency = models.CharField(max_length=10)
    network = models.CharField(max_length=50)
    transaction_fee = models.DecimalField(max_digits=10, decimal_places=8, default=Decimal('0.0'))
    net_amount = models.DecimalField(max_digits=20, decimal_places=8, default=Decimal('0.0'))
    status = models.CharField(
        max_length=50,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')],
        default='pending'
    )
    deposit_address = models.CharField(max_length=255)
    memo_tag = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Add the account_type field
    account_type = models.CharField(max_length=50, choices=[('personal', 'Personal'), ('business', 'Business')])

    def calculate_transaction_fee(self):
        """
        Calculate a 0.8% transaction fee.
        """
        return self.amount * Decimal('0.008')

    def save(self, *args, **kwargs):
        """
        Override save to calculate the transaction fee and net amount.
        """
        self.transaction_fee = self.calculate_transaction_fee()
        self.net_amount = self.amount - self.transaction_fee
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Deposit of {self.amount} {self.crypto_currency} by {self.user.username} - {self.status}"

    class Meta:
        verbose_name = "Deposit"
        verbose_name_plural = "Deposits"
        ordering = ['-timestamp']



    

# FiatDeposit Model
class FiatDeposit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency = models.CharField(max_length=20, default='USD')
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending')
    transaction_reference = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Fiat Deposit of {self.amount} {self.currency} by {self.user.username} - {self.status}"

# Trade Model
class Trade(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    ORDER_TYPE_CHOICES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=10, null=True, blank=True)
    order_type = models.CharField(max_length=4, choices=ORDER_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    current_balance = models.DecimalField(max_digits=20, decimal_places=8, default=0.0)
    total_profit = models.DecimalField(max_digits=20, decimal_places=8, default=0.0)
    date_created = models.DateTimeField(auto_now_add=True)
    last_profit_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} - {self.token} - {self.order_type}'

# BlockchainTransaction Model
class BlockchainTransaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=20, null=True, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    wallet_address = models.CharField(max_length=255)
    transaction_hash = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, default='PENDING')

    def __str__(self):
        return f"Transaction {self.id} - {self.token} - {self.status}"

# Transaction Model
class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('withdraw', 'Withdraw'),
        ('transfer', 'Transfer'),
    ]

    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    currency = models.CharField(max_length=20)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    transaction_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.6)
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES, default='pending')
    memo_tag = models.CharField(max_length=255, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    reference_code = models.CharField(max_length=50, null=True, blank=True, unique=True)
    external_transaction_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.amount} {self.currency} - {self.transaction_type} ({self.status})"
  
    

# MarketData Model
class MarketData(models.Model):
    symbol = models.CharField(max_length=10, default="DEFAULT_SYMBOL")
    price = models.DecimalField(max_digits=20, decimal_places=8)
    high = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    low = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    volume = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.symbol} - {self.price} at {self.timestamp}"
    

# InvestmentPlan Model
class InvestmentPlan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10, null=True, blank=True)
    amount_per_interval = models.DecimalField(max_digits=20, decimal_places=8)
    frequency = models.CharField(max_length=10, null=True, blank=True)
    next_purchase = models.DateTimeField()

    def __str__(self):
        return f"{self.user.username} - {self.symbol} - {self.amount_per_interval}"

# Staking Model
class Staking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10, null=True, blank=True)
    amount_staked = models.DecimalField(max_digits=20, decimal_places=8)
    staking_duration = models.IntegerField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.user.username} - Staked {self.amount_staked} {self.symbol}"


class MetaTraderAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="metatrader_account")
    account_number = models.CharField(max_length=50)
    broker = models.CharField(max_length=100)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.0)
    status = models.CharField(max_length=20, choices=[('connected', 'Connected'), ('disconnected', 'Disconnected')], default='disconnected')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s MetaTrader Account - {self.status}"


class CustomUser(AbstractUser):
    # Add your custom fields if any
    email_confirmed = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    phone_verification_code = models.CharField(max_length=6, null=True, blank=True)

    groups = models.ManyToManyField(
        Group,
        related_name="customuser_set",  # Add unique related_name
        blank=True,
        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_permissions",  # Add unique related_name
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )