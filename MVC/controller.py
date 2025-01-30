from config.config import TOKEN
from logger.logger import get_logger
from .model import Model
from .view import View

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
                                              " облигации (флоатеры и нет), фонды и другое")}
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
            return self.make_report()
        return "error"

    def make_report(self):
        data = self.model.get_portfolio_data()
        if data:
            return self.view.make_report(data)
        else:
            return "error"
