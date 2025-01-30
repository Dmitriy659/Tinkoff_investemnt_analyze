import time
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
                    if money.currency != "rub":
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
                time.sleep(0.08)
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
            elif instrument_type == "etf":
                info = client.instruments.etf_by(id_type=InstrumentIdType(1), id=figi)
            else:
                info = client.instruments.get_instrument_by(id_type=InstrumentIdType(1), id=figi)
            last_price = client.market_data.get_last_prices(figi=[figi])
            return info, last_price
        except Exception as e:
            log.error("Error while getting instrument info %s, %s", figi, str(e))
            return None, None

    def get_portfolio_for_view(self):
        """Получение распределения активов для вывода в консоль"""
        data = self.get_portfolio_data()
        whole_price = data["whole_price"]
        active_sum = 0
        res = {}
        for pos in data:
            if pos == "bond":
                if data[pos]["floater_price"] > 0:
                    res["floater_bond"] = data[pos]["floater_price"]
                    active_sum += data[pos]["floater_price"]
                if data[pos]["regular_price"] > 0:
                    res["regular_bond"] = data[pos]["regular_price"]
                    active_sum += data[pos]["regular_price"]
            else:
                if pos != "whole_price" and data[pos]["total_price"] > 0:
                    res[pos] = data[pos]["total_price"]
                    active_sum += data[pos]["total_price"]
        res['currency'] = whole_price - active_sum
        return res, whole_price

    def rebalance_1(self, old_structure, new_structure, whole_money):
        res = {}
        for pos in new_structure:
            cur_price = old_structure.get(pos, 0)
            new_price = whole_money * new_structure[pos]
            res[pos] = f"{cur_price}->{new_price} - {new_price - cur_price}"
        for pos in old_structure:
            if pos not in new_structure:
                res[pos] = f"{old_structure[pos]}->0 - {0 - old_structure[pos]}"
        return res

    def rebalance_3(self, old_structure, new_structure, whole_money):
        def check_sum(old_structure, new_structure, money):
            for pos in new_structure:
                if money * new_structure[pos] < old_structure.get(pos, 0):
                    return False
            return True

        l = whole_money
        r = whole_money * 100
        while r - l > 100:
            mid = (l + r) / 2
            if check_sum(old_structure, new_structure, mid):
                r = mid
            else:
                l = mid

        new_sum = l
        res = {}
        for pos in new_structure:
            cur_price = old_structure.get(pos, 0)
            new_price = new_sum * new_structure[pos]
            res[pos] = f"{round(cur_price, 2)}->{round(new_price, 2)} : {round(new_price - cur_price, 2)}"
        for pos in old_structure:
            if pos not in new_structure:
                res[pos] = f"{round(old_structure[pos], 2)}->0 : {round(0 - old_structure[pos], 2)}"
        return res
