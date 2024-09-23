# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password


# Metodo que se llaman en factura.js para obtener alguna forma de pago, en caso de que exista
@frappe.whitelist()
def get_forma_de_pago(sales_invoice_id):
    filters = [
        ["Payment Entry Reference", "reference_doctype", "=", "Sales Invoice"],
        ["Payment Entry Reference", "reference_name", "=", sales_invoice_id]
    ]
    pay_entry = frappe.get_all("Payment Entry", filters=filters)
    forma_de_pago = frappe.db.get_value(
        "Payment Entry", pay_entry, "mode_of_payment")

    return forma_de_pago

# Métodos que utilizan factura.py y reciboatofactura.py (de entrada esos dos, pero puende ser mas)

#Se obtiene el nombre del cliente
def get_cliente(invoice_data):
    cliente = invoice_data.customer

    return cliente

#Obtiene todos los datos del cliente
def get_customer_data(cliente):
    customer_data = frappe.get_doc('Customer', cliente)

    return customer_data


#Utilizando los datos obtenidos del cliente, se obtiene el Rregimen fiscal, solo se regresan los primeros
#tres caracteres que son el numero (600 y tantos), es lo que utiliza el API
def get_regimen_fiscal(cliente):
    regimen_fiscal = get_customer_data(cliente).tax_category[:3]

    return regimen_fiscal



#Se obtiene la direccion del cliente, tiene que tener definida direccion primaria, la que tiene en la Constancia
#El regreso ya viene configurado para ser añadido al http request (data)
def get_datos_direccion_facturacion(cliente):
    filters = [
        ["Dynamic Link", "link_doctype", "=", "Customer"],
        ["Dynamic Link", "link_name", "=", cliente],
        ["Address", "is_primary_address", "=", 1]
    ]
    company_address = frappe.get_all("Address", filters=filters)
    datos_direccion = frappe.db.get_value('Address', company_address, [
                                            'pincode', 'email_id'], as_dict=1)
    if datos_direccion == "":
        frappe.throw("Hay un problema con la dirección de facturación registrada, revisa en la configuración del cliente, Direcciones y Contactos")

    return datos_direccion


#Utilizando los datos obtenidos del cliente, se obtiene el RFC
def get_tax_id(cliente):
    tax_id = get_customer_data(cliente).tax_id

    return tax_id



#Se optiene el product key, este es un campo que se añade por medio de fixtures
def get_product_key(item_code):
    product_key = frappe.db.get_value("Item", item_code, "product_key")
    return product_key

#Se obtienen los datos de producto, estan en un child table
def get_items_info(invoice_data):
    items_info = []
    for producto in invoice_data.items:
        detalle_item = {
            'quantity': producto.qty,
            'product': {
                'description': producto.item_name,
                'product_key': get_product_key(producto.item_code),
                'price': producto.rate
            }
        }
        if not detalle_item['product']['product_key']:
            frappe.throw("Todos los productos deben tener un código SAT válido (product_key).  Añadir en los productos seleccionados")
        items_info.append(detalle_item)

    return items_info
