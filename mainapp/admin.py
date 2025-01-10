from django.contrib import admin
from .models import Profile, Wallet, Service, ContactModel, Deposit, Transaction, Withdraw, Trade, BlockchainTransaction, Profile, Referral, Cryptocurrency, Portfolio
from django.utils.html import format_html
from django.conf import settings
import ccxt
# Logger for error handling and debug information
import logging
from kucoin.client import Client
import os

# ================================
# Transaction Admin
# ================================

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon', 'is_active')  # Display these fields in the admin list view
    list_filter = ('is_active',)  # Filter by active status
    search_fields = ('title', 'description')  # Add search functionality
    

class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'referral_code', 'is_2fa_enabled', 'is_phone_verified']



# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Fetch API credentials from environment variables
api_key = os.getenv('KUCOIN_API_KEY')  # Set your KuCoin API Key
api_secret = os.getenv('KUCOIN_API_SECRET')  # Set your KuCoin API Secret
passphrase = os.getenv('KUCOIN_PASSPHRASE')  # Set your KuCoin API Passphrase

# Initialize the KuCoin client
try:
    exchange = Client(api_key=api_key, api_secret=api_secret, passphrase=passphrase)
    logger.info("KuCoin Client successfully initialized.")
except Exception as e:
    logger.error(f"Error initializing KuCoin client: {str(e)}")


class DepositAdmin(admin.ModelAdmin):
    # Fields to display in the admin interface
    list_display = (
        'user', 'amount', 'crypto_currency', 'get_transaction_type', 'status',
        'deposit_address', 'get_transaction_id', 'timestamp', 'display_account_type',
        'display_asset_balance', 'fetch_current_price'
    )

    # Searchable fields in the admin interface
    search_fields = ('user__username', 'crypto_currency', 'deposit_address', 'network', 'transaction_id')

    # Filters for narrowing results in the admin interface
    list_filter = ('status', 'crypto_currency', 'network', 'account_type')  # Ensure 'account_type' is a valid field or method

    # Ordering for list view
    ordering = ('-timestamp',)

    # ForeignKey dropdown size optimization
    raw_id_fields = ('user',)

    # Custom actions in the admin interface
    actions = ['mark_completed', 'mark_failed']

    # Custom method for transaction type
    def get_transaction_type(self, obj):
        return obj.transaction_type
    get_transaction_type.short_description = "Transaction Type"

    # Custom method for transaction ID
    def get_transaction_id(self, obj):
        return obj.transaction_id
    get_transaction_id.short_description = "Transaction ID"

    # Custom display method for account type
    def display_account_type(self, obj):
        return obj.account_type  # Ensure this field exists in the Deposit model
    display_account_type.short_description = "Account Type"

    # Custom display method for asset balance using KuCoin API
    def display_asset_balance(self, obj):
        try:
            balance = exchange.fetch_balance()
            asset_balance = balance['total'].get(obj.crypto_currency, 0.0)
            return format_html(f"{asset_balance:.8f} {obj.crypto_currency}")
        except Exception as e:
            logger.error(f"Error fetching balance for {obj.crypto_currency}: {e}")
            return "Error"
    display_asset_balance.short_description = "Asset Balance"

    # Fetch current price using KuCoin API
    def fetch_current_price(self, obj):
        try:
            ticker = exchange.fetch_ticker(f'{obj.crypto_currency}/USDT')
            price = ticker.get('last', 0.0)
            return format_html(f"${price:.2f}")
        except Exception as e:
            logger.error(f"Error fetching current price for {obj.crypto_currency}: {e}")
            return "Error"
    fetch_current_price.short_description = "Current Price (USD)"

    # Admin actions to mark deposits as completed
    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f"{updated} deposit(s) marked as completed.")
    mark_completed.short_description = "Mark selected deposits as completed"

    # Admin actions to mark deposits as failed
    def mark_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f"{updated} deposit(s) marked as failed.")
    mark_failed.short_description = "Mark selected deposits as failed"



class TransactionAdmin(admin.ModelAdmin):
    # List display to show in the admin interface
    list_display = ('user', 'amount', 'currency', 'transaction_type', 'transaction_fee', 'status', 'timestamp', 'memo_tag', 'reference_code', 'external_transaction_id')
    
    # Search functionality for admin
    search_fields = ('user__username', 'currency', 'transaction_type', 'reference_code', 'external_transaction_id')
    
    # Filters to filter by specific fields in the admin interface
    list_filter = ('transaction_type', 'status', 'currency')
    
    # Displaying only the relevant fields on the admin change page
    fields = ('user', 'amount', 'currency', 'transaction_type', 'transaction_fee', 'status', 'timestamp', 'memo_tag', 'reference_code', 'external_transaction_id')
    
    # Enable the ability to filter records by 'status' and 'transaction_type'
    ordering = ('-timestamp',)
    
    # You can also use raw_id_fields to reduce the dropdowns' size when working with FK fields
    raw_id_fields = ('user',)
    
    # Custom actions in the admin interface (optional)
    actions = ['mark_completed', 'mark_failed']

    def mark_completed(self, request, queryset):
        queryset.update(status='completed')
    mark_completed.short_description = "Mark selected transactions as completed"
    
    def mark_failed(self, request, queryset):
        queryset.update(status='failed')
    mark_failed.short_description = "Mark selected transactions as failed"



