from collections import defaultdict
from pprint import pprint

from tinkoff.invest.services import Services

from logger.logger import get_logger

from tinkoff.invest import Client, InstrumentIdType

log = get_logger()


class Model:
    def __init__(self, account_id, token):
        self.account_id = account_id
        self.token = token

        self.currencies = defaultdict(str)

        with Client(token) as client:
            currencies = client.instruments.currencies()
            for currency in currencies.instruments:
                price = client.market_data.get_last_prices(figi=[currency.figi])
                price = price.last_prices[0].price
                price = price.units + price.nano / 10 ** 9
                self.currencies[currency.iso_currency_name] = price

    def get_portfolio_data(self):
        try:
            res = {"bond": {"total_price": 0,
                            "regular_price": 0,
                            "floater_price": 0,
                            "total_amount": 0,
                            "regular_amount": 0,
                            "floater_amount": 0,
                            "regular_positions": [],
                            "floater_positions": [],
                            "sector": defaultdict(int)
                            },
                   "share": {"total_price": 0,
                             "total_amount": 0,
                             "positions": [],
                             "sector": defaultdict(int)
                             },
                   "etf": {"total_price": 0,
                           "total_amount": 0,
                           "positions": [],
                           "focus_type": defaultdict(int)}
                   }
            whole_price = 0

            with Client(self.token) as client:
                log.info("Получение данных по портфелю")

                positions = client.operations.get_positions(account_id=self.account_id)
                for money in positions.money:
                    cur_price = money.units + money.nano / 10 ** 9
                    if money.currency != 'rub':
                        cur_price *= self.currencies.get(money.currency, 1)
                    whole_price += cur_price

                for position in positions.securities:
                    if position.instrument_type == "bond":  # облигация
                        cnt = position.balance
                        info, price = self._get_instrument_info(client, position.figi, position.instrument_type)
                        info = info.instrument

                        price = price.last_prices[0].price
                        price = price.units * 10 + price.nano / 10 ** 8
                        res["bond"]["total_amount"] += cnt
                        res["bond"]["total_price"] += price * cnt

                        if info.floating_coupon_flag:
                            res["bond"]["floater_amount"] += cnt
                            res["bond"]["floater_price"] += price * cnt
                            res["bond"]["floater_positions"].append({"name": info.name,
                                                                     "coupon_per": info.coupon_quantity_per_year,
                                                                     "one_price": price,
                                                                     "count": cnt,
                                                                     "whole_price": cnt * price,
                                                                     "country": info.country_of_risk_name,
                                                                     "nominal": info.initial_nominal.units +
                                                                                info.initial_nominal.nano / 10 ** 9})
                        else:
                            res["bond"]["regular_amount"] += cnt
                            res["bond"]["regular_price"] += price * cnt
                            res["bond"]["regular_positions"].append({"name": info.name,
                                                                     "coupon_per": info.coupon_quantity_per_year,
                                                                     "one_price": price,
                                                                     "count": cnt,
                                                                     "whole_price": cnt * price,
                                                                     "country": info.country_of_risk_name,
                                                                     "nominal": info.initial_nominal.units +
                                                                                info.initial_nominal.nano / 10 ** 9})
                        res["bond"]["sector"][info.sector] += price * cnt
                        whole_price += price * cnt
                    elif position.instrument_type == "share":  # акция
                        cnt = position.balance
                        info, price = self._get_instrument_info(client, position.figi, position.instrument_type)
                        info = info.instrument
                        price = price.last_prices[0].price
                        price = price.units + price.nano / 10 ** 9

                        res["share"]["total_price"] += price * cnt
                        res["share"]["total_amount"] += cnt
                        res["share"]["positions"].append({"name": info.name,
                                                          "country": info.country_of_risk_name,
                                                          "one_price": price,
                                                          "count": cnt,
                                                          "whole_price": cnt * price})
                        res["share"]["sector"][info.sector] += price * cnt
                        whole_price += price * cnt
                    elif position.instrument_type == "etf":  # фонд
                        cnt = position.balance
                        info, price = self._get_instrument_info(client, position.figi, position.instrument_type)
                        info = info.instrument
                        price = price.last_prices[0].price
                        price = price.units + price.nano / 10 ** 9

                        res["etf"]["total_price"] += price * cnt
                        res["etf"]["total_amount"] += cnt
                        res["etf"]["positions"].append({"name": info.name,
                                                        "one_price": price,
                                                        "count": cnt,
                                                        "whole_price": cnt * price,
                                                        "focus_type": info.focus_type})
                        res["etf"]["focus_type"][info.focus_type] += price * cnt
                        whole_price += price * cnt
                    else:
                        instrument_type = position.instrument_type
                        cnt = position.balance
                        info, price = self._get_instrument_info(client, position.figi, instrument_type)
                        info = info.instrument
                        price = price.last_prices[0].price
                        price = price.units + price.nano / 10 ** 9

                        res.setdefault(instrument_type, {"total_price": 0, "total_amount": 0, "positions": []})

                        res[instrument_type]["total_price"] += price * cnt
                        res[instrument_type]["total_amount"] += cnt
                        res[instrument_type]["positions"].append({"name": info.name,
                                                                  "one_price": price,
                                                                  "count": cnt,
                                                                  "whole_price": cnt * price})
                        whole_price += price * cnt
                res["whole_price"] = whole_price

                log.info("Данные успешно получены")
                return res
        except Exception as e:
            log.error("Error while getting portfolio data", str(e))
            return {}

    def _get_instrument_info(self, client: Services, figi: str, instrument_type: str):
        try:
            if instrument_type == "bond":
                info = client.instruments.bond_by(id_type=InstrumentIdType(1), id=figi)
            elif instrument_type == "share":
                info = client.instruments.share_by(id_type=InstrumentIdType(1), id=figi)
            elif instrument_type == 'etf':
                info = client.instruments.etf_by(id_type=InstrumentIdType(1), id=figi)
            else:
                info = client.instruments.get_instrument_by(id_type=InstrumentIdType(1), id=figi)
            last_price = client.market_data.get_last_prices(figi=[figi])
            return info, last_price
        except Exception as e:
            log.error("Error while getting instrument info %s, %s", figi, str(e))
            return None, None
