import datetime
import time
from collections import defaultdict

from tinkoff.invest import Client, InstrumentIdType, InstrumentStatus, OperationType
from tinkoff.invest.services import Services
from tinkoff.invest.utils import now

from logger.logger import get_logger

log = get_logger()


class MainModel:
    def __init__(self, account_id, token, open_date):
        self.account_id = account_id
        self.token = token
        self.open_date = open_date
        self.currencies = defaultdict(str)

    def _convert_money_to_int(self, money):
        res = money.units + money.nano / 10**9
        if hasattr(money, "currency") and money.currency != "rub":
            res *= self.currencies.get(money.currency, 1)
        return res

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


class Model(MainModel):
    def __init__(self, account_id, token, open_date):
        super().__init__(account_id, token, open_date)
        self.positions_info = {}

        with Client(token) as client:
            currencies = client.instruments.currencies(instrument_status=InstrumentStatus(2))
            # a = client.instruments.currency_by(id="eur")
            for currency in currencies.instruments:
                price = client.market_data.get_last_prices(figi=[currency.figi])
                price = price.last_prices[0].price
                price = price.units + price.nano / 10**9
                self.currencies[currency.iso_currency_name] = price

    def get_portfolio_data(self):
        try:
            res = {
                "bond": {
                    "total_price": 0,
                    "regular_price": 0,
                    "floater_price": 0,
                    "total_amount": 0,
                    "regular_amount": 0,
                    "floater_amount": 0,
                    "floater_coupon": 0,
                    "regular_coupon": 0,
                    "regular_positions": [],
                    "floater_positions": [],
                    "sector": defaultdict(int),
                },
                "share": {
                    "total_price": 0,
                    "total_amount": 0,
                    "buy_profit": 0,
                    "positions": [],
                    "dividend": 0,
                    "sector": defaultdict(int),
                },
                "etf": {
                    "total_price": 0,
                    "total_amount": 0,
                    "buy_profit": 0,
                    "positions": [],
                    "focus_type": defaultdict(int),
                },
            }
            whole_price = 0

            with Client(self.token) as client:
                log.info("Получение данных по портфелю")

                positions = client.operations.get_positions(account_id=self.account_id)
                portfolio = client.operations.get_portfolio(account_id=self.account_id)
                operations = client.operations.get_operations(
                    account_id=self.account_id,
                    from_=self.open_date,
                    to=now(),
                )

                blocked_money = sum(self._convert_money_to_int(item) for item in positions.blocked)
                whole_price += blocked_money

                uid_bond_float = self.get_positions_info(positions, client)
                dividens, dividend_per_share, coupons_per_bond, coupons_float, coupons_reg = self.process_operations(
                    operations, client, uid_bond_float
                )

                portfolio_average_prices = dict()

                for op in portfolio.positions:
                    portfolio_average_prices[op.figi] = self._convert_money_to_int(op.average_position_price)

                for money in positions.money:
                    cur_price = self._convert_money_to_int(money)
                    if money.currency != "rub":
                        cur_price *= self.currencies.get(money.currency, 1)
                    whole_price += cur_price

                for position in positions.securities:
                    if position.instrument_type == "bond":  # облигация
                        cnt = position.balance
                        info, price = (
                            self.positions_info[position.figi]["info"],
                            self.positions_info[position.figi]["price"],
                        )

                        initial_nominal = self._convert_money_to_int(info.initial_nominal)
                        price = price.last_prices[0].price
                        price = ((price.units + price.nano / 10**9) / 100) * initial_nominal
                        res["bond"]["total_amount"] += cnt
                        res["bond"]["total_price"] += price * cnt

                        if info.floating_coupon_flag:
                            res["bond"]["floater_amount"] += cnt
                            res["bond"]["floater_price"] += price * cnt
                            res["bond"]["floater_positions"].append(
                                {
                                    "name": info.name,
                                    "coupon_per": info.coupon_quantity_per_year,
                                    "one_price": price,
                                    "count": cnt,
                                    "whole_price": cnt * price,
                                    "avr_price": portfolio_average_prices[position.figi],
                                    "coupons": coupons_per_bond.get(info.name, 0),
                                    "country": info.country_of_risk_name,
                                    "nominal": self._convert_money_to_int(info.initial_nominal),
                                    "maturity_date": info.maturity_date,
                                    "placement_date": info.placement_date,
                                    "days_before_maturity": (
                                        info.maturity_date - datetime.datetime.now(datetime.timezone.utc)
                                    ).days,
                                    "amortization": info.amortization_flag,
                                }
                            )
                        else:
                            coups = client.instruments.get_bond_coupons(
                                figi=position.figi, from_=info.placement_date, to=info.maturity_date
                            )
                            nearest_coupon_idx = 0
                            left, right = 0, len(coups.events) - 1
                            while left <= right:
                                mid = (left + right) // 2
                                if coups.events[mid].coupon_date < datetime.datetime.now(datetime.timezone.utc):
                                    left = mid + 1
                                else:
                                    nearest_coupon_idx = mid
                                    right = mid - 1
                            pay_one_bond = self._convert_money_to_int(coups.events[nearest_coupon_idx].pay_one_bond)
                            if pay_one_bond == 0:  # если следующий купон не определен
                                pay_one_bond = self._convert_money_to_int(
                                    coups.events[max(0, nearest_coupon_idx - 1)].pay_one_bond
                                )
                            coupons_percent = (
                                pay_one_bond
                                * info.coupon_quantity_per_year
                                / self._convert_money_to_int(info.initial_nominal)
                            )
                            coupons_percent = round(coupons_percent * 100, 1)
                            coups.events = coups.events[nearest_coupon_idx:]

                            coupons_profit = 0
                            for coup in coups.events:
                                pay = coup.pay_one_bond
                                coupons_profit += self._convert_money_to_int(pay) * cnt
                            buy_profit = (price - portfolio_average_prices[position.figi]) * cnt

                            res["bond"]["regular_amount"] += cnt
                            res["bond"]["regular_price"] += price * cnt
                            res["bond"]["regular_positions"].append(
                                {
                                    "name": info.name,
                                    "coupon_per": info.coupon_quantity_per_year,
                                    "one_price": price,
                                    "count": cnt,
                                    "whole_price": cnt * price,
                                    "avr_price": portfolio_average_prices[position.figi],
                                    "coupons": coupons_per_bond.get(info.name, 0),
                                    "country": info.country_of_risk_name,
                                    "coupons_percent": coupons_percent,
                                    "nominal": initial_nominal,
                                    "maturity_date": info.maturity_date,
                                    "days_before_maturity": (
                                        info.maturity_date - datetime.datetime.now(datetime.timezone.utc)
                                    ).days,
                                    "placement_date": info.placement_date,
                                    "amortization": info.amortization_flag,
                                    "coupons_future_profit": coupons_profit,
                                    "buy_profit": buy_profit,
                                }
                            )

                        res["bond"]["sector"][info.sector] += price * cnt
                        whole_price += price * cnt
                    elif position.instrument_type == "share":  # акция
                        cnt = position.balance
                        info, price = (
                            self.positions_info[position.figi]["info"],
                            self.positions_info[position.figi]["price"],
                        )

                        divs = client.instruments.get_dividends(
                            figi=position.figi,
                            from_=datetime.datetime.now(),
                            to=datetime.datetime.now() + datetime.timedelta(days=180),
                        )
                        if divs.dividends:
                            div_date = divs.dividends[0].record_date.strftime("%Y-%m-%d")
                            div_value = divs.dividends[0].dividend_net
                            div_price = self._convert_money_to_int(div_value) * cnt
                        else:
                            div_date = ""
                            div_price = ""

                        price = price.last_prices[0].price
                        price = self._convert_money_to_int(price)

                        res["share"]["total_price"] += price * cnt
                        res["share"]["total_amount"] += cnt
                        res["share"]["buy_profit"] += (price - portfolio_average_prices[position.figi]) * cnt
                        res["share"]["positions"].append(
                            {
                                "name": info.name,
                                "country": info.country_of_risk_name,
                                "one_price": price,
                                "count": cnt,
                                "whole_price": cnt * price,
                                "avr_price": portfolio_average_prices[position.figi],
                                "dividend": dividend_per_share.get(info.name, 0),
                                "div_date": div_date,
                                "div_price": div_price,
                            }
                        )
                        res["share"]["sector"][info.sector] += price * cnt
                        whole_price += price * cnt
                    elif position.instrument_type == "etf":  # фонд
                        cnt = position.balance
                        info, price = (
                            self.positions_info[position.figi]["info"],
                            self.positions_info[position.figi]["price"],
                        )

                        price = price.last_prices[0].price
                        price = self._convert_money_to_int(price)

                        res["etf"]["total_price"] += price * cnt
                        res["etf"]["total_amount"] += cnt
                        res["etf"]["buy_profit"] += (price - portfolio_average_prices[position.figi]) * cnt
                        res["etf"]["positions"].append(
                            {
                                "name": info.name,
                                "one_price": price,
                                "count": cnt,
                                "whole_price": cnt * price,
                                "focus_type": info.focus_type,
                                "avr_price": portfolio_average_prices[position.figi],
                            }
                        )
                        res["etf"]["focus_type"][info.focus_type] += price * cnt
                        whole_price += price * cnt
                    else:
                        instrument_type = position.instrument_type
                        cnt = position.balance
                        info, price = (
                            self.positions_info[position.figi]["info"],
                            self.positions_info[position.figi]["price"],
                        )

                        price = price.last_prices[0].price
                        price = self._convert_money_to_int(price)

                        res.setdefault(instrument_type, {"total_price": 0, "total_amount": 0, "positions": []})

                        res[instrument_type]["total_price"] += price * cnt
                        res[instrument_type]["total_amount"] += cnt
                        res[instrument_type]["positions"].append(
                            {"name": info.name, "one_price": price, "count": cnt, "whole_price": cnt * price}
                        )
                        whole_price += price * cnt
                res["whole_price"] = whole_price
                res["share"]["dividend"] = dividens
                res["bond"]["floater_coupon"] = coupons_float
                res["bond"]["regular_coupon"] = coupons_reg

                res["bond"]["regular_positions"].sort(key=lambda x: x["whole_price"], reverse=True)
                res["bond"]["floater_positions"].sort(key=lambda x: x["whole_price"], reverse=True)
                res["share"]["positions"].sort(key=lambda x: x["whole_price"], reverse=True)
                res["etf"]["positions"].sort(key=lambda x: x["whole_price"], reverse=True)

                log.info("Данные успешно получены")
                time.sleep(0.08)
                return res
        except Exception as e:
            log.error("Error while getting portfolio data", str(e))
            return {}

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
        res["currency"] = whole_price - active_sum
        return res, whole_price

    def rebalance_1(self, old_structure, new_structure, whole_money):
        res = {}
        whole_price = 0
        for pos in new_structure:
            cur_price = old_structure.get(pos, 0)
            new_price = whole_money * new_structure[pos]
            whole_price += new_price
            res[pos] = f"{round(cur_price, 2)}->{round(new_price, 2)} - {round(new_price - cur_price, 2)}"
        for pos in old_structure:
            if pos not in new_structure:
                res[pos] = f"{round(old_structure[pos], 2)}->0 - {round(0 - old_structure[pos], 2)}"
        res["whole_price"] = round(whole_price, 2)
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
        res["whole_price"] = round(new_sum, 2)
        return res

    def process_operation(self, op, client):  # TODO скорее всего бесполезно
        """
        Получение информации и цены.
        """
        if op.figi in self.positions_info:
            info = self.positions_info[op.figi]["info"]
        else:
            info, price = self._get_instrument_info(client, op.figi, op.instrument_type)
            info = info.instrument
            self.positions_info[op.figi] = {"info": info, "price": price}

        value = self._convert_money_to_int(op.payment)
        return info, value

    def process_operations(self, operations, client, uid_bond_float):
        """
        Получение информации по купонам и дивидендам для бумаг в портфеле
        """
        dividens = 0
        dividend_per_share = defaultdict(int)
        coupons_per_bond = defaultdict(int)
        coupons_float = 0
        coupons_reg = 0

        for op in operations.operations:
            if op.operation_type == OperationType(21):  # дивиденды
                info, value = self.process_operation(op, client)
                dividens += value
                dividend_per_share[info.name] += value
            elif op.operation_type == OperationType(23):  # купоны
                info, value = self.process_operation(op, client)
                coupons_per_bond[info.name] += value
                if op.position_uid in uid_bond_float:
                    coupons_float += value
                else:
                    coupons_reg += value

        return dividens, dividend_per_share, coupons_per_bond, coupons_float, coupons_reg

    def get_positions_info(self, positions, client):
        """
        Сохранение информации и цены для всех инструментов, а также получегие возвар множества с id флоатеров
        """
        uid_bond_float = set()

        for position in positions.securities:
            info, price = self._get_instrument_info(client, position.figi, position.instrument_type)
            info = info.instrument

            self.positions_info[position.figi] = {"info": info, "price": price}
            if position.instrument_type == "bond" and info.floating_coupon_flag:
                uid_bond_float.add(position.position_uid)
        return uid_bond_float
