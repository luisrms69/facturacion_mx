# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
# se importa para poder acceder al password
from frappe.utils.password import get_decrypted_password
from .api import test_access, actualizar_cancelacion_respuesta_pac	#Para utilizar las funciones definidas en api de cancelacion factura


class CancelacionFactura(Document):
    
	def get_factura_id(self):
		factura_id = frappe.db.get_value(
			"Cancelacion Factura", self.get_title(), 'id_pac'
		)

		return factura_id
	
	def determine_resultado(data_response):
		if 'id' in data_response.keys():
			return 1
		else:
			return 0
		
	def anade_response_record(self,pac_response):	#refactor: esta lista debera estar en una variable para hacer un foreach o algo por el estilo
		if CancelacionFactura.determine_resultado(pac_response) == 1:
			self.append("respuestas", 
					{
						'response_id': pac_response['id'],
						'status_response' : pac_response['status'],
						'cancellation_status' : pac_response['cancellation_status'],
						'verification_url' : pac_response['verification_url'],
						'uuid' : pac_response['uuid'],
						'fecha_de_creacion' : pac_response['created_at'],
						'folio' : pac_response['folio_number'],
						'serie_de_facturacion': pac_response['series'],
						'monto_total': pac_response['total'],
						'forma_de_pago': pac_response['payment_form'],
						'id_del_cliente': pac_response['customer']['id'],
						'nombre_del_cliente': pac_response['customer']['legal_name'],
						'rfc': pac_response['customer']['tax_id'],
						'signature': pac_response['stamp']['signature'],
						'fecha_de_sellado': pac_response['stamp']['date'],
						'numero_de_certificado_sat': pac_response['stamp']['sat_cert_number'],
						'firma_sat': pac_response['stamp']['signature']
						})
			self.save()

		
	def actualizar_cancelacion_respuesta_pac(self, pac_response):  #refactor: esto se deberia poder mejorar, demasiado texto hardcoded
		if CancelacionFactura.determine_resultado(pac_response) == 1:
			actualizar_cancelacion_respuesta_pac(pac_response)
			# test_access()
			# message_status = str(pac_response['status'])
			# message_cancellation_status = str(pac_response['cancellation_status'])
			# if message_status == "canceled":
			# 	status = "Cancelacion Exitosa"
			# else:
			# 	if message_status == "valid" and message_cancellation_status == "pending":
			# 		status = "Cancelacion Requiere VoBo"
			# 	else:
			# 		status ="Desconocido"
			# frappe.msgprint(
			# 		msg=f"El estatus reportado por el PAC en la solicitud es: {message_status} y el estatus de cancelación es: {message_cancellation_status}",
			# 		title='La solicitud de cancelación fue exitosa.',
			# 		indicator='green')
			self.db_set({
			'status' : "Cancelacion Requiere VoBo"
        })
		else:
			frappe.msgprint(
                msg=str(pac_response),
                title='La solicitud de facturacion no fue exitosa',
                indicator='red'
			)
			self.db_set({
			'status' : "Solicitud Rechazada",
            'mensaje_de_error' : pac_response['message']
        })


	def get_motivo_cancelacion(self):
		motivo_cancelacion = frappe.db.get_value(
			"Cancelacion Factura", self.get_title(), 'motivo_de_cancelacion'
		)
		id_motivo_cancelacion = frappe.db.get_value("Motivo de Cancelacion", motivo_cancelacion, 'motivo_de_cancelación')

		return id_motivo_cancelacion
	
	def cancel_cfdi(self):
		factura_a_cancelar = self.get_factura_id()
		motivo_cancelacion = self.get_motivo_cancelacion()
		api_token = get_decrypted_password('Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
		headers ={ "Authorization": f"Bearer {api_token}"}
		factura_endpoint = frappe.db.get_single_value('Facturacion MX Settings', 'endpoint_cancelar_facturas')
		q = f"{factura_a_cancelar}?motive={motivo_cancelacion}"
		final_url= f"{factura_endpoint}/{q}"

		response = requests.delete(final_url, headers=headers)

		data_response =response.json()

		# resultado = CancelacionFactura.determine_resultado(data_response) #AL PARECER NO SE USA

		self.actualizar_cancelacion_respuesta_pac(data_response)
		self.anade_response_record(data_response)



	def on_submit(self):
		self.cancel_cfdi()
			#OJO OJO  OJO MOVER A CANCEL_CFDI UNA VEZ PROBADA

	# def on_update(self):
	# 	test_access()

