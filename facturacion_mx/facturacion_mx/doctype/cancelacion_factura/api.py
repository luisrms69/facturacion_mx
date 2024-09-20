# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
# import requests  # Se utiliza para hacer el http request
# from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password


# Metodo que se llaman en factura.js para obtener alguna forma de pago, en caso de que exista
@frappe.whitelist()
def status_check_cx_factura():
    frappe.msgprint("dot path correcto")