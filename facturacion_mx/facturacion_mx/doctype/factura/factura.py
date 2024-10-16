# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password
# from frappe.utils import validate_email_address
from facturacion_mx.facturacion_mx.api import *

class Factura(Document):
    
#Metodo para solicitar la creacion de una factura
    def create_cfdi(self):
#Primero solicita la definicion de variables del documento actual   
        current_document = self.get_title()
        sales_invoice_id = frappe.db.get_value(
            'Factura', current_document, 'sales_invoice_id')
        invoice_data = frappe.get_doc('Sales Invoice', sales_invoice_id)
        cliente = get_cliente(invoice_data)
        datos_direccion = get_datos_direccion_facturacion(cliente)
        tax_id = get_tax_id(cliente)
        email_id = datos_direccion.email_id

#Despues se arma el http request. endpoint, headers y data. Los valores de headers y endpoint se toman de settings
#Los valores de data se arman en este metodo, hacen llamadas a los metodos de la clase creada (Factura)
        facturapi_endpoint = frappe.db.get_single_value('Facturacion MX Settings','endpoint_crear_facturas')
        api_token = get_decrypted_password('Facturacion MX Settings','Facturacion MX Settings',"live_secret_key")
        headers = {"Authorization": f"Bearer {api_token}"}
        data = {
            "payment_form": frappe.db.get_value('Factura', current_document, 'foma_de_pago_sat')[:2],
            "use": frappe.db.get_value('Factura', current_document, 'usocfdi'),
            "payment_method": frappe.db.get_value('Factura', current_document, 'metodo_pago_sat')[:3],
            "customer": {
                "legal_name": cliente,
                "tax_id": tax_id,
                "tax_system": get_regimen_fiscal(cliente),
                "email": email_id,
                "address": {
                    "zip": datos_direccion.pincode
                },
            },
            "items": get_items_info(invoice_data)
        }

		#Cambia el estado de las notaas de venta a enviadas a PAC
        actualizar_status_sales_invoice(sales_invoice_id,"Enviado a PAC")

        response = requests.post(
            facturapi_endpoint, json=data, headers=headers)
        
        data_response =response.json()

        update_pac_response(self, response)
        
   #refactor: mucho codigo duplicado con factura global, cambien ombre variables en algunos casos
        if check_pac_response_success(response) == 1:
            sale_invoice_status = "Factura Normal"
            factura_status = "Facturado"
            aviso_message = "La Facturación fue exitosa"
            aviso_titulo = "Facturación Exitosa"
            aviso_color = "green"
        else:
            sale_invoice_status = "Sin facturar"
            factura_status = "Rechazada"
            aviso_message = str(data_response)
            aviso_titulo = "Hubo problema con la solicitud, revisa el reporte"
            aviso_color = "red"

        actualizar_status_sales_invoice(sales_invoice_id,sale_invoice_status)
        actualizar_status_doc(self, factura_status)
        despliega_aviso(title=aviso_titulo, msg=aviso_message, color=aviso_color)

#Metodo que se corre para validar si los campos son correctos        
    def validate(self):
        validate_rfc_factura(self.tax_id)
        validate_cp_factura(self.zip_code)
        validate_tax_category_factura(self.tax_category)
        validate_email_factura(self.email_id)

#Metodo que se corre al enviar (submit) solicitar creacion de la factura
    def on_submit(self):
        self.create_cfdi()
