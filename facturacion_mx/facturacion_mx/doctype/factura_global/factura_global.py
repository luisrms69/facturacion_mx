# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from facturacion_mx.facturacion_mx.api import *

# import requests  # Se utiliza para hacer el http request
# from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password
# from frappe.utils import validate_email_address
# from .api import *


class FacturaGlobal(Document):

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


# # refactor: deberia poder tener la info de los campos a actualizar en una lista como la funcion de check_pac
# # Añade informacion en caso de exito al documento
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
    
#Metodo para solicitar la creacion de una factura global
	def create_cfdi_global(self):
		current_document = self.get_title()
		fecha_inicial = frappe.db.get_value('Factura Global', current_document, 'fecha_inicial')
		fecha_final = frappe.db.get_value('Factura Global', current_document, 'fecha_final')
		invoice_list = get_invoices_factura_global(fecha_inicial,fecha_final)
		forma_de_pago = get_forma_de_pago_global(invoice_list)
		cliente = validate_cliente_publico_en_general()
		uso_cfdi_global = "S01"
		metodo_de_pago_cfdi_global = "PUE"
		regimen_fiscal_cfdi_global ="616"
		direccion_emisor = frappe.db.get_value('Factura Global', current_document, 'lugar_de_emision')
		datos_direccion = get_zipcode_email_from_address(direccion_emisor)
		tipo = "I"  #fix: Esto se debe definir en otro lugar
		currency = "MXN"  #fix: Esto se debe definir en otro lugar
		periodicity = frappe.db.get_value('Factura Global', current_document, 'periodicity')
		months = frappe.db.get_value('Factura Global', current_document, 'months')
		year = frappe.db.get_value('Factura Global', current_document, 'year')


#Despues se arma el http request. endpoint, headers y data. Los valores de headers y endpoint se toman de settings
#Los valores de data se arman en este metodo, hacen llamadas a los metodos de la clase creada (Factura)

		facturapi_endpoint = frappe.db.get_single_value('Facturacion MX Settings','endpoint_crear_facturas')
		api_token = get_decrypted_password('Facturacion MX Settings','Facturacion MX Settings',"live_secret_key")
		headers = {"Authorization": f"Bearer {api_token}"}
		data = {
            "payment_form": forma_de_pago[:2],
            "use": uso_cfdi_global,
            "payment_method": metodo_de_pago_cfdi_global,
			"type" : tipo,
			"global" : {
				"periodicity": periodicity,
				"months" : months,
				"year" : year
			},
            "customer": {
                "legal_name": cliente,
                "tax_id": get_tax_id(cliente),
                "tax_system": regimen_fiscal_cfdi_global,
                "email": datos_direccion.email_id,
                "address": {
                    "zip": datos_direccion.pincode
                },
            },
            "items": prepare_conceptos_cfdi_global(invoice_list)
        }


		frappe.msgprint(str(forma_de_pago))



		# response = requests.post(facturapi_endpoint, json=data, headers=headers)
		# 		self.anadir_response_record(response)

		# data_response =response.json()

		# status = self.actualizar_cancelacion_respuesta_pac(response)
		# actualizar_status_cx_factura(self, status)
		# self.anadir_response_record(response)

		# if status == "Cancelacion Exitosa" :
		# 	actualizar_status_factura_invoice(self.name)


# # La respuesta se almacena, se convierte a JSON y se verifica si fue exitosa o rechazada
# #se avisa al usuario el resultado y se escribe en el documento dependiendo del resultado
# # Si fue exitosa se marca en sales invoice com facturado
#         response = requests.post(
#             facturapi_endpoint, json=data, headers=headers)
        
#         data_response =response.json()


#         if check_pac_response_success(response) == 1:
#             factura_pac_keys = ['id','uuid','verification_url','series','folio_number', 'created_at', 'total']
#             pac_response = Factura.check_pac_response(data_response,factura_pac_keys)

#             if pac_response['status'] == "Facturado":
#                 self.update_pac_response(pac_response)
#                 Factura.update_sales_invoice_status(sales_invoice_id)
#                 frappe.msgprint(
#                     msg="La solicitud de facturación ha sido exittosa, puedes consultar los detalles de la confirmación proporcionados por el PAC en la parte inferior de este documento",
#                     title='Solicitud exitosa!!',
#                     indicator='green'             
#                 )
#             else:
#                 self.db_set['status'] = "Rechazada" # refactor: no creo que sea necesario este else
#         else:
#             self.db_set({
#                 'status' : "Rechazada",
#                 'response_rechazada' : str(data_response)  #refactor: dejar en una sola seccion exito y fracaso
#                          })
#             frappe.msgprint(
#                 msg=str(data_response),
#                 title='La solicitud de facturacion no fue exitosa',
#                 indicator='red'
#             )

#Metodo que se corre para validar si los campos son correctos        
	def validate(self):
		validate_cliente_publico_en_general()
		msg_invoice_empty = ("No existen notas de venta pendientes de facturación para el periodo seleccionado")
		validate_not_empty(self.notas_de_venta, msg_invoice_empty)


#Metodo que se corre al enviar (submit) solicitar creacion de la factura
	def on_update(self):
		self.create_cfdi_global()
	# def on_update(self):
	# 	invoice_list_test = get_invoices_factura_global()
	# 	frappe.msgprint(str(invoice_list_test))
	# 	forma_pago_test = get_forma_de_pago_global(invoice_list_test)
	# 	validate_cliente_publico_en_general()
		


