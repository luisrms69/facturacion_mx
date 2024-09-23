# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
# from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password
# from frappe.utils import validate_email_address

#fix: urge quitar hardcoded y ponerlo en variables, tanto aqui como con cx_factura (ENUM)
# Maneja el response obtenido del pac, realiza los avisos y regresa el valor status
def actualizar_recibo_respuesta_pac(pac_response):  #refactor: esto se deberia poder mejorar, demasiado texto hardcoded
        message_status = str(pac_response['status'])
        # message_cancellation_status = str(pac_response['cancellation_status'])
        if message_status == "open":
            status = "Emitido"
        else:
            if message_status == "canceled":
                status = "Cancelado"
            else:
                if message_status == "invoiced_to_customer":
                     status = "Autofacturado"
                else:
                     status ="Desconocido"
        frappe.msgprint(
                msg=f"El estatus reportado por el PAC en la solicitud es: {message_status}",
                title='La solicitud de emision del recibo de autofactura fue exitosa.',
                indicator='green')
        
        return status

#Metodo que añade en el doctype cancelar factura en el childtable la respuesta obtenida del PAC
def anade_recibo_response_record(doc,pac_response):	#refactor: esta lista debera estar en una variable para hacer un foreach o algo por el estilo
    doc.append("respuestas", 
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
    doc.save()