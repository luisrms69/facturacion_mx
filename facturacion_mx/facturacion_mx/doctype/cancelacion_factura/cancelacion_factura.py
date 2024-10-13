# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
# se importa para poder acceder al password
from frappe.utils.password import get_decrypted_password
from facturacion_mx.facturacion_mx.doctype.factura.api import *
from .api import *	#Para utilizar las funciones definidas en api de cancelacion factura
# from facturacion_mx.doctype.factura.api import *
from facturacion_mx.facturacion_mx.api import *

class CancelacionFactura(Document):
#Metodo para obtener el id de la factura que se va a cancelar, este es el ID proporcionado por el PAC   
	def get_factura_id(self):
		factura_id = frappe.db.get_value(
			"Cancelacion Factura", self.get_title(), 'id_pac'
		)

		return factura_id

#Metodo para evaluar si la respuesta del PAC es de exito o fracaso, en fracasos no hay id	
	# def determine_resultado(data_response):
	# 	if 'id' in data_response.keys():
	# 		return 1
	# 	else:
	# 		return 0

#Metodo que llama al metodo que añade en el child table de cancelar factura el response del PAC		
	def anadir_response_record(self,pac_response):	#refactor: esta lista debera estar en una variable para hacer un foreach o algo por el estilo
		if check_pac_response_success(pac_response) == 1:
			pac_response_json = pac_response.json()
			anade_response_record(self,pac_response_json)

#Metodo que evalua la respuesta obtenida y en base a esta avisa por medio de un mensaje el resultado
# Retorna ademas un valor de status que se utilizara para la actualizacion de los documentos		
	def actualizar_cancelacion_respuesta_pac(self, pac_response):  #refactor: esto se deberia poder mejorar, demasiado texto hardcoded
		if check_pac_response_success(pac_response) == 1:
			pac_response_json = pac_response.json()			
			status = status_respuesta_pac(pac_response_json)
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

# Metodo que jala el motivo de cancelacion introducido por el usuario
	def get_motivo_cancelacion(self):
		motivo_cancelacion = frappe.db.get_value(
			"Cancelacion Factura", self.get_title(), 'motivo_de_cancelacion'
		)
		id_motivo_cancelacion = frappe.db.get_value("Motivo de Cancelacion", motivo_cancelacion, 'motivo_de_cancelación')

		return id_motivo_cancelacion

# Metodo que se encarga de enviar a cancelar
# Primero determina los valores del query que se adicionaran al http request
# Posteriormente define los elementos del request headers y authorization
# Envía el request y con base en la respuesta actualiza el documento
# Si la cancelacion es exitosa tambien actualiza el status de la factura y el invoice
	def cancel_cfdi(self):
		factura_a_cancelar = self.get_factura_id()
		motivo_cancelacion = self.get_motivo_cancelacion()
		api_token = get_decrypted_password('Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
		headers ={ "Authorization": f"Bearer {api_token}"}
		factura_endpoint = frappe.db.get_single_value('Facturacion MX Settings', 'endpoint_cancelar_facturas')
		q = f"{factura_a_cancelar}?motive={motivo_cancelacion}"
		final_url= f"{factura_endpoint}/{q}"

		response = requests.delete(final_url, headers=headers)

		data_response =response.json()  #refactor:pareciera que no se usa

		status = self.actualizar_cancelacion_respuesta_pac(response)
		actualizar_status_cx_factura(self, status)
		self.anadir_response_record(response)

		if status == "Cancelacion Exitosa" :
			actualizar_status_factura_invoice(self.name)

# Se ejecuta el HOOK al dar click en Submit
	def on_submit(self):
		self.cancel_cfdi()

	# def on_update(self):
	# 	test_access()

