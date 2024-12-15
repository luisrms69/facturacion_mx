# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
# se importa para poder acceder al password
from frappe.utils.password import get_decrypted_password
# from facturacion_mx.facturacion_mx.doctype.factura.api import *
# from .api import *	#Para utilizar las funciones definidas en api de cancelacion factura
# from facturacion_mx.doctype.factura.api import *
from facturacion_mx.facturacion_mx.api import *

class CancelacionFactura(Document):

# Metodo que se encarga de enviar a cancelar
# Primero determina los valores del query que se adicionaran al http request
# Posteriormente define los elementos del request headers y authorization
# Envía el request y con base en la respuesta actualiza el documento
# Si la cancelacion es exitosa tambien actualiza el status de la factura y el invoice
	def cancel_cfdi(self):
		factura_a_cancelar = get_factura_id(self)
		motivo_cancelacion = get_motivo_cancelacion(self)
		api_token = get_decrypted_password('Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
		headers ={ "Authorization": f"Bearer {api_token}"}
		factura_endpoint = frappe.db.get_single_value('Facturacion MX Settings', 'endpoint_cancelar_facturas')
		q = f"{factura_a_cancelar}?motive={motivo_cancelacion}"
		final_url= f"{factura_endpoint}/{q}"

		response = requests.delete(final_url, headers=headers)

		data_response =response.json()  #refactor:pareciera que no se usa

		status = actualizar_cancelacion_respuesta_pac(self,response)
		# actualizar_status_cx_factura(self, status) #refactor: Se va a modificar el nombre a actualizar_status_doc
		actualizar_status_doc(self,status)

		if check_pac_response_success(response) ==1:
			table_respuestas = "respuestas"
			anade_response_record(table_respuestas, self,data_response)
		# self.anadir_response_record(response)

		if status == "Cancelacion Exitosa" :
			actualizar_status_factura_invoice(self.name)

# Se ejecuta el HOOK al dar click en Submit
	def on_submit(self):
		self.cancel_cfdi()

	# def on_update(self):
	# 	test_access()

