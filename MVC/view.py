import datetime
import xlsxwriter
import os

from time import sleep
from logger.logger import get_logger
from googletrans import Translator
from xlsxwriter.utility import xl_rowcol_to_cell

log = get_logger()


class View:
    def __init__(self):
        self.translate = {"bond": "Облигации", "share": "Акции", "etf": "Фонды", "regular": "обычным",
                          "floater": "плавающим", "whole_price": "Общая_информация"}
        self.translator = Translator()

    def make_report(self, data):
        try:
            log.info("Начинаю создавать отчет...")
            os.makedirs("/results", exist_ok=True)

            workbook = xlsxwriter.Workbook(
                f"results/report_{datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")}.xlsx")
            header_format = workbook.add_format({"bold": True, "bg_color": "#D3D3D3", "border": 1})
            currency_format = workbook.add_format({"num_format": "#,##0.00 ₽"})

            general_information = {}

            for instrument_type in data:
                name = self.translate.get(instrument_type, instrument_type)
                worksheet = workbook.add_worksheet(name=name)
                if instrument_type == "bond":
                    self._make_bond_worksheet(data["bond"], worksheet, workbook, header_format, currency_format,
                                              data["whole_price"], name)
                elif instrument_type == "share":
                    self._make_share_worksheet(data["share"], worksheet, workbook, header_format, currency_format,
                                               data["whole_price"], name)
                elif instrument_type == "etf":
                    self._make_etf_worksheet(data["etf"], worksheet, workbook, header_format, currency_format,
                                             data["whole_price"], name)
                elif instrument_type == "whole_price":
                    self._make_general_worksheet(general_information, worksheet, workbook, header_format, currency_format,
                                                 data["whole_price"], name)
                    break
                else:
                    self._make_other_worksheet(data[instrument_type], worksheet, workbook, header_format, currency_format,
                                               data["whole_price"], name)

                general_information[instrument_type] = data[instrument_type]["total_price"]

            workbook.close()

            log.info("Отчет успешно создан и сохранен")
            sleep(0.08)
            return "ready"
        except Exception as e:
            log.error("Ошибка во время создания отчета, %s", str(e))
            return "error"

    def _make_bond_worksheet(self, data, worksheet, workbook, header_format, currency_format, whole_price,
                             worksheet_name):
        worksheet.write(0, 0, "Общая информация", header_format)
        worksheet.write_row(1, 0, ["Общая стоимость", data["total_price"]])
        worksheet.write_row(2, 0, ["Общее количество", data["total_amount"]])
        worksheet.write_row(3, 0,
                            ["Доля от портфеля", data["total_price"] / whole_price * 100 if whole_price > 0 else 0])

        cur_row = 4
        for bond_type in ["regular", "floater"]:
            cur_row += 2
            worksheet.write(cur_row, 0, f"Общая информация по {self.translate[bond_type]} облигациям", header_format)
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Общая стоимость", data[f"{bond_type}_price"]])
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Общее количество", data[f"{bond_type}_amount"]])
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Доля от облигаций", data[f"{bond_type}_price"] / data["total_price"]
                                                                  * 100 if data["total_price"] > 0 else 0])
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Доля от портфеля", data[f"{bond_type}_price"] /
                                                                 whole_price if whole_price > 0 else 0])
            cur_row += 2
            worksheet.write(cur_row, 0, "Информация по позициям")
            cur_row += 1
            worksheet.write_row(cur_row, 0, ["Название", "Частота купонов", "Цена за одну", "Кол-во", "Полная цена",
                                             "Страна", "Номинал"])
            for pos in data[f"{bond_type}_positions"]:
                cur_row += 1
                worksheet.write_row(cur_row, 0, [pos["name"], pos["coupon_per"], pos["one_price"], pos["count"],
                                                 pos["whole_price"], pos["country"], pos["nominal"]])

        cur_col = 9
        sector_names = []
        sector_nums = []
        for sector in data["sector"]:
            sector_names.append(sector)
            sector_nums.append(data["sector"][sector])
        sector_names = self.translator.translate("...  ".join(sector_names), src="en", dest="ru").text.split("...")
        sector_names = list(map(lambda x: x.strip().capitalize(), sector_names))
        if "Это" in sector_names:
            sector_names[sector_names.index("Это")] = "IT"
        worksheet.write_row(0, cur_col, sector_names)
        worksheet.write_row(1, cur_col, sector_nums)

        self._make_pie(worksheet, worksheet_name, workbook, [0, cur_col], [0, cur_col + len(sector_names) - 1],
                       [1, cur_col], [1, cur_col + len(sector_nums) - 1], "J5", "Распределение по секторам")

        cur_row = 20
        worksheet.write_row(cur_row, cur_col, ["Обычные", "Плавающие"])
        worksheet.write_row(cur_row + 1, cur_col, [data["regular_price"], data["floater_price"]])

        self._make_pie(worksheet, worksheet_name, workbook, [cur_row, cur_col], [cur_row, cur_col + 1],
                       [cur_row + 1, cur_col], [cur_row + 1, cur_col + 1], "J25", "Распределение облигаций")

    def _make_share_worksheet(self, data, worksheet, workbook, header_format, currency_format, whole_price,
                              worksheet_name):
        worksheet.write(0, 0, "Общая информация", header_format)
        worksheet.write_row(1, 0, ["Общая стоимость", data["total_price"]])
        worksheet.write_row(2, 0, ["Общее количество", data["total_amount"]])
        worksheet.write_row(3, 0,
                            ["Доля в портфеле", data["total_price"] / whole_price * 100 if whole_price > 0 else 0])

        worksheet.write(5, 0, "Информация по позициям", header_format)
        worksheet.write_row(6, 0, ["Название", "Страна", "Цена за одну", "Кол-во", "Общая стоимость"])
        cur_row = 7

        for pos in data["positions"]:
            worksheet.write_row(cur_row, 0,
                                [pos["name"], pos["country"], pos["one_price"], pos["count"], pos["whole_price"]])
            cur_row += 1

        cur_col = 8
        sector_names = []
        sector_nums = []
        for sector in data["sector"]:
            sector_names.append(sector)
            sector_nums.append(data["sector"][sector])
        sector_names = self.translator.translate("...  ".join(sector_names), src="en", dest="ru").text.split("...")
        sector_names = list(map(lambda x: x.strip().capitalize(), sector_names))
        if "Это" in sector_names:
            sector_names[sector_names.index("Это")] = "IT"
        worksheet.write_row(0, cur_col, sector_names)
        worksheet.write_row(1, cur_col, sector_nums)

        self._make_pie(worksheet, worksheet_name, workbook, [0, cur_col], [0, cur_col + len(sector_names) - 1],
                       [1, cur_col], [1, cur_col + len(sector_nums) - 1], "J5", "Распределение по секторам")

    def _make_etf_worksheet(self, data, worksheet, workbook, header_format, currency_format, whole_price,
                            worksheet_name):
        worksheet.write(0, 0, "Общая информация", header_format)
        worksheet.write_row(1, 0, ["Общая стоимость", data["total_price"]])
        worksheet.write_row(2, 0, ["Общее количество", data["total_amount"]])
        worksheet.write_row(3, 0,
                            ["Доля в портфеле", data["total_price"] / whole_price * 100 if whole_price > 0 else 0])

        worksheet.write(5, 0, "Информация по позициям", header_format)
        worksheet.write_row(6, 0, ["Название", "Цена за одну", "Кол-во", "Общая стоимость", "Фокус фонда"])
        cur_row = 7

        for pos in data["positions"]:
            worksheet.write_row(cur_row, 0,
                                [pos["name"], pos["one_price"], pos["count"], pos["whole_price"], pos["focus_type"]])
            cur_row += 1

        cur_col = 8
        focus_names = []
        focus_nums = []
        for sector in data["focus_type"]:
            focus_names.append(sector)
            focus_nums.append(data["focus_type"][sector])
        focus_names = self.translator.translate("...  ".join(focus_names), src="en", dest="ru").text.split("...")
        focus_names = list(map(lambda x: x.strip().capitalize(), focus_names))
        if "Это" in focus_names:
            focus_names[focus_names.index("Это")] = "IT"
        worksheet.write_row(0, cur_col, focus_names)
        worksheet.write_row(1, cur_col, focus_nums)

        self._make_pie(worksheet, worksheet_name, workbook, [0, cur_col], [0, cur_col + len(focus_names) - 1],
                       [1, cur_col], [1, cur_col + len(focus_nums) - 1], "J5", "Распределение по фокусам")

    def _make_other_worksheet(self, data, worksheet, workbook, header_format, currency_format, whole_price,
                              worksheet_name):
        worksheet.write(0, 0, "Общая информация", header_format)
        worksheet.write_row(1, 0, ["Общая стоимость", data["total_price"]])
        worksheet.write_row(2, 0, ["Общее количество", data["total_amount"]])
        worksheet.write_row(3, 0,
                            ["Доля в портфеле", data["total_price"] / whole_price * 100 if whole_price > 0 else 0])

        worksheet.write(5, 0, "Информация по позициям", header_format)
        worksheet.write_row(6, 0, ["Название", "Цена за одну", "Кол-во", "Общая стоимость", "Фокус фонда"])
        cur_row = 7

        for pos in data["positions"]:
            worksheet.write_row(cur_row, 0,
                                [pos["name"], pos["one_price"], pos["count"], pos["whole_price"]])
            cur_row += 1

    def _make_general_worksheet(self, data, worksheet, workbook, header_format, currency_format, whole_price,
                                worksheet_name):
        worksheet.write(0, 0, "Общая информация", header_format)
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
