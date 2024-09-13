# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests #Se utiliza para hacer el http request

import inspect

def whatis(message, backend=True, frontend=True):
	"""
	This function is using in debugging, and shows an object's value, type, and call stack.
	"""
	inspected_stack = inspect.stack()

	direct_caller = inspected_stack[1]
	direct_caller_linenum = direct_caller[2]

	parent_caller = inspected_stack[2]
	parent_caller_function = parent_caller[3]
	parent_caller_path = parent_caller[1]
	parent_caller_line = parent_caller[2]

	message_type = str(type(message)).replace('<', '').replace('>', '')
	msg = f"---> DEBUG (frappe.whatis)\n"
	msg += f"* Initiated on Line: {direct_caller_linenum}"
	msg += f"\n  * Value: {message}\n  * Type: {message_type}"
	msg += f"\n  * Caller: {parent_caller_function}"
	msg += f"\n  * Caller Path: {parent_caller_path}\n  * Caller Line: {parent_caller_line}\n"

	if backend:
		print(msg)
	if frontend:
		msg = msg.replace('\n', '<br>')
		frappe.msgprint(msg)





class Factura(Document):
    
     def get_product_key(item_code):
            product_key = frappe.db.get_value("Item", item_code, "product_key")
            return product_key
     
     def get_items_info(invoice_data):
          items_info = []
          for producto in invoice_data.items:
               detalle_item = {
                    'quantity' : producto.qty,
                    'product' : {
                         'description' : producto.item_name,
                         'product_key' : Factura.get_product_key(producto.item_code),
                         'price' : producto.rate
                    }
               }
               items_info.append(detalle_item)

          return items_info
     
     
     def create_cfdi(self):
          current_document = self.get_title()
          sales_invoice_id = frappe.db.get_value('Factura', current_document, 'sales_invoice_id' )
          invoice_data = frappe.get_doc('Sales Invoice', sales_invoice_id )
          items_info = Factura.get_items_info(invoice_data)

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
               "use" : frappe.db.get_value('Factura', current_document,'usocfdi'),
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
          response = requests.post(facturapi_endpoint,json=data,headers=headers)

          whatis(response)


                    
     def on_submit(self):
         self.create_cfdi()


