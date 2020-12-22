import json
import re
from PyPDF2 import PdfFileReader, PdfFileWriter
import slate3k as slate
import sys
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4


with open("description.json") as fd:
    description = json.load(fd)

starter_string = ["Wishing"]
description_list = description.keys()


class Order:
    def __init__(self, invoice, seller_address, main_string):
        self.invoice = invoice
        self.seller_address = seller_address
        self.main_string = main_string
        self.quantity: dict = self.get_information(main_string=self.main_string)
        self.is_single_key = self.is_single()

    def get_information(self, main_string):
        quantity_result = {}
        main_string = main_string.split("DescriptionUnitPriceQtyNetAmountTaxRateTaxTypeTaxAmountTotalAmount")[1]
        remain_string: str = main_string
        print(remain_string)

        for serial_number in range(1, 5):
            print(f"Check for serial number {serial_number}")

            # Check the starting element
            next_serial_check = False
            current_description = None

            demo = [(starter, asic) for asic in description_list for starter in starter_string]
            for starter, asic in demo:
                value = str(
                    serial_number) + starter + "[\w\.\W]{1,200}(₹\d*.\d\d\d*₹\d*.\d\d)?[^(₹\d*.\d\d\d*₹\d*.\d\d)]"
                print(value)

                result = re.search(value, remain_string)
                if result:
                    if asic not in result.group(0):
                        continue
                    print(result.group(0))
                    next_serial_check = True
                    current_description = asic
                    break

            if not next_serial_check:
                print("No need to find next iteration")
                print(f"Max serial number available is : {serial_number}")
                break

            remain_string = remain_string.split(current_description)[1].strip()
            output = re.search(r"[\w\.\W]{1,30}(₹\d*.\d\d)(\d*)(₹\d*.\d\d)", remain_string)
            print(f"Quantity  is {output.group(2)}")
            quantity_result[current_description] = output.group(2)
        return quantity_result

    def is_single(self):
        if len(self.quantity.keys()) != 1:
            return False

        single_key = list(self.quantity.keys())
        # print(single_key)
        single_key = single_key[0]

        if int(self.quantity[single_key]) != 1:
            return False

        if 'pack' in description[single_key]["ShortDescription"].lower():
            return False

        return single_key

    def get_invoice(self,value):
        buffer = BytesIO()

        # create a new PDF with Reportlab
        p = canvas.Canvas(buffer, pagesize=A4)
        p.drawString(80, 0, value)
        p.showPage()
        p.save()

        # move to the beginning of the StringIO buffer
        buffer.seek(0)
        newPdf = PdfFileReader(buffer)

        #######DEBUG NEW PDF created#############
        pdf1 = buffer.getvalue()
        open('pdf1.pdf', 'wb').write(pdf1)
        #########################################

        self.invoice.mergePage(newPdf.getPage(0))

        return self.invoice



if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description='Filter amazon pay slip')
    file_name = sys.argv[1]
    # print("This file name :",file_name)

    pdf_file = open(file_name, mode="rb")
    pdf = PdfFileReader(pdf_file)

    with open(file_name, 'rb') as f:
        extracted_text = slate.PDF(f)

    list_order = []
    for i in range(0, len(extracted_text), 2):
        print("Current i=", i)
        list_order.append(Order(seller_address=pdf.getPage(i), invoice=pdf.getPage(i + 1),
                                main_string=extracted_text[i + 1]))

    # Filter the result
    filter_result = {"mix": []}
    order: Order
    for order in list_order:
        print(order.is_single())
        print(order.quantity)

        if order.is_single():
            print("This part executed")
            if not filter_result.get(order.is_single_key):
                filter_result[order.is_single_key] = []

            order_list = filter_result.get(order.is_single_key)
            order_list.append(order)
        else:
            filter_result["mix"].append(order)

    print(filter_result)
    print(len(filter_result["mix"]))

    # Write to output file
    for key in filter_result:
        file_name = key + ".pdf"

        if key != "mix" and description[key].get("ShortDescription"):
            file_name = description[key].get("ShortDescription") + ".pdf"

        pdf_writer = PdfFileWriter()
        order: Order
        for index , order in enumerate(filter_result[key]):
            pdf_writer.addPage(order.seller_address)
            # pdf_writer.addPage(order.invoice)
            pdf_writer.addPage(order.get_invoice("Order no: {}".format(index + 1 )))

        with open(file_name, 'wb') as out:
            pdf_writer.write(out)
        print('Created: {}'.format(file_name))

    pdf_file.close()
