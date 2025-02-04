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

class ComplementodePagoPPD(Document):
    def create_complemento(self):
        current_document = self.get_title()
        payment_entry_id = frappe.db.get_value(
            'Complemento de Pago PPD', current_document, 'entrada_de_pago_id')
        payment_data = frappe.get_doc('Payment Entry', payment_entry_id)
        cliente = payment_data.party_name
        datos_direccion = get_datos_direccion_facturacion(cliente)
        tax_id = get_tax_id(cliente)
        email_id = datos_direccion.email_id


# Pendiente configuración o automatización
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
