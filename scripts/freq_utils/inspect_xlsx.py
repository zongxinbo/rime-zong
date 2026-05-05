import openpyxl
import sys

def inspect_xlsx(filename):
    wb = openpyxl.load_workbook(filename, data_only=True)
    sheet = wb.active
    print(f"Sheet Name: {sheet.title}")
    for i, row in enumerate(sheet.iter_rows(max_row=20, values_only=True)):
        print(f"Row {i}: {row}")

if __name__ == "__main__":
    inspect_xlsx('schemas/frequency/北京语言大学25亿字语料汉字字频表.xlsx')
