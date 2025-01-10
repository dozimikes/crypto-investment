# mainapp/api_views.py
import requests
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Cryptocurrency, Portfolio



def get_top_10_crypto(request):
    # URL to get the top 10 cryptocurrencies by market cap
    top_10_crypto_url_global = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=USD&order=market_cap_desc&per_page=10&page=1&sparkline=true'
    top_10_crypto_data_global = requests.get(top_10_crypto_url_global).json()
    
    # Return the data as a JSON response
    return JsonResponse(top_10_crypto_data_global, safe=False)  # safe=False allows non-dict objects to be serialized

# mainapp/api_views.py


@login_required
def get_user_portfolio(request):
    # Assuming the user is authenticated, get their portfolio and cryptocurrencies
    user = request.user
    portfolio = Portfolio.objects.filter(user=user).first()
    cryptocurrencies = Cryptocurrency.objects.filter(user=user)
    
    # Prepare data to send in the response
    portfolio_data = {
        'total_value': portfolio.total_value if portfolio else 0,
        'cryptocurrencies': [
            {
                'name': crypto.name,
                'quantity': crypto.quantity,
                'current_price': crypto.current_price,
                'total_value': crypto.quantity * crypto.current_price
            }
            for crypto in cryptocurrencies
        ]
    }

    # Return portfolio data as JSON
    return JsonResponse(portfolio_data)


def search_crypto(request):
    search_query = request.GET.get('query', '')  # Get search query from URL parameters
    if search_query:
        api_url = f'https://api.coingecko.com/api/v3/search?query={search_query}'
        response = requests.get(api_url)
        search_results = response.json()
        return JsonResponse(search_results, safe=False)
    else:
        return JsonResponse({'error': 'No search query provided'}, status=400)