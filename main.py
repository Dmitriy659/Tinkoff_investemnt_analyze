from datetime import timedelta

from config.config import TOKEN

from tinkoff.invest import CandleInterval, Client
from tinkoff.invest.utils import now


with Client(TOKEN) as client:
    account_id = client.users.get_accounts().accounts[0].id
    shares = client.operations.get_portfolio(account_id=account_id)
    print(shares)
