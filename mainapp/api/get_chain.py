from django.http import JsonResponse

def get_chains(request):
    coin = request.GET.get('coin')
    if not coin:
        return JsonResponse({'error': 'Coin not provided'}, status=400)

    # Replace this with actual API logic
    chains_map = {
        'BTC': ['Bitcoin Mainnet'],
        'ETH': ['Ethereum Mainnet', 'Binance Smart Chain'],
        'USDT': ['Ethereum Mainnet', 'Tron', 'Binance Smart Chain']
    }
    chains = chains_map.get(coin, [])
    return JsonResponse(chains, safe=False)
