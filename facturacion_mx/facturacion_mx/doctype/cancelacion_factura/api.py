# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password


# Metodo que se llaman en factura.js para obtener alguna forma de pago, en caso de que exista
# @frappe.whitelist()
def get_factura_object(factura_a_revisar):
        api_token = get_decrypted_password('Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
        headers ={ "Authorization": f"Bearer {api_token}"}
        factura_endpoint = frappe.db.get_single_value('Facturacion MX Settings', 'endpoint_obtener_facturas')
        final_url= f"{factura_endpoint}/{factura_a_revisar}"
        
        response = requests.get(final_url, headers=headers)
        
        data_response =response.json()

        return data_response
        

#refactor:fix:bug: este metodo lo estoy trayendo de cx facturas no puede estar duplicado		
def actualizar_cancelacion_respuesta_pac(pac_response):  #refactor: esto se deberia poder mejorar, demasiado texto hardcoded
    # if CancelacionFactura.determine_resultado(pac_response) == 1:
        message_status = str(pac_response['status'])
        message_cancellation_status = str(pac_response['cancellation_status'])
        if message_status == "canceled":
            status = "Cancelacion Exitosa"
        else:
            if message_status == "valid" and message_cancellation_status == "pending":
                status = "Cancelacion Requiere VoBo"
            else:
                status ="Desconocido"
        frappe.msgprint(
                msg=f"El estatus reportado por el PAC en la solicitud es: {message_status} y el estatus de cancelación es: {message_cancellation_status}",
                title='La solicitud de cancelación fue exitosa.',
                indicator='green')
    #     self.db_set({
    #     'status' : status
    # })
    # else:
    #     frappe.msgprint(
    #         msg=str(pac_response),
    #         title='La solicitud de facturacion no fue exitosa',
    #         indicator='red'
    #     )
    #     self.db_set({
    #     'status' : "Solicitud Rechazada",
    #     'mensaje_de_error' : pac_response['message']
    # })

        
@frappe.whitelist()
def status_check_cx_factura(factura_a_revisar):
        factura_object = get_factura_object(factura_a_revisar)
        actualizar_cancelacion_respuesta_pac(factura_object)

        # frappe.msgprint(str(factura_object))