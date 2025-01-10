from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views, api_views
from .views import (
    crypto_chart, 
    deposit_view, 
    connect_wallet_view, 
    admin_transaction_view, 
    ProfitLossAnalysisView, 
    TaxReportingView, 
    PerformanceMetricsView,
    login_view,
    signup_view,
    confirm_email_view,
    logout_view,
    setup,
    terms_conditions_view, 
    error_page,
    get_binance_data,
    fetch_networks,
    get_networks,
    fetch_coins,
    fetch_deposit_details,
    get_kucoin_data
)



urlpatterns = [
    # Landing Page
    path('', views.index, name='index'),  # Landing page URL

    # User Authentication
    path('logout/', logout_view, name='logout_view'),
    path('login/', views.login_view, name='login'),  # Login URL
    path('signup/', views.signup_view, name='signup'),  # Signup URL
    path('verify-phone/', views.signup_view, name='verify_phone'),  # Verify phone URL
    path('terms/', terms_conditions_view, name='terms_conditions'),
    path('crypto_chart/', crypto_chart, name='crypto_chart'),
    path('account/confirm-email/<uidb64>/<token>/', confirm_email_view, name='confirm_email'),
    path('signup/<str:referral_code>/', views.signup_with_referrer_view, name='signup_with_referrer_view'),

    # Dashboard and Profile
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('setup/', views.setup, name='setup'),
    path('register/', views.register, name='register'),  # Ensure this matches your view name

    # Static Pages
    path('about/', views.about, name='about'),
    path('services/', views.services_view, name='services'),
    path('contact/', views.contact_view, name='contact'),

    # Wallet and Portfolio
    path('wallet/', views.wallet, name='wallet'),
    path('wallet/update/', views.update_wallet, name='update_wallet'),
    path('get-binance-data/', get_binance_data, name='get_binance_data'),
    path('error/', views.error_page, name='error_page'),
    path('portfolio/', views.portfolio_view, name='portfolio'),
    path('select-plan/', views.select_plan, name='select_plan'),
    path('crypto_chart/', crypto_chart, name='crypto_chart'),

    # CRUD Operations
    path('search/', views.search_view, name='search'),
    path('deposit/', deposit_view, name='deposit'),
    path('deposit/create/', views.deposit_cancel, name='deposit_create'),
    path('deposit/success/', views.deposit_success, name='deposit_success'),
    path('fetch_deposit_details/<str:coin>/<str:network>/', views.fetch_deposit_details, name='fetch_deposit_details'), 
    path('fetch_coins/', views.fetch_coins, name='fetch_coins'),
    path('fetch_networks/<str:coin>/', views.fetch_networks, name='fetch_networks'),path('withdraw/', views.withdraw, name='withdraw'),
    path('get-kucoin-data/', views.get_kucoin_data, name='get_kucoin_data'),
    path('get-kucoin-data/<str:coin_symbol>/', views.get_kucoin_data, name='get_kucoin_data_with_symbol'),
    path('transactions/', views.transaction_history_view, name='transaction_history'),
    path('initiate-trade/', views.initiate_trade, name='initiate_trade'),
    path('create/', views.create_portfolio, name='create_portfolio'),
    path('delete/<int:pk>/', views.delete_from_portfolio_view, name='delete_from_portfolio'),

    # Trade Management
    path('trade/<str:symbol>/<str:transaction_type>/', views.execute_trade, name='execute_trade'),
    path('trade_status/<int:trade_id>/', views.trade_status, name='trade_status'),

    # Investment and Staking
    path('investment-plan/<str:symbol>/<str:amount>/<str:frequency>/', views.create_investment_plan, name='create_investment_plan'),
    path('stake/<str:symbol>/<str:amount>/<int:staking_duration>/', views.stake_crypto, name='stake_crypto'),

    # Wallet Connection
    path('connect-wallet/', connect_wallet_view, name='connect_wallet'),
    path('connect_to_mt5/', views.connect_to_mt5, name='connect_to_mt5'),
    path('get_account_info/', views.get_account_info, name='get_account_info'),
    path('mt5_chart/', views.get_mt5_chart, name='get_mt5_chart'),
    path('place_trade/', views.place_trade, name='place_trade'),

    # Analytics and Reporting
    path('analytics/profit-loss/', ProfitLossAnalysisView.as_view(), name='profit_loss_analysis'),
    path('analytics/tax-reporting/', TaxReportingView.as_view(), name='tax_reporting'),
    path('analytics/performance-metrics/', PerformanceMetricsView.as_view(), name='performance_metrics'),

    # Password Reset
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='reset/password_reset.html'), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name='reset/password_reset_done.html'), name='password_reset_done'),
    path('password_reset_confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='reset/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password_reset_complete/', auth_views.PasswordResetCompleteView.as_view(template_name='reset/password_reset_complete.html'), name='password_reset_complete'),

    # Additional Features
    path('top-10-crypto/', api_views.get_top_10_crypto, name='top_10_crypto'),
    path('add_to_portfolio/', views.add_to_portfolio_view, name='add_to_portfolio'),
    path('delete_from_portfolio/<int:pk>/', views.delete_from_portfolio_view, name='delete_from_portfolio'),
]
