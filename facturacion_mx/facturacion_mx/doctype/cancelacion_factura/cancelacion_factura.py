# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
# se importa para poder acceder al password
from frappe.utils.password import get_decrypted_password


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
		
	def actualizar_cancelacion_respuesta_pac(self, pac_response):  #refactor: esto se deberia poder mejorar
		if CancelacionFactura.determine_resultado(pac_response) == 1:
			self.db_set({
            'id_cancelacion_pac': pac_response['id'],
            # 'uuid' : pac_response['uuid'],
            # 'url_de_verificación' : pac_response['verification_url'],
            # 'serie_de_la_factura' : pac_response['series'],
            # 'folio_de_factura' : pac_response['folio_number'],
            # 'fecha_timbrado' : pac_response['created_at'],  #refactor: no se trata de la fecha de timbrado es la fehca de emision
            # 'status' : pac_response['status'],
            'status' : "Cancelacion Exitosa"
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

		# frappe.msgprint(str(data_response))

		resultado = CancelacionFactura.determine_resultado(data_response)

		self.actualizar_cancelacion_respuesta_pac(data_response)

	def on_submit(self):
		self.cancel_cfdi()


	

    

    # def cancel_cfdi(self):
    #     factura_a_cancelar = self.get_factura_id()
    #     motivo_cancelacion = self.get_motivo_cancelacion()
    #     api_token = get_decrypted_password(
    #         'Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
    #     headers = {"Authorization": f"Bearer {api_token}"}
    #     facturapi_endpoint = frappe.db.get_single_value(
    #         'Facturacion MX Settings', 'endpoint_cancelar_facturas')
    #     query = f"{factura_a_cancelar}?motive={motivo_cancelacion}"
    #     final_url = f"{facturapi_endpoint}/{query}"
    #     response = requests.delete(final_url, headers=headers)

    #     data_response = response.json()

    #     frappe.msgprint(str(data_response))

    #     # frappe.msgprint(final_url)
    #     # return final_url

    # def on_submit(self):
    #     self.cancel_cfdi()

	    # def get_factura_id(self):
    #     factura_id = frappe.db.get_value(
    #         "Cancelacion Factura", self.get_title(), 'id_pac')

    #     return factura_id


	# def determine_status(data_response):
    #         if 'id' in data_response.keys:
    #                return 1
    #         else:
    #                return 0

    # def get_motivo_cancelacion(self):
    #     motivo_cancelacion = frappe.db.get_value(
    #         "Cancelacion Factura", self.get_title(), 'motivo_de_cancelacion')
    #     id_motivo_cancelacion = frappe.db.get_value(
    #         "Motivo de Cancelacion", motivo_cancelacion, 'motivo_de_cancelación')
    #     return id_motivo_cancelacion
