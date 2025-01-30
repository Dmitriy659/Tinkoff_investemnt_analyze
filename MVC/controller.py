from config.config import TOKEN
from logger.logger import get_logger
from .model import Model

from tinkoff.invest import Client

token = TOKEN
log = get_logger()


class Controller:
    def __init__(self):
        with Client(token) as client:
            self.account_id = client.users.get_accounts().accounts[0].id
            print(self.account_id)
            log.info("Account id successfully received")

        self.available_functions = {"ОТЧЕТ": ("Создать excel отчет с расширенной аналитикой по портфелю",
                                              "Расчёт стоимости каждого актива: акции, облигации (флоатеры и нет),"
                                              "фонды - отразить все данные на графиках")}
        self.model = Model(self.account_id, token)

    def start_work(self):
        print("Привет, это приложение расширенной аналитики брокерского счета в Тинькофф-инвестициях")
        print("Сейчас я могу предоставить следующий функционал, чтобы узнать о функции поподробнее напиши '{ФУНКЦИЯ} "
              "info'.\nА чтобы воспользоваться функцией напиши '{ФУНКЦИЯ}'\n")

        for func in self.available_functions:
            print(f"{func} - {self.available_functions[func][0]}")

        while True:
            query = input().strip()
            if query.endswith('info'):
                func_name = query.split()
                if func_name in self.available_functions:
                    print(self.available_functions[query][1])
                else:
                    print('Такой функции нет')
            elif query in self.available_functions:
                status = self.choice_function(query)
                print('Статус', status)

    def choice_function(self, func_name):
        if func_name == 'ОТЧЕТ':
            return self.make_report()
        return "error"

    def make_report(self):
        data = self.model.get_portfolio_data()

