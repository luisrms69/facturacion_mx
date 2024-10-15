# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from facturacion_mx.facturacion_mx.api import *

# import requests  # Se utiliza para hacer el http request
# from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password
# from frappe.utils import validate_email_address


class FacturaGlobal(Document):
   
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


		#Cambia el estado de las notaas de venta a enviadas a PAC
		cambia_status_invoice_list_global(invoice_list,"Enviado a PAC")

		response = requests.post(facturapi_endpoint, json=data, headers=headers)
		data_response =response.json()

		table_respuestas = "respuestas_del_pac"
		anade_response_record(table_respuestas, self,data_response)

		if check_pac_response_success(response) == 1:
			sale_invoice_status = "Factura Global"
			factura_global_status = "Facturado"
			aviso_message = "La Facturación fue exitosa, consulta los detalles en la tabla Respuesta del PAC"
			aviso_titulo = "Facturación Exitosa"
			aviso_color = "green"
		else:
			sale_invoice_status = "Sin facturar"
			factura_global_status = "Rechazada"
			aviso_message = str(data_response)
			aviso_titulo = "Hubo problema con la solicitud, revisa el reporte"
			aviso_color = "red"

		cambia_status_invoice_list_global(invoice_list, sale_invoice_status)
		actualizar_status_doc(self, factura_global_status)
		despliega_aviso(title=aviso_titulo, msg=aviso_message, color=aviso_color)


#Metodo que se corre para validar si los campos son correctos        
	def validate(self):
		validate_cliente_publico_en_general()
		msg_orden_fechas =  "La fecha inicial es posterior a la fecha final"
		validate_orden_fechas(self.fecha_inicial, self.fecha_final, msg_orden_fechas)
		msg_invoice_empty = "No existen notas de venta pendientes de facturación para el periodo seleccionado"
		validate_not_empty(self.notas_de_venta, msg_invoice_empty)


#Metodo que se corre al enviar (submit) solicitar creacion de la factura
	def on_submit(self):
		self.create_cfdi_global()


	# def on_update(self):
	# 	despliega_aviso(title="titulo", msg="test message red", color="red")
			# 	invoice_list_test = get_invoices_factura_global()
	# 	frappe.msgprint(str(invoice_list_test))
	# 	forma_pago_test = get_forma_de_pago_global(invoice_list_test)
	# 	validate_cliente_publico_en_general()
		


