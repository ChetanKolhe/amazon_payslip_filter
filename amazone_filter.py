import json
import re
import PyPDF2
import slate3k as slate
import argparse
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
        self.is_file_name_updated = False

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

    def get_invoice(self, value):
        buffer = BytesIO()

        page_description = f"{value}  ("
        for key in self.quantity:
            page_description = page_description + f"{description[key]['ShortDescription']}={self.quantity[key]},"

        page_description = page_description + ")"

        # create a new PDF with Reportlab
        p = canvas.Canvas(buffer, pagesize=A4)
        p.drawString(0, 2, page_description)
        p.showPage()
        p.save()

        # move to the beginning of the StringIO buffer
        buffer.seek(0)
        newPdf = PyPDF2.PdfFileReader(buffer)

        #######DEBUG NEW PDF created#############
        pdf1 = buffer.getvalue()
        open('pdf1.pdf', 'wb').write(pdf1)
        #########################################

        self.invoice.mergePage(newPdf.getPage(0))

        return self.invoice

    def get_shipping(self, value):
        buffer = BytesIO()

        page_description = f"{value}  ("
        for key in self.quantity:
            page_description = page_description + f"{description[key]['ShortDescription']}={self.quantity[key]}, "

        page_description = page_description + ")"

        # create a new PDF with Reportlab
        p = canvas.Canvas(buffer, pagesize=A4)
        p.drawString(0, 2, page_description)
        p.showPage()
        p.save()

        # move to the beginning of the StringIO buffer
        buffer.seek(0)
        newPdf = PyPDF2.PdfFileReader(buffer)

        #######DEBUG NEW PDF created#############
        pdf1 = buffer.getvalue()
        open('pdf1.pdf', 'wb').write(pdf1)
        #########################################

        self.seller_address.mergePage(newPdf.getPage(0))

        return self.seller_address

    @staticmethod
    def write_pdf_files(list_of_order: list, pdf_file_name, include_invoice=True, include_address=True):
        pdf_writer = PyPDF2.PdfFileWriter()
        order: Order
        for index, order in enumerate(list_of_order):
            # pdf_writer.addPage(order.seller_address)
            # pdf_writer.addPage(order.invoice)
            if not order.is_file_name_updated:
                if include_address:
                    pdf_writer.addPage(order.get_shipping("Order no: {}".format(index + 1)))

                if include_invoice:
                    pdf_writer.addPage(order.get_invoice("Order no: {}".format(index + 1)))
            order.is_file_name_updated = True

        with open(pdf_file_name, 'wb') as out:
            pdf_writer.write(out)
        print('Created: {}'.format(pdf_file_name))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Filter amazon pay slip')
    parser.add_argument("file_name",
                        help="Enter amazon file name")

    parser.add_argument("-f", "--filter",
                        help="Separate invoice and address yes/no",
                        default="no")

    # file_name = sys.argv[1]
    # file_name = "examle.pdf"
    args = parser.parse_args()
    file_name = args.file_name
    separate = True if args.filter.lower() == 'yes' else False

    # print("This file name :",file_name)

    pdf_file = open(file_name, mode="rb")
    pdf = PyPDF2.PdfFileReader(pdf_file)

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

        if separate:
            Order.write_pdf_files(list_of_order=filter_result[key],
                                  pdf_file_name=f"invoice_{file_name}",
                                  include_address=False)

            Order.write_pdf_files(list_of_order=filter_result[key],
                                  pdf_file_name=f"address_{file_name}",
                                  include_invoice=False)
        else:
            Order.write_pdf_files(list_of_order=filter_result[key],
                                  pdf_file_name=f"{file_name}")

    # Write all files in single file
    list_order_file = []
    for key in filter_result:
        list_order_file = list_order_file + filter_result[key]

    Order.write_pdf_files(list_of_order=list_order_file,
                          pdf_file_name="all_filter.pdf")

    pdf_file.close()
