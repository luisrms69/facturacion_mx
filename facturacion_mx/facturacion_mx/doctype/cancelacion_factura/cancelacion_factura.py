# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
# se importa para poder acceder al password
from frappe.utils.password import get_decrypted_password
from .api import actualizar_cancelacion_respuesta_pac, actualizar_status_cx_factura, anade_response_record, actualizar_status_factura_invoice	#Para utilizar las funciones definidas en api de cancelacion factura


class CancelacionFactura(Document):
#    
	def get_factura_cx_id(self):
		factura_id = frappe.db.get_value(
			"Cancelacion Factura", self.get_title(), 'id_pac'
		)

		return factura_id
	
	def determine_resultado(data_response):
		if 'id' in data_response.keys():
			return 1
		else:
			return 0
		
	def anadir_response_record(self,pac_response):	#refactor: esta lista debera estar en una variable para hacer un foreach o algo por el estilo
		if CancelacionFactura.determine_resultado(pac_response) == 1:
			anade_response_record(self,pac_response)

		
	def actualizar_cancelacion_respuesta_pac(self, pac_response):  #refactor: esto se deberia poder mejorar, demasiado texto hardcoded
		if CancelacionFactura.determine_resultado(pac_response) == 1:
			status = actualizar_cancelacion_respuesta_pac(pac_response)
		else:
			frappe.msgprint(
                msg=str(pac_response),
                title='La solicitud de facturacion no fue exitosa',
                indicator='red'
			)
			self.db_set({
            'mensaje_de_error' : pac_response['message']
        })
			status = "Solicitud Rechazada"
			
		return status


	def get_motivo_cancelacion(self):
		motivo_cancelacion = frappe.db.get_value(
			"Cancelacion Factura", self.get_title(), 'motivo_de_cancelacion'
		)
		id_motivo_cancelacion = frappe.db.get_value("Motivo de Cancelacion", motivo_cancelacion, 'motivo_de_cancelación')

		return id_motivo_cancelacion
	
	def cancel_cfdi(self):
		factura_a_cancelar = self.get_factura_cx_id()
		motivo_cancelacion = self.get_motivo_cancelacion()
		api_token = get_decrypted_password('Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
		headers ={ "Authorization": f"Bearer {api_token}"}
		factura_endpoint = frappe.db.get_single_value('Facturacion MX Settings', 'endpoint_cancelar_facturas')
		q = f"{factura_a_cancelar}?motive={motivo_cancelacion}"
		final_url= f"{factura_endpoint}/{q}"

		response = requests.delete(final_url, headers=headers)

		data_response =response.json()

		status = self.actualizar_cancelacion_respuesta_pac(data_response)
		actualizar_status_cx_factura(self, status)
		self.anadir_response_record(data_response)

		if status == "Cancelacion Exitosa" :
			actualizar_status_factura_invoice(self.name)


	def on_submit(self):
		self.cancel_cfdi()

	# def on_update(self):
	# 	test_access()

