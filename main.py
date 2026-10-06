import asyncio

from openpyxl import load_workbook
# from openpyxl.descriptors.excel import Extension
from openpyxl.styles import PatternFill

from client import CheckResultEnum, AsyncKKTChecker
#
# # Tolerate xlsx files whose pivot-cache extensions omit the `uri` attribute
# # (Excel/LibreOffice produce these; openpyxl's strict descriptor rejects them).
# Extension.uri.allow_none = True


async def main() -> None:
    # Load the Excel file
    wb = load_workbook("test.xlsx")

    # Select the "KKT" worksheet
    ws = wb["ККТ"]

    # Iterate over all rows (including header)
    title_column_index = None
    model_column_index = None
    number_column_index = None
    state_column_index = None

    header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    for i, state_cell in enumerate(header):
        match state_cell:
            case "Наименование":
                title_column_index = i
            case "Модель ККТ":
                model_column_index = i
            case "Заводской Номер ККТ":
                number_column_index = i
            case "Статус Проверки":
                state_column_index = i

    checker = AsyncKKTChecker()
    try:
        for row in ws.iter_rows(min_row=2, max_row=400):
            owner_cell = row[title_column_index]
            model_cell = row[model_column_index]
            number_cell = row[number_column_index]
            state_cell = row[state_column_index]

            print(owner_cell.value)

            if owner_cell.value and model_cell.value and number_cell.value:
                try:
                    res = await checker.check(model=str(model_cell.value), factory_number=str(number_cell.value))
                except RuntimeError as e:
                    raise Exception("СЕРВИС НЕ ДОСТУПЕН") from e

                match res:
                    case CheckResultEnum.FAILED:
                        state_cell.value = "НЕУСПЕШНО"
                        state_cell.fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
                    case CheckResultEnum.SUCCESS:
                        state_cell.value = "УСПЕШНО"
                        state_cell.fill = PatternFill(start_color="00FF00", end_color="00FF00", fill_type="solid")
                    case CheckResultEnum.ERROR:
                        state_cell.value = "ОШИБКА"
                        state_cell.fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

                wb.save("test.xlsx")
                await asyncio.sleep(0.5)
    finally:
        await checker.close()


if __name__ == "__main__":
    asyncio.run(main())
