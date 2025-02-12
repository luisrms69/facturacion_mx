# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


def execute():

    facturas = [
        "ACC-SINV-2025-00431","ACC-SINV-2025-00286","ACC-SINV-2025-00318","ACC-SINV-2025-00323","ACC-SINV-2025-00361","ACC-SINV-2025-00378","ACC-SINV-2025-00409","ACC-SINV-2025-00450","ACC-SINV-2025-00499","ACC-SINV-2025-00532","ACC-SINV-2025-00090","ACC-SINV-2025-00062","ACC-SINV-2025-00280","ACC-SINV-2025-00542"
        ]

    for factura in facturas:
        if frappe.db.exists("Sales Invoice", factura,):
            frappe.db.set_value("Sales Invoice", factura,
                          'custom_status_facturacion', "Sin Facturar")