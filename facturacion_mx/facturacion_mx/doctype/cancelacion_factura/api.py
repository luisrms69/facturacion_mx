# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password


# Metodo que se llaman en factura.js para obtener alguna forma de pago, en caso de que exista
# @frappe.whitelist()
def get_factura_object(factura_a_revisar):
        api_token = get_decrypted_password('Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
        headers ={ "Authorization": f"Bearer {api_token}"}
        factura_endpoint = frappe.db.get_single_value('Facturacion MX Settings', 'endpoint_obtener_facturas')
        final_url= f"{factura_endpoint}/{factura_a_revisar}"
        
        response = requests.get(final_url, headers=headers)
        
        data_response =response.json()

        return data_response
        
        
@frappe.whitelist()
def status_check_cx_factura(factura_a_revisar):
        factura_object = get_factura_object(factura_a_revisar)

        frappe.msgprint(str(factura_object))