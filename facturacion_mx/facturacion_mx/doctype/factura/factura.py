# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests #Se utiliza para hacer el http request



class Factura(Document):
    def create_cfdi(self):
          print("----inicia after submit---")
          print("inicia envio")
          current_document = self.get_title()
          print(current_document)
          sales_invoice_id = frappe.db.get_value('Factura', current_document, 'sales_invoice_id' )
          invoice_data = frappe.get_doc('Sales Invoice', sales_invoice_id )
          items_info = []
          for producto in invoice_data.items:
               detalle_item = {
                    'quantity' : producto.qty,
                    'product' : {
                         'description' : producto.item_name,
                         'product_key' : "25172503",
                         'price' : producto.rate
                    }
               }
               items_info.append(detalle_item)
          cliente = invoice_data.customer
          customer_data = frappe.get_doc('Customer', cliente )
          tax_id = customer_data.tax_id
          regimen_fiscal = customer_data.tax_category[:3]
          filters = [
               ["Dynamic Link", "link_doctype", "=", "Customer"],
               ["Dynamic Link", "link_name", "=", cliente],
               ["Address", "is_primary_address", "=", 1]
          ]
          company_address = frappe.get_all("Address", filters=filters)
          datos_direccion = frappe.db.get_value('Address', company_address,['pincode', 'email_id'], as_dict=1)
          filters = [
               ["Payment Entry Reference", "reference_doctype", "=", "Sales Invoice"],
               ["Payment Entry Reference", "reference_name", "=", sales_invoice_id]
          ]
          pay_entry = frappe.get_all("Payment Entry", filters=filters)
          metodo_de_pago = frappe.db.get_value("Payment Entry", pay_entry, "mode_of_payment")[:2]
          facturapi_endpoint = "https://www.facturapi.io/v2/invoices"
          api_token = "sk_test_rBbmpjK2Mq0oE8GXvx2Qe6E3blga45PnR9YkZOAJLQ"
          headers = {"Authorization": f"Bearer {api_token}"}
          data = {
               "payment_form" : metodo_de_pago,
               "use" : "S01",
               "customer" : {
                    "legal_name": cliente,
                    "tax_id": tax_id,
                    "tax_system": regimen_fiscal,
                    "email": datos_direccion.email_id,
                    "address": {
                         "zip": datos_direccion.pincode
                    },
               },
               "items": items_info               
          }
          #response = frappe.make_post_request(Facturapi_endpoint, json=data, headers=headers)
          response = requests.post(facturapi_endpoint,json=data,headers=headers)

          print("---termina envio---")
          

    def on_submit(self):
         print("-----entro en on submit???----")
         self.create_cfdi()
