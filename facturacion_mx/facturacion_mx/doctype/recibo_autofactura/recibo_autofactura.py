# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password
from facturacion_mx.facturacion_mx.api import *

class ReciboAutofactura(Document):
    
#Metodo para solicitar la creacion de un recibo (se puede utilizar para autofacturacion)
    def create_recibo(self):
        current_document = self.get_title()
        sales_invoice_id = frappe.db.get_value(
            'Recibo Autofactura', current_document, 'sales_invoice_id')
        invoice_data = frappe.get_doc('Sales Invoice', sales_invoice_id)
        # cliente = get_cliente(invoice_data)
        # status_options_receipts = {"open" : "Abierto","canceled" : "Cancelado","invoiced_to_customer" : "Facturado","invoiced_globally": "Factura Global", "rechazado": "Solicitud Rechazada"} # OJO ESTE DEBE SER GLOBAL

# Arma http request. endpoint, headers y data.

        facturapi_endpoint = frappe.db.get_single_value('Facturacion MX Settings','endpoint_crear_recibo_autofactura')
        api_token = get_decrypted_password('Facturacion MX Settings','Facturacion MX Settings',"live_secret_key")
        headers = {"Authorization": f"Bearer {api_token}"}
        data = {
            "payment_form": frappe.db.get_value('Recibo Autofactura', current_document, 'forma_de_pago_registrada')[:2],
            "items": get_items_info(invoice_data)
        }

# Almacena respuesta y define el estatus
        response = requests.post(
            facturapi_endpoint, json=data, headers=headers)
        
        # data_response =response.json()

        status , status_sales_invoice = respuesta_pac(self,response)
        actualizar_status_doc(self,status)
        actualizar_status_sales_invoice(self.sales_invoice_id, status_sales_invoice)
        
        if check_pac_response_success(response) ==1:
            table_respuestas = "respuestas_del_pac"
            add_response(table_respuestas, self,response.json())

#Metodo que se corre para validar si los campos son correctos        
    def validate(self):
        validate_rfc_factura(self.rfc)
        validate_cp_factura(self.cp)

#Metodo que se corre al enviar (submit) solicitar creacion de la factura
    def on_submit(self):
        actualizar_status_sales_invoice(self.sales_invoice_id,"Enviado a PAC") # Enviado a Pac deberia esar en ENUM Global
        self.create_recibo()
