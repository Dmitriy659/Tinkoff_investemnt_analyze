import datetime
import os
from time import sleep

import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell

from logger.logger import get_logger

log = get_logger()


class View:
    def __init__(self):
        self.translate = {"bond": "Облигации", "share": "Акции", "etf": "Фонды", "regular": "обычным",
                          "floater": "плавающим", "whole_price": "Общая_информация"}
        self.HEADER_FORMAT = None
        self.TABLE_HEADER_FORMAT = None
        self.EVEN_FORMAT = None  # четная строка
        self.ODD_FORMAT = None  # нечетная строка

    def make_report(self, data):
        try:
            log.info("Начинаю создавать отчет...")
            os.makedirs("/results", exist_ok=True)

            workbook = xlsxwriter.Workbook(
                f"results/report_{datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")}.xlsx")
            self.HEADER_FORMAT = workbook.add_format({"bold": True, "bg_color": "#D3D3D3", "border": 1})
            self.TABLE_HEADER_FORMAT = workbook.add_format({"bold": True, "bg_color": "#6699ff", "border": 1})
            self.EVEN_FORMAT = workbook.add_format({"bg_color": "#ffffff", "border": 1})
            self.ODD_FORMAT = workbook.add_format({"bg_color": "#dbe9f9", "border": 1})

            general_information = {}

            for instrument_type in data:
                name = self.translate.get(instrument_type, instrument_type)
                worksheet = workbook.add_worksheet(name=name)
                if instrument_type == "bond":
                    self._make_bond_worksheet(data["bond"], worksheet, workbook, data["whole_price"],
                                              name)
                elif instrument_type == "share":
                    self._make_share_worksheet(data["share"], worksheet, workbook, data["whole_price"],
                                               name)
                elif instrument_type == "etf":
                    self._make_etf_worksheet(data["etf"], worksheet, workbook, data["whole_price"], name)
                elif instrument_type == "whole_price":
                    self._make_general_worksheet(general_information, worksheet, workbook,
                                                 data["whole_price"], name)
                    break
                else:
                    self._make_other_worksheet(data[instrument_type], worksheet, data["whole_price"])

                general_information[instrument_type] = data[instrument_type]["total_price"]

            workbook.close()

            log.info("Отчет успешно создан и сохранен")
            sleep(0.08)
            return "ready"
        except Exception as e:
            log.error("Ошибка во время создания отчета, %s", str(e))
            return "error"

    def _make_bond_worksheet(self, data, worksheet, workbook, whole_price,
                             worksheet_name):
        width = {"A": 20, "B": 14, "C": 12, "E": 14, "F": 15, "G": 12, "H": 22, "I": 22, "J": 20, "K": 20, "L": 22,
                 "M": 18, "N": 16, "O": 16, "P": 20, "Q": 16, "R": 20}
        for i in width:
            worksheet.set_column(f"{i}:{i}", width[i])

        worksheet.write(0, 0, "Общая информация", self.HEADER_FORMAT)
        worksheet.write_row(1, 0, ["Общая стоимость", data["total_price"]])
        worksheet.write_row(2, 0, ["Общее количество", data["total_amount"]])
        worksheet.write_row(3, 0,
                            ["Доля от портфеля", data["total_price"] / whole_price * 100 if whole_price > 0 else 0])
        worksheet.write_row(4, 0, ['Общая сумма купонов', data["floater_coupon"] + data["regular_coupon"]])

        cur_row = 5
        for bond_type in ["regular", "floater"]:
            cur_row += 2
            worksheet.write(cur_row, 0, f"Общая информация по {self.translate[bond_type]} облигациям",
                            self.HEADER_FORMAT)
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Общая стоимость", data[f"{bond_type}_price"]])
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Общее количество", data[f"{bond_type}_amount"]])
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Доля от облигаций", round(data[f"{bond_type}_price"] / data["total_price"]
                                                                        * 100 if data["total_price"] > 0 else 0, 2)])
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Доля от портфеля",
                                             round(data[f"{bond_type}_price"] / whole_price if whole_price > 0 else 0,
                                                   2)])
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Сумма купонов", data[f"{bond_type}_coupon"]])
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Доходность купонов",
                                             round(
                                                 data[f"{bond_type}_coupon"] / data[f"{bond_type}_price"] * 100 if data[
                                                                                                                       f"{bond_type}_price"] > 0 else 0,
                                                 2)])

            cur_row += 2
            worksheet.write(cur_row, 0, "Информация по позициям", self.HEADER_FORMAT)
            cur_row += 1
            if bond_type == "regular":
                worksheet.write_row(cur_row, 0,
                                    ["Название", "Частота купонов", "Цена за одну", "Кол-во", "Полная цена",
                                     "Средняя цена",
                                     "Купоны", "Текущая доходность купонов", "Текущая полная доходность",
                                     "Потенциальные купоны", "Профит к номиналу", "Обшая потенциальная прибыль",
                                     "Амортизация", "Дата открытия", "Дата погашения", "Страна", "Номинал", "Название"],
                                    cell_format=self.TABLE_HEADER_FORMAT)
            else:
                worksheet.write_row(cur_row, 0,
                                    ["Название", "Частота купонов", "Цена за одну", "Кол-во", "Полная цена",
                                     "Средняя цена",
                                     "Купоны", "Текущая доходность купонов", "Текущая полная доходность",
                                     "Амортизация", "Дата открытия", "Дата погашения", "Страна", "Номинал", "Название"],
                                    cell_format=self.TABLE_HEADER_FORMAT)
            even_row = True
            for pos in data[f"{bond_type}_positions"]:
                cur_row += 1
                profit = round(pos["coupons"] / (pos["avr_price"] * pos["count"]) * 100 if pos["avr_price"] > 0 else 0,
                               2)
                full_profit = round(((pos["whole_price"] + pos["coupons"]) - (pos["avr_price"] * pos["count"])) / (
                            pos["avr_price"] * pos["count"]) * 100, 2)

                if even_row:
                    fmt = self.EVEN_FORMAT
                else:
                    fmt = self.ODD_FORMAT

                if bond_type == "regular":
                    worksheet.write_row(cur_row, 0, [pos["name"], pos["coupon_per"], pos["one_price"], pos["count"],
                                                     pos["whole_price"], pos["avr_price"], pos["coupons"], profit,
                                                     full_profit, pos["coupons_future_profit"], pos["buy_profit"],
                                                     pos["coupons_future_profit"] + pos["buy_profit"] + pos["coupons"],
                                                     pos["amortization"],
                                                     pos["placement_date"].strftime('%Y-%m-%d'),
                                                     pos["maturity_date"].strftime('%Y-%m-%d'),
                                                     pos["country"], pos["nominal"], pos["name"]],
                                        fmt)
                else:
                    worksheet.write_row(cur_row, 0, [pos["name"], pos["coupon_per"], pos["one_price"], pos["count"],
                                                     pos["whole_price"], pos["avr_price"], pos["coupons"], profit,
                                                     full_profit,
                                                     pos["amortization"],
                                                     pos["placement_date"].strftime('%Y-%m-%d'),
                                                     pos["maturity_date"].strftime('%Y-%m-%d'),
                                                     pos["country"], pos["nominal"], pos["name"]],
                                        fmt)
                even_row = not even_row

        cur_col = 19
        sector_names = []
        sector_nums = []
        for sector in data["sector"]:
            sector_names.append(sector)
            sector_nums.append(data["sector"][sector])
        sector_names = list(map(lambda x: x.strip().capitalize(), sector_names))
        worksheet.write_row(0, cur_col, sector_names)
        worksheet.write_row(1, cur_col, sector_nums)

        self._make_pie(worksheet, worksheet_name, workbook, [0, cur_col], [0, cur_col + len(sector_names) - 1],
                       [1, cur_col], [1, cur_col + len(sector_nums) - 1], "T5", "Распределение по секторам")

        cur_row = 20
        worksheet.write_row(cur_row, cur_col, ["Обычные", "Плавающие"])
        worksheet.write_row(cur_row + 1, cur_col, [data["regular_price"], data["floater_price"]])

        self._make_pie(worksheet, worksheet_name, workbook, [cur_row, cur_col], [cur_row, cur_col + 1],
                       [cur_row + 1, cur_col], [cur_row + 1, cur_col + 1], "T25", "Распределение облигаций")

    def _make_share_worksheet(self, data, worksheet, workbook, whole_price,
                              worksheet_name):
        width = {"A": 20, "B": 14, "C": 12, "E": 14, "F": 15, "G": 12, "H": 12, "I": 18, "J": 16, "K": 20, "L": 20}
        for i in width:
            worksheet.set_column(f"{i}:{i}", width[i])

        worksheet.write(0, 0, "Общая информация", self.HEADER_FORMAT)
        worksheet.write_row(1, 0, ["Общая стоимость", data["total_price"]])
        worksheet.write_row(2, 0, ["Общее количество", data["total_amount"]])
        worksheet.write_row(3, 0,
                            ["Доля в портфеле",
                             round(data["total_price"] / whole_price * 100 if whole_price > 0 else 0, 2)])
        worksheet.write_row(4, 0, ["Сумма дивидендов", data["dividend"]])
        worksheet.write_row(5, 0, ["Доходность дивидендов от акций",
                                   round(data["dividend"] / data["total_price"] * 100 if data["total_price"] > 0 else 0,
                                         2)])
        worksheet.write_row(6, 0, ["Доходность покупок", data["buy_profit"]])
        worksheet.write_row(7, 0, ["Общая доходность, Р", data["buy_profit"] + data["dividend"]])
        worksheet.write_row(7, 0, ["Общая доходность, %",
                                   round((data["buy_profit"] + data["dividend"]) / data["total_price"] * 100, 2)])

        worksheet.write(9, 0, "Информация по позициям", self.HEADER_FORMAT)
        worksheet.write_row(10, 0,
                            ["Название", "Страна", "Цена за одну", "Кол-во", "Общая стоимость", "Средняя стоимость",
                             "Доходность",
                             "Дивиденды", "Доходность дивидендов", "Полная доходность", "Будущий дивиденд",
                             "Дата дивидендов"],
                            self.TABLE_HEADER_FORMAT)
        cur_row = 11

        even_row = True
        for pos in data["positions"]:
            profit = round(pos["whole_price"] / (pos["avr_price"] * pos["count"]) * 100 if pos["avr_price"] * pos[
                "count"] else 0, 2) - 100
            div_profit = round(pos["dividend"] / pos["whole_price"] * 100 if pos["whole_price"] > 0 else 0, 2)

            if even_row:
                fmt = self.EVEN_FORMAT
            else:
                fmt = self.ODD_FORMAT

            worksheet.write_row(cur_row, 0,
                                [pos["name"], pos["country"], pos["one_price"], pos["count"], pos["whole_price"],
                                 pos["avr_price"], profit, pos["dividend"], div_profit, profit + div_profit,
                                 pos["div_price"], pos["div_date"]],
                                fmt)
            cur_row += 1
            even_row = not even_row

        cur_col = 14
        sector_names = []
        sector_nums = []
        for sector in data["sector"]:
            sector_names.append(sector)
            sector_nums.append(data["sector"][sector])
        sector_names = list(map(lambda x: x.strip().capitalize(), sector_names))
        worksheet.write_row(0, cur_col, sector_names)
        worksheet.write_row(1, cur_col, sector_nums)

        self._make_pie(worksheet, worksheet_name, workbook, [0, cur_col], [0, cur_col + len(sector_names) - 1],
                       [1, cur_col], [1, cur_col + len(sector_nums) - 1], "O5", "Распределение по секторам")

    def _make_etf_worksheet(self, data, worksheet, workbook, whole_price,
                            worksheet_name):
        width = {"A": 20, "B": 12, "D": 18, "E": 18, "F": 15, "G": 16}
        for i in width:
            worksheet.set_column(f"{i}:{i}", width[i])

        worksheet.write(0, 0, "Общая информация", self.HEADER_FORMAT)
        worksheet.write_row(1, 0, ["Общая стоимость", data["total_price"]])
        worksheet.write_row(2, 0, ["Общее количество", data["total_amount"]])
        worksheet.write_row(3, 0,
                            ["Доля в портфеле", data["total_price"] / whole_price * 100 if whole_price > 0 else 0])
        worksheet.write_row(4, 0, ["Доходность покупок, Р", data["buy_profit"]])
        worksheet.write_row(5, 0, ["Доходность покупок, %", round(data["buy_profit"] / data["total_price"] * 100, 2)])

        worksheet.write(7, 0, "Информация по позициям", self.HEADER_FORMAT)
        worksheet.write_row(8, 0,
                            ["Название", "Цена за одну", "Кол-во", "Общая стоимость", "Средняя стоимость",
                             "Доходность, %",
                             "Доходность, Р", "Фокус фонда"],
                            self.TABLE_HEADER_FORMAT)
        cur_row = 9
        even_row = True
        for pos in data["positions"]:
            profit_percent = round(
                pos["whole_price"] / (pos["avr_price"] * pos["count"]) if (pos["avr_price"] * pos["count"]) > 0 else 0,
                2)
            profit = round(
                pos["whole_price"] - pos["avr_price"] * pos["count"] if (pos["avr_price"] * pos["count"]) > 0 else 0, 2)

            if even_row:
                fmt = self.EVEN_FORMAT
            else:
                fmt = self.ODD_FORMAT

            worksheet.write_row(cur_row, 0,
                                [pos["name"], pos["one_price"], pos["count"], pos["whole_price"], pos["avr_price"],
                                 profit_percent, profit, pos["focus_type"]],
                                cell_format=fmt)
            cur_row += 1
            even_row = not even_row

        cur_col = 8
        focus_names = []
        focus_nums = []
        for sector in data["focus_type"]:
            focus_names.append(sector)
            focus_nums.append(data["focus_type"][sector])
        focus_names = list(map(lambda x: x.strip().capitalize(), focus_names))
        worksheet.write_row(0, cur_col, focus_names)
        worksheet.write_row(1, cur_col, focus_nums)

        self._make_pie(worksheet, worksheet_name, workbook, [0, cur_col], [0, cur_col + len(focus_names) - 1],
                       [1, cur_col], [1, cur_col + len(focus_nums) - 1], "J5", "Распределение по фокусам")

    def _make_other_worksheet(self, data, worksheet, whole_price):
        worksheet.write(0, 0, "Общая информация", self.HEADER_FORMAT)
        worksheet.write_row(1, 0, ["Общая стоимость", data["total_price"]])
        worksheet.write_row(2, 0, ["Общее количество", data["total_amount"]])
        worksheet.write_row(3, 0,
                            ["Доля в портфеле", data["total_price"] / whole_price * 100 if whole_price > 0 else 0])

        worksheet.write(5, 0, "Информация по позициям", self.HEADER_FORMAT)
        worksheet.write_row(6, 0, ["Название", "Цена за одну", "Кол-во", "Общая стоимость", "Фокус фонда"])
        cur_row = 7

        for pos in data["positions"]:
            worksheet.write_row(cur_row, 0,
                                [pos["name"], pos["one_price"], pos["count"], pos["whole_price"]])
            cur_row += 1

    def _make_general_worksheet(self, data, worksheet, workbook, whole_price,
                                worksheet_name):
        worksheet.write(0, 0, "Общая информация", self.HEADER_FORMAT)
        worksheet.write_row(1, 0, ["Общая стоимость", whole_price])

        worksheet.write(3, 0, "Информация по ценным бумагам")
        cur_row = 4
        pos_cost = 0
        for pos in data:
            worksheet.write_row(cur_row, 0, [self.translate.get(pos, pos), data[pos]])
            pos_cost += data[pos]
            cur_row += 1
        worksheet.write_row(cur_row, 0, ["Валюта", whole_price - pos_cost])

        self._make_pie(worksheet, worksheet_name, workbook, [4, 0], [4 + len(data), 0],
                       [4, 1], [4 + len(data), 1], "E3", "Распределение активов")

    def _make_pie(self, worksheet, worksheet_name, workbook, category_left, category_right, values_left, values_right,
                  insert_place, pie_name):
        categories_left = xl_rowcol_to_cell(*category_left)
        categories_right = xl_rowcol_to_cell(*category_right)

        values_left = xl_rowcol_to_cell(*values_left)
        values_right = xl_rowcol_to_cell(*values_right)

        chart = workbook.add_chart({"type": "pie"})
        chart.add_series({
            "name": pie_name,
            "categories": f"={worksheet_name}!{categories_left}:{categories_right}",
            "values": f"={worksheet_name}!{values_left}:{values_right}",
            "data_lables": {"percentage": True, "value": True}
        })

        worksheet.insert_chart(insert_place, chart)

    def show_rebalance_changes(self, changes):
        print('-' * 15)
        print("Результат")
        for key, value in changes.items():
            print(f"{key} - {value}")
        print('-' * 15)
        return "ready"