# ================================
# Withdraw Admin
# ================================
class WithdrawAdmin(admin.ModelAdmin):
    list_display = ['user', 'currency', 'amount', 'transaction_fee', 'status', 'timestamp']
    readonly_fields = ['transaction_fee', 'timestamp']
    search_fields = ['user__username', 'currency']
    list_filter = ['status', 'currency', 'timestamp']
    ordering = ['-timestamp']  # Order by most recent transactions first

    def transaction_fee(self, obj):
        """
        Calculate the transaction fee for the withdrawal.
        Assumes the fee is 2% of the amount.
        """
        return round(obj.amount * 0.02, 2) if obj.amount else 0.00

    transaction_fee.short_description = 'Transaction Fee'  # Custom column name in the admin panel


# ================================
# Wallet Admin
# ================================
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance_btc', 'balance_eth', 'balance_usd')  # Correct fields for list_display
    list_filter = ('user',)  # Adding a valid field for list_filter
    search_fields = ('user__username',)  # Enable search by the username of the associated user
    readonly_fields = ('balance_btc', 'balance_eth', 'balance_usd')  # Prevent balances from being editable

    def has_add_permission(self, request):
        """Prevent creating new wallets directly from the admin interface."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting wallets from the admin interface."""
        return False
    
    
# ================================
# Trade Admin
# ================================
class TradeAdmin(admin.ModelAdmin):
    list_display = ('user', 'order_type', 'token', 'amount', 'status', 'date_created')
    search_fields = ('user__username', 'token')
    list_filter = ('order_type', 'status', 'date_created')


# ================================
# BlockchainTransaction Admin
# ================================
class BlockchainTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'amount', 'status', 'transaction_hash')
    search_fields = ('user__username', 'token')
    list_filter = ('status',)


# ================================
# Profile Admin
# ================================
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_2fa_enabled', 'referral_link')
    search_fields = ('user__username', 'user__email')

    def referral_link(self, obj):
        return format_html('<a href="{0}" target="_blank">{0}</a>', obj.get_referral_link())
    referral_link.short_description = 'Referral Link'  # Optional: Customize the column title


# ================================
# Portfolio Admin
# ================================
class PortfolioAdmin(admin.ModelAdmin):
    # Display relevant fields in the admin list view
    list_display = (
        'user',                # User associated with the portfolio
        'asset_name',          # Name of the asset
        'total_invested',      # Total invested amount
        'total_units',         # Total units
        'current_value',       # Current value of the asset
        'portfolio_value',     # Total value of the portfolio
        'created',             # Date when the portfolio was created
        'last_updated',        # Last time the portfolio was updated
    )

    # Add more meaningful filters to manage portfolio items effectively
    list_filter = ('user', 'asset_name', 'created', 'last_updated')

    # Enable searching by asset name and username
    search_fields = ('user__username', 'asset_name')

    # Make the fields read-only or editable in the admin interface
    readonly_fields = ('created', 'last_updated')  # These fields should not be editable

    # Optional: Add ordering for better admin view
    ordering = ('-last_updated',)  # Orders by the most recent updates

    # Custom actions for admin panel
    actions = ['clear_investment']

    def clear_investment(self, request, queryset):
        """
        Custom action to reset the investment fields for selected portfolios.
        """
        for portfolio in queryset:
            portfolio.total_invested = 0
            portfolio.total_units = 0
            portfolio.current_value = 0
            portfolio.save()
        self.message_user(request, "Selected portfolios have been reset.")
    
    clear_investment.short_description = "Reset total investment and units for selected portfolios"


@admin.register(ContactModel)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')
    search_fields = ('name', 'email')
    list_filter = ('created_at',)


class ReferralAdmin(admin.ModelAdmin):
    list_display = ('user', 'referrer', 'get_referral_link')
    search_fields = ('user__username', 'referrer__username')

    def get_referral_link(self, obj):
        return f"{settings.SITE_URL}/referral/{obj.user.profile.referral_code}"

    get_referral_link.short_description = 'Referral Link'


# ================================
# Register models with their admin classes
# ================================
admin.site.register(Referral, ReferralAdmin)  # No custom admin required
admin.site.register(Cryptocurrency)  # No custom admin required
admin.site.register(Portfolio, PortfolioAdmin)  # Register with PortfolioAdmin
admin.site.register(Withdraw, WithdrawAdmin)  # Custom admin added
admin.site.register(Deposit, DepositAdmin)  # Custom admin added
admin.site.register(Trade, TradeAdmin)  # Custom admin added
admin.site.register(BlockchainTransaction, BlockchainTransactionAdmin)  # Custom admin added
admin.site.register(Transaction, TransactionAdmin)  # Custom admin added
admin.site.register(Wallet, WalletAdmin)
admin.site.register(Profile, ProfileAdmin)