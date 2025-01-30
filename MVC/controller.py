from config.config import TOKEN
from logger.logger import get_logger
from .model import Model
from .view import View
from .utils import check_rebalance_values

from tinkoff.invest import Client

token = TOKEN
log = get_logger()


class Controller:
    def __init__(self):
        with Client(token) as client:
            self.account_id = client.users.get_accounts().accounts[0].id
            log.info("Account id successfully received")

        self.available_functions = {"ОТЧЕТ": ("Создать excel отчет с расширенной аналитикой по портфелю",
                                              "Расчёты и аналитика с графиками по каждому виду актива: акции,"
                                              " облигации (флоатеры и нет), фонды и другое"),
                                    "РЕБАЛАНСИРОВКА": (
                                        "Найти итоговые стоимости активов в соответствии с ребалансирвокой",
                                        "Есть три вида ребалансировки: в первой можно всё продавать и покупать,"
                                        " во второй можно всё продавать и покупать, при этом добавляется ещё сумма\n"
                                        "В третьей активы ребалансировки не продаются, и ищется минимальная дополнительная сумма,"
                                        "чтобы достичь ребалансировки")
                                    }
        self.model = Model(self.account_id, token)
        self.view = View()

    def start_work(self):
        print("Привет, это приложение расширенной аналитики брокерского счета в Тинькофф-инвестициях")
        print("Сейчас я могу предоставить следующий функционал, чтобы узнать о функции поподробнее напиши 'ФУНКЦИЯ "
              "info'.\nЧтобы воспользоваться функцией напиши её название так: 'ФУНКЦИЯ'\n")
        print("Чтобы завершить программу, напиши 'ВЫЙТИ'")

        for func in self.available_functions:
            print(f"{func} - {self.available_functions[func][0]}")

        while True:
            query = input("Напиши функцию, которую ты хочешь запустить\n").strip()
            if query.endswith("info"):
                func_name = query.split()
                if func_name[0] in self.available_functions:
                    print(self.available_functions[func_name[0]][1])
                else:
                    print("Такой функции нет")
            elif query in self.available_functions:
                status = self.choice_function(query)
                print("Статус", status)
            elif query == "ВЫЙТИ":
                print("Завершение...")
                break
            else:
                print("Такой функции нет")

    def choice_function(self, func_name):
        if func_name == "ОТЧЕТ":
            return self.__make_report()
        elif func_name == 'РЕБАЛАНСИРОВКА':
            return self.__make_rebalance()
        return "error"

    def __make_report(self):
        data = self.model.get_portfolio_data()
        if data:
            return self.view.make_report(data)
        else:
            return "error"

    def __make_rebalance(self):
        try:
            print("Сначала укажи, какой вид балансировки ты хочешь сделать, напиши 1, 2 или 3")

            errors_count = 0
            while errors_count < 3:
                rebalance_type = input().strip()
                if rebalance_type in ("1", "2", "3"):
                    output, whole_money = self.model.get_portfolio_for_view()
                    print('Текущее состояние портфеля')
                    print("Общая стоимость", whole_money)
                    for key, value in output.items():
                        print(f"{key} - {round(value / whole_money, 3)}")
                    print(
                        'Введите новую структуру портфеля в следующем виде: ИНСТРУМЕНТ-ДОЛЯ, ИНСТРУМЕНТ-ДОЛЯ... Если сумма'
                        ' долей меньше 1, то они будут равномерно увеличены, а если больше 1, то уменьшены')

                    rebalance_str = input().strip()
                    rebalance_str, status = check_rebalance_values(rebalance_str)

                    if status == "rebalanced":
                        print("Структуру была ребалансирована")
                        for key, value in rebalance_str.items():
                            print(f"{key} - {value}")
                        decision = input("Устраивает ли новая структура? Введи 1, если да\n").strip()
                        if decision != "1":
                            return "error"
                    elif status == "error" or not rebalance_str:
                        print("Ошибка")
                        return "error"

                    if rebalance_type == "1":
                        changes = self.model.rebalance_1(output, rebalance_str, whole_money)
                    elif rebalance_type == "2":
                        money = int(input("Введите доплату"))
                        changes = self.model.rebalance_1(output, rebalance_str, whole_money + money)
                    else:
                        changes = self.model.rebalance_3(output, rebalance_str, whole_money)
                    return self.view.show_rebalance_changes(changes)
                else:
                    print('Такого типа нет')
                    errors_count += 1
            else:
                print('Лучше сначала ознакомьтесь с правилами')
                return "error"
        except Exception as e:
            log.error("Ошибка во время ребалансировки", str(e))
            return "error"
