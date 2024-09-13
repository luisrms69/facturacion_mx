# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password


class Factura(Document):

    def get_product_key(item_code):
        product_key = frappe.db.get_value("Item", item_code, "product_key")
        return product_key

    def get_items_info(invoice_data):
        items_info = []
        for producto in invoice_data.items:
            detalle_item = {
                'quantity': producto.qty,
                'product': {
                    'description': producto.item_name,
                    'product_key': Factura.get_product_key(producto.item_code),
                    'price': producto.rate
                }
            }
            items_info.append(detalle_item)

        return items_info

    def get_cliente(invoice_data):
        cliente = invoice_data.customer

        return cliente

    def get_customer_data(cliente):
        customer_data = frappe.get_doc('Customer', cliente)

        return customer_data

    def get_tax_id(cliente):
        tax_id = Factura.get_customer_data(cliente).tax_id

        return tax_id

    def get_regimen_fiscal(cliente):
        regimen_fiscal = Factura.get_customer_data(cliente).tax_category[:3]

        return regimen_fiscal

    def get_datos_direccion_facturacion(cliente):
        filters = [
            ["Dynamic Link", "link_doctype", "=", "Customer"],
            ["Dynamic Link", "link_name", "=", cliente],
            ["Address", "is_primary_address", "=", 1]
        ]
        company_address = frappe.get_all("Address", filters=filters)
        datos_direccion = frappe.db.get_value('Address', company_address, [
                                              'pincode', 'email_id'], as_dict=1)

        return datos_direccion

    def get_metodo_de_pago(sales_invoice_id):
        filters = [
            ["Payment Entry Reference", "reference_doctype", "=", "Sales Invoice"],
            ["Payment Entry Reference", "reference_name", "=", sales_invoice_id]
        ]
        pay_entry = frappe.get_all("Payment Entry", filters=filters)
        metodo_de_pago = frappe.db.get_value(
            "Payment Entry", pay_entry, "mode_of_payment")[:2]

        return metodo_de_pago

    def create_cfdi(self):
        current_document = self.get_title()
        sales_invoice_id = frappe.db.get_value(
            'Factura', current_document, 'sales_invoice_id')
        invoice_data = frappe.get_doc('Sales Invoice', sales_invoice_id)
        cliente = Factura.get_cliente(invoice_data)
        datos_direccion = Factura.get_datos_direccion_facturacion(cliente)

        facturapi_endpoint = frappe.db.get_single_value('Facturacion MX Settings','endpoint_crear_facturas')
     # facturapi_endpoint = "https://www.facturapi.io/v2/invoices"
     #   api_token = frappe.db.get_single_value('Facturacion MX Settings','live_secret_key')
    #    api_token = "sk_test_rBbmpjK2Mq0oE8GXvx2Qe6E3blga45PnR9YkZOAJLQ"
    #    facturacion_settings = frappe.get_doc('Facturacion MX Settings')
        api_token = get_decrypted_password('Facturacion MX Settings','Facturacion MX Settings',"live_secret_key")
        headers = {"Authorization": f"Bearer {api_token}"}
        data = {
            "payment_form": Factura.get_metodo_de_pago(sales_invoice_id),
            "use": frappe.db.get_value('Factura', current_document, 'usocfdi'),
            "customer": {
                "legal_name": cliente,
                "tax_id": Factura.get_tax_id(cliente),
                "tax_system": Factura.get_regimen_fiscal(cliente),
                "email": datos_direccion.email_id,
                "address": {
                    "zip": datos_direccion.pincode
                },
            },
            "items": Factura.get_items_info(invoice_data)
        }
        response = requests.post(
            facturapi_endpoint, json=data, headers=headers)

    def on_submit(self):
        self.create_cfdi()
