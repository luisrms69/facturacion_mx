# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password

from facturacion_mx.facturacion_mx.api import *
# from facturacion_mx.doctype.factura.api import *
from .api import *


class ReciboAutofactura(Document):
    
# #refactor: este codigo ya no tiene sentido asi, ya verificamos el status en el metodo anterior
# #toma la respuesta y las llaves deseadas y la prepara para escritura en el documento
#     def check_pac_response(data_response,keys):
#         pac_response = {'status' : "Facturado" }
#         for key in keys:
#             if key in data_response.keys():
#                 pac_response[key] = data_response[key]
#             else:
#                 pac_response = { 'status' : "Rechazada" }

#         return pac_response


# refactor: deberia poder tener la info de los campos a actualizar en una lista como la funcion de check_pac
# Añade informacion en caso de exito al documento
#     def update_pac_response(self,pac_response):
#         self.db_set({
#             'id_pac': pac_response['id'],
#             'uuid' : pac_response['uuid'],
#             'url_de_verificación' : pac_response['verification_url'],
#             'serie_de_la_factura' : pac_response['series'],
#             'folio_de_factura' : pac_response['folio_number'],
#             'fecha_timbrado' : pac_response['created_at'],  #refactor: no se trata de la fecha de timbrado es la fehca de emision
#             'status' : pac_response['status'],
#             'monto_total' : pac_response['total']
#         })

# #Actualiza el sales invoice como facturado Normal
#     def update_sales_invoice_status(sales_invoice_id):
#         frappe.set_value('Sales Invoice', sales_invoice_id, 'custom_status_facturacion', "Factura Normal")
    

    
#Metodo para solicitar la creacion de un recibo (se puede utilizar para autofacturacion)
    def create_recibo(self):
#Primero solicita la definicion de variables del documento actual   
        current_document = self.get_title()
        sales_invoice_id = frappe.db.get_value(
            'Recibo Autofactura', current_document, 'sales_invoice_id')
        invoice_data = frappe.get_doc('Sales Invoice', sales_invoice_id)
        cliente = get_cliente(invoice_data)
        datos_direccion = get_datos_direccion_facturacion(cliente)
        tax_id = get_tax_id(cliente)
        email_id = datos_direccion.email_id

#Despues se arma el http request. endpoint, headers y data. Los valores de headers y endpoint se toman de settings
#Los valores de data se arman en este metodo, hacen llamadas a los metodos de la clase creada (Factura)
        facturapi_endpoint = frappe.db.get_single_value('Facturacion MX Settings','endpoint_crear_recibo_autofactura')
        api_token = get_decrypted_password('Facturacion MX Settings','Facturacion MX Settings',"live_secret_key")
        headers = {"Authorization": f"Bearer {api_token}"}
        data = {
            "payment_form": frappe.db.get_value('Recibo Autofactura', current_document, 'forma_de_pago_registrada')[:2],
            "items": get_items_info(invoice_data)
        }

# La respuesta se almacena, se convierte a JSON y se verifica si fue exitosa o rechazada
#se avisa al usuario el resultado y se escribe en el documento dependiendo del resultado

        response = requests.post(
            facturapi_endpoint, json=data, headers=headers)
        
        data_response =response.json()

#Metodo que se corre para validar si los campos son correctos        
    def validate(self):
        validate_rfc_factura(self.rfc)
        validate_cp_factura(self.cp)

#Metodo que se corre al enviar (submit) solicitar creacion de la factura
    def on_submit(self):
        self.create_recibo()
