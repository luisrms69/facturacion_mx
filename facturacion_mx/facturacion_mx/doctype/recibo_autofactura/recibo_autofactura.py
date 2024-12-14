# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
# from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password
from facturacion_mx.facturacion_mx.api import *

class ReciboAutofactura(Document):
    
#Metodo para solicitar la creacion de un recibo (se puede utilizar para autofacturacion)
    def create_recibo(self):
# Arma http request. endpoint, headers y data.

        facturapi_endpoint = get_endpoint('endpoint_crear_recibo_autofactura')
        api_token = get_api_token_live()
        headers = {"Authorization": f"Bearer {api_token}"}
        data = payload_recibo_autofactura(self)

# Almacena respuesta y define el estatus
        response = requests.post(
            facturapi_endpoint, json=data, headers=headers)

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
        # refactor: en realidad lo unico que se requiere validar es payment_form y productos.

#Metodo que se corre al enviar (submit) solicitar creacion de la factura
    def on_submit(self):
        actualizar_status_sales_invoice(self.sales_invoice_id,"Enviado a PAC") # Enviado a Pac deberia esar en ENUM Global
        self.create_recibo()
