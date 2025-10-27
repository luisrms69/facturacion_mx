# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password
from facturacion_mx.facturacion_mx.api import *
from datetime import datetime, timedelta


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_valid_payment_entries_for_ppd(doctype, txt, searchfield, start, page_len, filters):
    """
    Retorna Payment Entries válidos para Complemento de Pago PPD.

    Criterios de validación:
    1. Payment Entry en status 'Submitted' (docstatus=1)
    2. custom_status_payment_ppd = 'Sin Facturar'
    3. payment_type = 'Receive' (solo ingresos)
    4. TODAS las Sales Invoices relacionadas deben:
       - Tener custom_metodo_de_pago = 'PPD' (no NULL, no PUE)
       - Ser del año 2025 o posterior (posting_date >= 2025-01-01)
    5. Debe tener al menos una referencia a Sales Invoice
    """
    # Construir parámetros
    search_txt = f"%{txt}%" if txt else "%"

    # Query SQL que respeta todos los criterios
    return frappe.db.sql("""
        SELECT DISTINCT
            p.{key},
            p.posting_date,
            p.paid_amount
        FROM `tabPayment Entry` AS p
        WHERE p.custom_status_payment_ppd = 'Sin Facturar'
            AND p.docstatus = 1
            AND p.payment_type = 'Receive'
            AND (p.{key} LIKE %(txt)s OR p.posting_date LIKE %(txt)s)
            AND NOT EXISTS (
                SELECT 1
                FROM `tabPayment Entry Reference` AS per
                JOIN `tabSales Invoice` AS si ON per.reference_name = si.name
                WHERE per.parent = p.name
                    AND (
                        si.custom_metodo_de_pago IS NULL
                        OR si.custom_metodo_de_pago != 'PPD'
                        OR si.posting_date < '2025-01-01'
                    )
            )
            AND EXISTS (
                SELECT 1
                FROM `tabPayment Entry Reference` AS per2
                WHERE per2.parent = p.name
            )
        ORDER BY
            CASE WHEN p.{key} LIKE %(txt)s THEN 0 ELSE 1 END,
            p.posting_date DESC
        LIMIT %(page_len)s OFFSET %(start)s
    """.format(key=searchfield), {
        'txt': search_txt,
        'start': start or 0,
        'page_len': page_len or 20
    })


class ComplementodePagoPPD(Document):
    def create_complemento(self):
        current_document = self.get_title()
        payment_entry_id = frappe.db.get_value(
            'Complemento de Pago PPD', current_document, 'entrada_de_pago_id')
        payment_data = frappe.get_doc('Payment Entry', payment_entry_id)
        cliente = payment_data.party_name
        datos_direccion = get_datos_direccion_facturacion(cliente)
        tax_id = get_tax_id(cliente)

# refactor, pasar email id directo abajo y eliminar aqui
        email_id = datos_direccion.email_id


# Pendiente configuración o automatización
# refactor: eliminar type, poner P directamente abajo
        type = "P"
        payment_related_ids =[]

# Pendiente configuración de estos campos, NO SE VAN A OCUPAR, SE DEJA EL PLACER
        currency = "MXN"
        exchange = 1  # ESTO DEBERA CONFIGURARSE DE OTRA MANERA
        conditions = ""
        related_documents = []
        export = "01"
        complements = []
        status = "pending"
        # date = "" # ESTE CAMPO NO LO VOY A CONFIGURAR, EL DEFAULT ES NOW, ACTUALIZACION SI SE CONFIGURO
        address = {}
        external_id = ""
        idempotency_key = ""
        namespaces = []
        pdf_options = {}

        facturapi_endpoint = frappe.db.get_single_value('Facturacion MX Settings','endpoint_crear_facturas')
        api_token = get_api_token_live()
        headers = {"Authorization": f"Bearer {api_token}"}
        data = {
            "type": type,
            "customer": {
                "legal_name": cliente,
                "tax_id": tax_id,
                "tax_system": get_regimen_fiscal(cliente),
                "email": email_id,
                "address": {
                    "zip": datos_direccion.pincode
                },
            },
            "complements": get_complements_info(payment_data),
            "date": str(datetime.today()),
        }

        response = requests.post(
            facturapi_endpoint, json=data, headers=headers)

        status_doc , status_payment_entry = respuesta_pac_complemento(self, response)

        actualizar_status_doc(self,status_doc)
        actualizar_status_payment_entry(self.entrada_de_pago_id,status_payment_entry)
 
#Metodo que se corre para validar si los campos son correctos
# refactor: si es lo mismo en receipts, crear funcion que agrupe todo   
    def validate(self):
     pass


#Metodo que se corre al enviar (submit) solicitar creacion de la factura
    def on_submit(self):
        self.create_complemento()
