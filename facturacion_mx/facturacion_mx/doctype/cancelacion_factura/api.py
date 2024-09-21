# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password


def get_factura_object(factura_a_revisar):
        api_token = get_decrypted_password('Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
        headers ={ "Authorization": f"Bearer {api_token}"}
        factura_endpoint = frappe.db.get_single_value('Facturacion MX Settings', 'endpoint_obtener_facturas')
        final_url= f"{factura_endpoint}/{factura_a_revisar}"
        
        response = requests.get(final_url, headers=headers)
        
        data_response =response.json()

        return data_response
        

def actualizar_status_factura_invoice(factura_cx):
      factura_a_cancelar = frappe.db.get_value("Cancelacion Factura", factura_cx, 'factura_a_cancelar')
      frappe.db.set_value("Factura", factura_a_cancelar,'status',"Cancelada")
      sales_invoice_Afectada = frappe.db._get_value("Factura", factura_a_cancelar, 'sales_invoice_id')
      frappe.db.set_value("Sales Invoice", sales_invoice_Afectada,'status','Sin Facturar')


def check_status_actual(status)
      if status == "Cancelacion Exitosa":
            return 1
      else:
            return 0
      
#fix: urge quitar hardcoded y ponerlo en variables, tanto aqui como con cx_factura (ENUM)
def actualizar_cancelacion_respuesta_pac(pac_response):  #refactor: esto se deberia poder mejorar, demasiado texto hardcoded
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
        
        return status
        
def actualizar_status_cx_factura(doc, status):
      doc.db_set({
            'status' : status
      })


def anade_response_record(doc,pac_response):	#refactor: esta lista debera estar en una variable para hacer un foreach o algo por el estilo
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

        
@frappe.whitelist()
def status_check_cx_factura(id_cx_factura, factura_cx):
        factura_object = get_factura_object(id_cx_factura)
        status = actualizar_cancelacion_respuesta_pac(factura_object)
        doc = frappe.get_doc("Cancelacion Factura", factura_cx)
        anade_response_record(doc, factura_object)
        actualizar_status_cx_factura(doc,status)
        if check_status_actual == 1 :
              actualizar_status_factura_invoice(factura_cx)


