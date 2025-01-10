from celery import shared_task
from .models import Trade
from .views import execute_trade

@shared_task
def process_trade(trade_id):
    trade = Trade.objects.get(id=trade_id)
    execute_trade(trade)
