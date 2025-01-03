# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
# se importa para poder acceder al password
from frappe.utils.password import get_decrypted_password
from frappe.utils import validate_email_address
from frappe.utils.response import *
import re  # fix: Se incluye por que venía en el metodo para obtener el nombre del archivo en descarga factura, no estoy seguro si se usa
import json  # lo cargo para utilizar json.loads
import ast
from frappe.utils import add_to_date # Funcion add_to_date para la fecha de creacion de e-receipts
import datetime
from frappe.utils import get_site_base_path


#  DEFINICION DE VARIABLES GLOBALES
    
receipt_object = {'id': 'id', 'created_at':'created_at', 'date':'date', 'expires_at':'expires_at', 'status':'status_receipt', 'self_invoice_url': 'self_invoice_url', 'total':'total', 'invoice':'invoice', 'key': 'key', 'folio_number': 'folio_number', 'branch':'branch'}
status_options_receipts = {"open" : "Abierto","canceled" : "Cancelado","invoiced_to_customer" : "Facturado","invoiced_globally": "Factura Global", "rechazado": "Solicitud Rechazada"}
status_options_sales_invoice = {"initial" : "Sin Facturar","open" : "E-Receipt","pending" : "Enviado a PAC","invoiced_to_customer" : "Autofactura","invoiced_globally": "Factura Global", "rechazado": "Solicitud Rechazada", "unknown":"Desconocido","canceled" : "Sin Facturar","valid" : "Facturado","draft": "Enviado a PAC"}
invoice_object = {'id': 'id', 'created_at':'created_at', 'date':'date','livemode':'livemode', 'status':'status', 'cancellation_status': 'cancellation_status', 'verification_url':'verification_url', 'type':'type', 'customer':'customer', 'total': 'total', 'uuid': 'uuid', 'folio_number':'folio_number', 'series':'series', 'external_id':'external_id', 'idempotency_key': 'idempotency_key', 'payment_form': 'payment_form', 'is_ready_to_stamp':'is_ready_to_stamp','currency': 'currency', 'exchange':'exchange','pdf_custom_section': 'pdf_custom_section', 'addenda':'addenda','stamp': 'stamp', 'use':'use','payment_method':'payment_method','export':'export'}
status_options_invoice = {"pending" : "Enviada a PAC","canceled" : "Cancelado","valid" : "Facturado","draft": "Borrador", "rechazado": "Solicitud Rechazada"}
cancellation_status_options_invoice = {"none" : "Sin Estado","pending" : "Pendiente o en Proceso","accepted" : "Solicitud Aprobada","rejected": "Solicitud de Cancelación Rechazada", "expired": "Solicitud Expiro"}
invoice_object_additionals = {'related_documents': 'related_documents', 'complements': 'complements','namespaces':'namespaces', 'payment_related_ids': 'payment_related_ids'}
# status_options_invoice_global = {"pending" : "Enviada a PAC","canceled" : "Cancelado","valid" : "Facturado","draft": "Borrador", "rechazado": "Solicitud Rechazada"}

# invoice object additionals on response: CFDI Version, 
# campos que no se pueden incluir siempre, debera haber un diccionario especial  yconformar los objectos acorde con el tipo de respeusta: namespaces, complements, related_documents, payment_related_ids


# Metodos de operaciones con matrices, listas, diccionarios

def get_dictionary_keys(dict):
    keys_list = []
    for key in dict.keys():
        keys_list.append(key)
        
    return keys_list

# Métodos que utilizan por los doctypes de facturacion_mx.
# Se agrupan por funcionalidades

# Se obtiene el nombre del cliente
def get_cliente(invoice_data):
    cliente = invoice_data.customer

    return cliente

# Obtiene todos los datos del cliente
def get_customer_data(cliente):
    customer_data = frappe.get_doc('Customer', cliente)

    return customer_data


# Obtiene el Rregimen fiscal, solo se regresan los primeros
# tres caracteres que son el numero (600 y tantos), es lo que utiliza el API
def get_regimen_fiscal(cliente):
    regimen_fiscal = get_customer_data(cliente).tax_category[:3]

    return regimen_fiscal


# Se obtiene la direccion del cliente, tiene que tener definida direccion primaria, la que tiene en la Constancia
# El regreso ya viene configurado para ser añadido al http request (data)

#refactor: evaluar juntar con el siguiente metodo, la opcion sería dividir esto en dos y la parte comun juntarla
def get_datos_direccion_facturacion(cliente):
    filters = [
        ["Dynamic Link", "link_doctype", "=", "Customer"],
        ["Dynamic Link", "link_name", "=", cliente],
        ["Address", "is_primary_address", "=", 1]
    ]
    company_address = frappe.get_all("Address", filters=filters)
    datos_direccion = frappe.db.get_value('Address', company_address, [
                                            'pincode', 'email_id'], as_dict=1)
    if datos_direccion == "":
        frappe.throw(
            "Hay un problema con la dirección de facturación registrada, revisa en la configuración del cliente, Direcciones y Contactos")

    return datos_direccion

def get_zipcode_email_from_address(address):
    datos_direccion = frappe.db.get_value('Address', address, [
                                            'pincode', 'email_id'], as_dict=1)
    if datos_direccion == "":
        frappe.throw(
            "Hay un problema con la dirección registrada, revisa en la configuración")

    return datos_direccion
     
# Utilizando los datos obtenidos del cliente, se obtiene el RFC
def get_tax_id(cliente):
    tax_id = get_customer_data(cliente).tax_id

    return tax_id


# Utilizando los datos obtenidos del cliente, se obtiene el uso CFDI
def get_uso_cfdi(cliente):
    uso_cfdi = frappe.db.get_value("Customer", cliente, "custom_uso_cfdi")

    return uso_cfdi


# Se optiene el product key, este es un campo que se añade por medio de fixtures
def get_product_key(item_code):
    product_key = frappe.db.get_value("Item", item_code, "product_key")
    return product_key

# Se obtienen los datos de impuestos

def get_invoice_tax(taxes):
     invoice_taxes = []
     for tax in taxes:
          tax_item = {
               'rate' : tax.rate/100,
               'type' : "IVA"  #fix:hardcoded
          }
          invoice_taxes.append(tax_item)

     return invoice_taxes

#refactor: no creo que se necesite dividir en dos el calculo del impuesto, tenia un error de funcion cuando no jalo, llamaba a get_tax_id
def get_tax_info(item_tax_rate,invoice_tax):
    product_taxes = []
    if item_tax_rate == "{}":
        product_taxes = invoice_tax
    else:
        dict_item_tax_rate = ast.literal_eval(item_tax_rate)
        keys = dict_item_tax_rate.keys()
        for key  in keys:
            product_tax = {
                'rate': dict_item_tax_rate.get(key)/100,
                'type': "IVA"  # fix: Hardcoded mejorar
            }
            product_taxes.append(product_tax)

    return product_taxes

# Se obtienen los datos de producto, estan en un child table


def get_items_info(invoice_data):
    items_info = []
    invoice_tax = get_invoice_tax(invoice_data.taxes)
    for producto in invoice_data.items:
        detalle_item = {
            'quantity': producto.qty,
            'discount': producto.discount_amount,
            'product': {
                'description': producto.item_name,
                'product_key': get_product_key(producto.item_code),
                'price': producto.net_rate,
                'tax_included': "false",
                # 'taxes' : get_tax_info(producto.item_tax_rate,invoice_tax),
                'taxes': [{
                     'rate': 0.16,
                     'type': "IVA"  # fix: Hardcoded mejorar
                     }],
                'unit_key': producto.uom.partition(" ")[0]
            }
        }
        if not detalle_item['product']['product_key']:
            frappe.throw(
                "Todos los productos deben tener un código SAT válido (product_key).  Añadir en los productos seleccionados")
        items_info.append(detalle_item)

    return items_info


def get_uuid_from_invoice(sales_invoice_id):
    #  factura = frappe.get_doc('Factura', sales_inovice_id)
    # factura = frappe.db.get_list('Factura',
    #                              filters = {
    #                                   'sales_invoice_id': sales_inovice_id,
    #                                   'status':status_options_invoice.get('valid')
    #                              })
    factura_id = frappe.db.get_value('Factura',{
         'sales_invoice_id': sales_invoice_id,
                                'status':status_options_invoice.get('valid')
                            }, 'name')

    if factura_id is None:
        frappe.throw("No se ha encontrado ninguna factura  con el numero de referencia, verifica que ya se haya elaborado la factura PPD por el pago que quieres facturar")
    else:
        factura = frappe.get_doc('Factura', factura_id)

    # frappe.msgprint(str(sales_inovice_id))
    # frappe.msgprint(str(factura))
    uuid = factura.response_pac[0].uuid

    # frappe.msgprint(str(uuid))

    return uuid

def get_payment_form(payment_data):
    valor_inferior = 1
    valor_superior = 99
    if payment_data.mode_of_payment is None:
        frappe.throw("El pago se capturo sin forma de pago,  este dato es necesario para facturar el complemento de pago PPD")
    else:
        payment_form = payment_data.mode_of_payment[:2]
        if not valor_inferior <= int(payment_form) <= valor_superior:
            frappe.throw("La forma de pago tiene un valor incorrecto, este dato es necesario para facturar el complemento de pago PPD")

    return payment_form

# Se obtienen los datos de producto, estan en un child table


def get_complements_info(payment_data):
    complements_info = []
    data = []
    # invoice_tax = get_invoice_tax(payment_data.taxes)
# fix: los datos no deben venir hardcoded
    # data = [{
    #      'payment_form': get_payment_form(payment_data),
    # }]
    for relateddocument in payment_data.references:       
         related_documents = [{
            'uuid' : get_uuid_from_invoice(relateddocument.reference_name),
            'amount' : relateddocument.allocated_amount,
            'taxes' : [{
                'base': relateddocument.allocated_amount,
                'type': "IVA",
                'rate': .16,
                'factor': "Tasa",
                'withholding': False
                }],
                'installment' : 1,
                'last_balance': relateddocument.allocated_amount + relateddocument.outstanding_amount,
                'taxability': "02"
         }]
        #  data.append(related_documents)
    data = [{
         'payment_form': get_payment_form(payment_data),
         'related_documents': related_documents,
         'currency': "MXN",
         'exchange': 1
    }]
    complements_info = [{
         'type': "pago",
         'data': data
    }]
    # complements_info.append(data)

    return complements_info


def prepare_conceptos_cfdi_global(invoice_list):
    clave_producto_servicio = "01010101"
    cantidad = 1
    clave_unidad = "ACT"
    descripcion = "Venta"
    taxability = "02" # fix: esto se debe definir en otro lugar
    tax_type ="IVA"  # fix: esto se debe definir en otro lugar
    tax_rate = 0.16  # fix: esto se debe definir en otro lugar
    items_info = []  #Se define como conceptos en la guia de CFDI
    for invoice in invoice_list:
        detalle_item = {
            'quantity': cantidad,
            'discount' : invoice.base_total - invoice.base_net_total,
            'product': {
                'description': descripcion,
                'product_key': clave_producto_servicio,
                'price': invoice.base_total,
                'unit_key': clave_unidad,
                'taxability' : taxability,
                'taxes':[
                     {
                          'type': tax_type,
                          'rate': tax_rate
                     }
                ]
            }
        }
        if not detalle_item['product']['product_key']:
            frappe.throw(
                "Todos los productos deben tener un código SAT válido (product_key).  Añadir en los productos seleccionados")
        items_info.append(detalle_item)

    return items_info

# Verifica si la respuesta fue exitosa, buscando la llave id en la respuesta
# refactor:fix: utilizar el metodo de abajo, corregir en Factura, CX Factura y Recibo


# refactor: a lo mejor unir con el siguiente metodo
def check_pac_response_success(data_response):
    if data_response.status_code == 200:
        return 1
    else:
        return 0


# Verifica la longitud del RFC, doce o trece son correctos
# feat: Puede mejorar para revisar si es compañia o individuo
def validate_rfc_factura(tax_id):
    if not tax_id:
        frappe.throw(
            "La empresa no tiene registrado RFC. Para incluirlo debes acceder a los datos del cliente en la pestaña de impuestos")

    tax_id_lenght = len(tax_id)
    if tax_id_lenght != 12:
        if tax_id_lenght != 13:
            frappe.throw(
                "RFC Incorrecto por favor verifícalo. Para modificar este dato debes acceder a los datos del cliente en la pestaña de impuestos")

# Verfica que el codigo sea de 5 letras


def validate_cp_factura(zip_code):
    if len(zip_code) != 5:
        frappe.throw("El código postal es incorrecto, debe contener 5 numeros. La correccion de esta información se realiza directamente en los datos del cliente, en la direccion primaria de facturación")

# Verifica que el regimen fiscal este entre los numeros esperados y que no este vacía


def validate_tax_category_factura(tax_category):
    valor_inferior = 600
    valor_superior = 627
    if not tax_category:
        frappe.throw(
            "La empresa no tiene regimen fiscal seleccionado. Para incluirlo debes acceder a los datos del cliente en la pestaña de impuestos")
    if not valor_inferior <= int(tax_category[:3]) <= valor_superior:
        frappe.throw("El regimen fiscal no es correcto, debe iniciar con tres números entre el 601 y 626. Para modificar este dato debes acceder a los datos del cliente en la pestaña de impuestos")


# Verifica que la empresa tiene definido CFDI

def validate_uso_cfid(uso_cfdi):
     if not uso_cfdi:
        frappe.throw(
            "La empresa no tiene registrado el Uso de CFDI para sus facturas. Para incluirlo debes acceder a los datos del cliente en la pestaña de impuestos")


# Verifica que la empresa tiene definido CFDI

def validate_api_secret_api_key(api_secret, api_key):
     if not api_secret or not api_key:
        frappe.throw(
            "Para descargar facturas se requiere definir un usuario API, este dato se captura en Factura MX Settings")


# Verifica que el correo electrónico no este vacío y su formato sea correcto
def validate_email_factura(email_id):
    if not email_id:
        frappe.throw("Se requiere capturar un correo electrónico para la dirección principal de facturación. La captura se realiza directamente en la sección de direcciones del cliente.")
    validate_email_address(email_id)

# Verifica que la informacion para generar la factura este completa y correcta
def validate_data_invoice(doc):
        validate_rfc_factura(doc.tax_id)
        validate_cp_factura(doc.zip_code)
        validate_tax_category_factura(doc.tax_category)
        validate_uso_cfid(doc.usocfdi)
        validate_email_factura(doc.email_id)


# Método que se usa para imprimir avisos, utiliza tres variables, el titulo, el mensaje y el color del indicador
def despliega_aviso(title="Aviso", msg="", color="green"):
     frappe.msgprint(title=title, msg=msg, indicator=color)
    

def get_endpoint(endpoint):
     endpoint_value = frappe.db.get_single_value('Facturacion MX Settings',endpoint)

     return endpoint_value

def get_api_token_live():
     api_token = get_decrypted_password('Facturacion MX Settings','Facturacion MX Settings',"live_secret_key")

     return api_token


# METODOS QUE SE TRAEN ORIGINALMENTE DE CX FACTURA API, ESTE SE ELIMINA.
# añado tambien los metodos que quedaban en CX Factura.py


#Metodo para obtener el id de la factura que se va a cancelar, este es el ID proporcionado por el PAC   
def get_factura_id(document):
    factura_id = document.response_pac[0].id

    return factura_id


# Método para preparar una respuesta negativa como object invoice (limitado) y que se pueda añadir a la tabla de respuestas
def objetizar_respuesta_negativa_pac(invoice_id, json_response):


     respuesta_negativa ={}
     respuesta_negativa[invoice_object.get('id')] = invoice_id
     respuesta_negativa[invoice_object.get('date')] = str(datetime.datetime.now())
     respuesta_negativa[invoice_object.get('cancellation_status')] = str(json_response)

     return respuesta_negativa


# Metodo que jala el motivo de cancelacion introducido por el usuario
def get_motivo_cancelacion(document):
    motivo_cancelacion = frappe.db.get_value(
        "Cancelacion Factura", document.get_title(), 'motivo_de_cancelacion'
    )
    id_motivo_cancelacion = frappe.db.get_value("Motivo de Cancelacion", motivo_cancelacion, 'motivo_de_cancelación')

    return id_motivo_cancelacion


def get_id_motivo_cancelacion(motivo):
    id_motivo_cancelacion = frappe.db.get_value("Motivo de Cancelacion", motivo, 'motivo_de_cancelación')

    return id_motivo_cancelacion


#Metodo que evalua la respuesta obtenida y en base a esta avisa por medio de un mensaje el resultado
# refactor: voy a duplicar esta funcion usada en CX para ver si puedo mejorarla
# Retorna ademas un valor de status que se utilizara para la actualizacion de los documentos		
def actualizar_cancelacion_respuesta_pac(document, pac_response):  #refactor: esto se deberia poder mejorar, demasiado texto hardcoded
    pac_response_json = pac_response.json()	
    if check_pac_response_success(pac_response) == 1:		
        status = status_respuesta_pac(pac_response_json)
    else:
        frappe.msgprint(str(pac_response_json))
        frappe.msgprint(
            msg=str(pac_response),
            title='La solicitud de facturacion no fue exitosa',
            indicator='red'
        )
        document.db_set({
        'mensaje_de_error' : pac_response_json['message']
    })
        status = "Solicitud Rechazada"
        
    return status


#refactor:fix: misma funcion para factura, factura global y e-receipt y cancelacion, en esta version tendresmos  versiones para cada uno, debe quedar una sola
def respuesta_pac(document, pac_response):
    
    pac_response_json = pac_response.json()	
    if check_pac_response_success(pac_response) == 1:		
        status = status_options_receipts.get(pac_response_json['status'])
        status_sales_invoice =  status_options_sales_invoice.get(pac_response_json['status'])
        title = 'Solicitud Exitosa!!!!!'
        message = "El recibo se ha generado exitosamente, puedes checar los detalles en este documento"
        indicator = "green"
    else:
        title = 'La solicitud de facturacion no fue exitosa'
        message = str(pac_response)
        indicator = "red"
        status = status_options_receipts.get("rechazado")
        status_sales_invoice = status_options_sales_invoice.get("initial")
        document.db_set({
        'mensaje_de_error' : pac_response_json['message']
    })

    despliega_aviso(title=title,msg=message,color=indicator)

    return status, status_sales_invoice


def respuesta_pac_cancelacion(document, pac_response):

    table_respuestas = "response_pac"
    
    pac_response_json = pac_response.json()	
    if check_pac_response_success(pac_response) == 1:		
        status = status_options_invoice.get(pac_response_json['status'])
        cancel_status = cancellation_status_options_invoice.get(pac_response_json.get(invoice_object['cancellation_status']))   #la bronca esta en la aplicacion del get, ya son muchas horas y me sigue dadno none
        # status_sales_invoice =  status_options_sales_invoice.get(pac_response_json['status'])
        # table_respuestas = "response_pac"
        add_response(table_respuestas,document,pac_response.json())
        title = 'Solicitud de Cancelación Recibida y Aceptada'
        # message = "El PAC ha respondido a la solicitud, puedes revisar el estado actual en la tabla de respuestas"
        message=f"El PAC ha aceptado la solicitud de cancelación, el estatus reportado es: {status} y el estado de cancelación es: {cancel_status}, considera que en algunos casos se requiere la validación por parte del cliente antes de la cancelación definitiva de la factura"
        indicator = "green"
        if status == status_options_invoice.get('canceled'):       
            actualizar_status_doc(document,status)
            actualizar_status_sales_invoice(document.sales_invoice_id,status_options_sales_invoice.get('initial'))
        else:      
            actualizar_status_doc(document,status_options_invoice.get('pending'))
            actualizar_status_sales_invoice(document.sales_invoice_id,status_options_sales_invoice.get('pending'))            
             
    else:
        title = 'La solicitud fue rechazada'
        message = str(pac_response_json)
        indicator = "red"
        actualizar_status_sales_invoice(document.sales_invoice_id,"Sin Facturar")

        
        registro_rechazo = objetizar_respuesta_negativa_pac(get_factura_id(document),pac_response_json)
        add_response(table_respuestas,document,registro_rechazo)


    despliega_aviso(title=title,msg=message,color=indicator)
        
    # return status, status_sales_invoice


def respuesta_pac_factura(document, pac_response):

    pac_response_json = pac_response.json()	
    if check_pac_response_success(pac_response) == 1:		
        status = status_options_invoice.get(pac_response_json['status'])
        status_sales_invoice =  status_options_sales_invoice.get(pac_response_json['status'])
        table_respuestas = "response_pac"
        add_response(table_respuestas,document,pac_response.json())
        title = 'Solicitud Exitosa!!!!!'
        message = "El PAC ha respondido a la solicitud, puedes revisar el estado actual en la tabla de respuestas"
        indicator = "green"
    else:
        title = 'La solicitud de facturacion no fue exitosa'
        message = str(pac_response_json)

# formar respuesta para añadir a table respuestas
        # add_response(table_respuestas,document,pac_response.json())


        indicator = "red"
        status = status_options_invoice.get("rechazado")
        status_sales_invoice = status_options_sales_invoice.get("initial")
        document.db_set({
        'response_rechazada' : pac_response_json['message']  #refactor:deberia poder usar la funcion add_error_message es un asunto de nombres de campos
    })

    despliega_aviso(title=title,msg=message,color=indicator)
        
    return status, status_sales_invoice

def respuesta_pac_factura_global(document, pac_response):
    
    pac_response_json = pac_response.json()	
    if check_pac_response_success(pac_response) == 1:		
        status = status_options_sales_invoice.get(pac_response_json['status'])
        status_sales_invoice =  status_options_sales_invoice.get(pac_response_json['status'])
        table_respuestas = "response_pac"
        add_response(table_respuestas,document,pac_response.json())
        title = 'Solicitud Exitosa!!!!!'
        message = "El PAC ha respondido a la solicitud, puedes revisar el estado actual en la tabla de respuestas, "
        indicator = "green"
    else:
        title = 'La solicitud de facturacion no fue exitosa'
        message = str(pac_response)
        indicator = "red"
        status = status_options_invoice.get("rechazado")
        status_sales_invoice = status_options_sales_invoice.get("initial")
        document.db_set({
        'response_rechazada' : pac_response_json['message']  #refactor:deberia poder usar la funcion add_error_message es un asunto de nombres de campos
    })

    despliega_aviso(title=title,msg=message,color=indicator)
        
    return status, status_sales_invoice

# Metodo para  obtern un objeto en forma de JSON de la factura
def get_factura_object(factura_a_revisar):
        api_token = get_decrypted_password(
            'Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
        headers = {"Authorization": f"Bearer {api_token}"}
        factura_endpoint = frappe.db.get_single_value(
            'Facturacion MX Settings', 'endpoint_obtener_facturas')
        final_url = f"{factura_endpoint}/{factura_a_revisar}"

        response = requests.get(final_url, headers=headers)

        data_response = response.json()

        return data_response

# Si la cancelacion es exitosa actualiza los status tanto de la factura como del invoice

def actualizar_status_factura_invoice(factura_cx):
      factura_a_cancelar = frappe.db.get_value(
          "Cancelacion Factura", factura_cx, 'factura_a_cancelar')
      frappe.db.set_value("Factura", factura_a_cancelar, 'status', "Cancelada")
      sales_invoice_Afectada = frappe.db.get_value(
          "Factura", factura_a_cancelar, 'sales_invoice_id')
      frappe.db.set_value("Sales Invoice", sales_invoice_Afectada,
                          'custom_status_facturacion', 'Sin Facturar')


# Verifica el status actual de la factura


def check_status_actual(status):
      if status == "Cancelacion Exitosa":
            return 1
      else:
            return 0

# fix: urge quitar hardcoded y ponerlo en variables, tanto aqui como con cx_factura (ENUM)
# Maneja el response obtenido del pac, realiza los avisos y regresa el valor status


# refactor: esto se deberia poder mejorar, demasiado texto hardcoded
def status_respuesta_pac(pac_response):
        message_status = str(pac_response['status'])
        message_cancellation_status = str(pac_response['cancellation_status'])
        if message_status == "canceled":
            status = "Cancelacion Exitosa"
        else:
            if message_status == "valid" and message_cancellation_status == "pending":
                status = "Cancelacion Requiere VoBo"
            else:
                status = "Desconocido"
        frappe.msgprint(
                msg=f"El estatus reportado por el PAC en la solicitud es: {message_status} y el estatus de cancelación es: {message_cancellation_status}",
                title='La solicitud de cancelación fue exitosa.',
                indicator='green')

        return status


# Actualiza el valor de status de la cancelacion de un docuemtno
def actualizar_status_doc(doc, status):
    doc.db_set({
         'status': status
      })


      # Actualiza el valor de status de la cancelacion de un docuemtno
def actualizar_status_cancelacion(doc, status):

      doc.db_set({
            'status': status
      })


# Método para actualizar el status de un documento
# fix: debe sustituir todos los metodos que traigo para actualizar status
#fix:debe utilizarse ENUM para los status posibles

def actualizar_status_sales_invoice(invoice, status):
           frappe.db.set_value("Sales Invoice", invoice,
                          'custom_status_facturacion', status)
           
def actualizar_status_payment_entry(payment_entry, status):
           frappe.db.set_value("Payment Entry", payment_entry,
                          'custom_status_payment_ppd', status)           

# refactor: no lo puedo ocupar porque los campos de mensaje de error son diferentes en factura y receipt
def add_error_response(document,response):
    pac_response = response.json()
    document.db_set({
         'mensaje_de_error' : pac_response['message']
    })


# Metodo que añade en el doctype cancelar factura en el childtable la respuesta obtenida del PAC

# fix: voy a duplicar esta funcion, la idea es que la primera desparezca y quede solo la inferior, por el momento esta no puede desarparecer porque se usa en CX factura
# refactor: esta lista debera estar en una variable para hacer un foreach o algo por el estilo
def anade_response_record(table_respuestas, doc, pac_response):
    doc.append(table_respuestas,
                {
                    'response_id': pac_response['id'],
                    'status_response': pac_response['status'],
                    'cancellation_status': pac_response['cancellation_status'],
                    'verification_url': pac_response['verification_url'],
                    'uuid': pac_response['uuid'],
                    'fecha_de_creacion': pac_response['created_at'],
                    'folio': pac_response['folio_number'],
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


def get_object_type(doc):
     document_type = doc.doctype

     match document_type:
          case "Factura":
               object_type = invoice_object
          case "Recibo Autofactura":
               object_type =receipt_object
          case "Complemento de Pago PPD":
               object_type = invoice_object

     return object_type



def add_response(table_respuestas, doc, pac_response):
    response_record = {}

    object_type = get_object_type(doc)

    for key in object_type:
         if key in pac_response.keys():  # REVIEW, SE CAMBIO EL 15 DICIEMBRE MEDIA NOCHE, POR SI DEJA DE JALAR REVISAR ESE COMMITT
                   response_record[object_type[key]] = pac_response[key]
         
    doc.append(table_respuestas, response_record)
    doc.save()


# Obtiene el nombre del archivo a partir de la response, content-disposition de los headers
def get_filename_from_cd(cd):
        if not cd:
                return None
        fname = re.findall('filename=(.+)', cd)
        if len(fname) == 0:
                return None
        return fname[0]

# Toma un string y devuelve los ultimos caracteres señalado


def presenta_ultimos_caracteres(str_var, caracteres):
        length = len(str_var)
        str_final = str_var[length - caracteres:]

        return str_final


# Toma un string y devuelve el mismo string eliminado caracteres antes y despues

def elimina_caracteres(str_var, al_principio):
    str_final = str_var[al_principio:]

    return str_final

# Graba el archivo de factura descargado y lo añade al documento Factura respectivo


def save_to_factura(document_name, filename_dir):
        # api_secret = '5b0504450091157'
        api_key = frappe.db.get_single_value(
            'Facturacion MX Settings', 'facturacion_user_key')
        api_secret = get_decrypted_password(
            'Facturacion MX Settings', 'Facturacion MX Settings', "facturacion_user_secret")

#feat: validate function para comprobar que existen estos campos, si no throw mensaje de que estan vacios
        validate_api_secret_api_key(api_secret, api_key)
        # api_key = 'd52ae25e20591f4'
        url = 'http://127.0.0.1:8000/api/method/upload_file'
        headers = {"Authorization": f"token {api_key}:{api_secret}",
                   'Accept': "application/json"
                #    'Content-Type': "pdf"
                   }
        files = {
                'file': open(filename_dir, 'rb'),
        }
        data = {
                'is_private': 1,
                'doctype': "Factura",
                'docname': document_name
        }
        response = requests.post(
            url=url, data=data, headers=headers, files=files)
        response.dict = json.loads(response.text)
        # frappe.msgprint(str(response.dict))
        # file_name = response.dict['message']['name']
        file_name = json.loads(response.text)['message']['name']

        frappe.errprint(response.__dict__)

        return file_name

# Metodo que se llaman en factura.js para descargar la factura


@frappe.whitelist()
def descarga_factura(document_name, format):

# Despues se arma el http request. endpoint, headers. Los valores de headers y endpoint se toman de settings
        current_document = get_factura_id(frappe.get_doc('Factura', document_name))

        factura_endpoint = frappe.db.get_single_value(
            'Facturacion MX Settings', 'endpoint_descarga_factura')
        # api_token = get_decrypted_password(
        #     'Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
        api_token = get_api_token_live()

        headers = {"Authorization": f"Bearer {api_token}"}

        final_url = f"{factura_endpoint}/{current_document}/{format}"

        response = requests.get(final_url, headers=headers)

# fix: no podemos dejar esto manual, se pierde en cada actualizacion
        # path = "/home/erpnext/frappe-bench/sites/llantascs.dev/private/files/"  # Se requiere crear por separado manualmente
        site_name_auto = elimina_caracteres(get_site_base_path(),2)
        path = f"/home/erpnext/frappe-bench/sites/{site_name_auto}/private/files/"
        # path = "/home/erpnext/frappe-bench/sites/llantascs.dev/private/files/"  # Se requiere crear por separado manualmente

        filename = get_filename_from_cd(
            response.headers.get('content-disposition'))[1:-1]
        filename_short = presenta_ultimos_caracteres(filename, 15)
        filename_dir = path + filename_short
        with open(filename_dir, 'wb') as file:
        #         # refactor: ver opcion señalada abajo para no ocupar tanto ram
                file.write(response.content)

        save_to_factura(document_name, filename_dir)

        # refactor option: con esto podemos disminuir el uso del ram
        # with open("/home/erpnext/frappe-bench/apps/facturacion_mx/archivo.xml", 'wb') as local_file:
        #       for chunk in response.iter_content(chunk_size=128):
        #              local_file.write(chunk)


# Metodo que se llaman en factura.js para obtener alguna forma de pago, en caso de que exista
@frappe.whitelist()
def get_forma_de_pago(sales_invoice_id):
    # Esto se ocupa cuando el pago se hizo por aparte, no en la misma compra
    filters = [
        ["Payment Entry Reference", "reference_doctype", "=", "Sales Invoice"],
        ["Payment Entry Reference", "reference_name", "=", sales_invoice_id]
    ]
    pay_entry = frappe.get_all("Payment Entry", filters=filters)

# Para casos donde haya cancelacioens de pagos o equivocaciones, tomara la ultima entrada
    if len(pay_entry) > 1:
         use_pay_entry = pay_entry[0]
    else:
         use_pay_entry = pay_entry
    
    forma_de_pago = frappe.db.get_value(
        "Payment Entry", use_pay_entry, "mode_of_payment")
    
    # Si el pago se hubiera hecho de manera simultanea, utilizando POS, entonces aqui se obtendria el dato
    if forma_de_pago is None:
         doc = frappe.get_doc('Sales Invoice', sales_invoice_id)
         forma_de_pago = doc.payments[0].mode_of_payment

    return forma_de_pago


# Metodo que se llaman en factura.js para enviar un correo de la factura
@frappe.whitelist()
def envia_factura_por_email(current_document, email_id):
# Primero solicita la definicion de variables del documento actual

# Despues se arma el http request. endpoint, headers y data. Los valores de headers y endpoint se toman de settings
# Los valores de data se arman en este metodo, hacen llamadas a los metodos de la clase creada (Factura)
        factura_id = get_factura_id(frappe.get_doc('Factura', current_document))
        
        factura_endpoint = frappe.db.get_single_value(
            'Facturacion MX Settings', 'endpoint_enviar_correo')
        api_token = get_decrypted_password(
            'Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
        headers = {"Authorization": f"Bearer {api_token}"}
        data = {
                "email": email_id
            }
        final_url = f"{factura_endpoint}/{factura_id}/email"

# La respuesta se muestra en la pantalla
        response = requests.post(
            final_url, json=data, headers=headers)

        data_response = response.json()

# refactor: Los textos no me gustan hardcoded,
        if check_pac_response_success(response) == 1:
                frappe.msgprint(
                    # refactor: Sería mejor que se incluyera el correo
                    msg="La información se envió al correo proporcionado",
                    title='Solicitud exitosa!!',
                    indicator='green'
                )
        else:
                frappe.msgprint(
                msg=str(data_response),
                title='No se envió el correo',
                indicator='red'
            )


# Metodo al que se llaman en JS para revisar cual es el status de la factura, se utiliza en aquellos
# casos donde la primer respuesta es que se requiere VOBO del cliente, se llama con un boton
# unicamente disponible para Cancelaciones en este status
@frappe.whitelist()
def status_check_cx_factura(id_cx_factura, factura_cx):
        factura_object = get_factura_object(id_cx_factura)
        status = actualizar_cancelacion_respuesta_pac(factura_object)
        doc = frappe.get_doc("Cancelacion Factura", factura_cx)
        anade_response_record(doc, factura_object)
        actualizar_status_cx_factura(doc, status)
        if check_status_actual == 1:
              actualizar_status_factura_invoice(factura_cx)




# Metodo para  obtern un objeto actualizado de un e-receipt
def get_receipt_object(recibo_a_revisar):
        api_token = get_decrypted_password(
            'Facturacion MX Settings', 'Facturacion MX Settings', "live_secret_key")
        headers = {"Authorization": f"Bearer {api_token}"}
        recibo_endpoint = frappe.db.get_single_value(
            'Facturacion MX Settings', 'endpoint_crear_recibo_autofactura')
        final_url = f"{recibo_endpoint}/{recibo_a_revisar}"

        response = requests.get(final_url, headers=headers)

        data_response = response.json()

        return data_response


# Metodo al que se llaman en JS para revisar cual es el status del recibo, se utiliza 
# para verificar si el cliente ya facturó o si todavía tiene pendiente hacerlo

@frappe.whitelist()
def status_check_receipt(id_receipt, receipt_docname):    
    # refactor: falta condición para asegurar que no hubo error
    receipt_object_update = get_receipt_object(id_receipt)
    status = status_options_receipts.get(receipt_object_update.get('status'))
    status_sales_invoice =status_options_sales_invoice.get(receipt_object_update.get('status'))

# refactor:lo estoy tomando todo de recibo_autofactura.py debe mejorarse
    table_respuestas = "respuestas_del_pac"
    doc = frappe.get_doc("Recibo Autofactura", receipt_docname)
    add_response(table_respuestas,doc,receipt_object_update)
    actualizar_status_doc(doc,status)
    actualizar_status_sales_invoice(doc.sales_invoice_id,status_sales_invoice)

    return

def payload_recibo_autofactura(doc):
        current_document = doc.get_title()
        sales_invoice_id = frappe.db.get_value(
            'Recibo Autofactura', current_document, 'sales_invoice_id')
        invoice_data = frappe.get_doc('Sales Invoice', sales_invoice_id)
        data = {
            "payment_form": frappe.db.get_value('Recibo Autofactura', current_document, 'forma_de_pago_registrada')[:2],
            "items": get_items_info(invoice_data),
            # "date" : str(add_to_date(str(invoice_data.posting_date), minutes=1))
            "date" : add_to_date(str(invoice_data.posting_date), minutes=15, as_string = True, as_datetime= True)
        }

        return data




def get_ereceipts_id_factura_global(recibo_autofactura_list):
    receipts_list = []
    for recibo in recibo_autofactura_list:
        #  frappe.msgprint(str(recibo))
         recibo_name = recibo.get('name')
         recibo_autofactura = frappe.get_doc("Recibo Autofactura", recibo_name)
         receipts_list.append(recibo_autofactura.respuestas_del_pac[0].id)

        #  frappe.msgprint(str(recibo_autofactura))

    # for renglon in receipts_list:
    #      frappe.msgprint(str(renglon))
    #      frappe.msgprint(renglon.created_at)
    #      frappe.msgprint(renglon.total)
    #      frappe.msgprint(renglon.status_receipt)
        
    return receipts_list


# Método para obtener la lista de notas de venta que se van a incluir en la factura global
# refactor: se necesita un ENUM para los estados de sales Invoice status facturacion
@frappe.whitelist()
def get_receipts_factura_global(fecha_inicial, fecha_final):
     recibo_autofactura_list = frappe.db.get_list('Recibo Autofactura', filters={
          'status': status_options_receipts.get("open"),
          'fecha_nota_de_venta': ['between',[fecha_inicial,fecha_final]],
          'cliente' : frappe.db.get_single_value('Facturacion MX Settings','cliente_factura_global')
          },
        fields = ['name', 'cliente', 'sales_invoice_id','creation','total_factura']  #fix: esto deber{ia estar en alguna variable}, hay dependencias en que name sea el indice cero
     )
     
    #  cliente_p_g = frappe.db.get_single_value('Facturacion MX Settings','cliente_factura_global')

    #  frappe.msgprint(cliente_p_g)
     frappe.msgprint(str(recibo_autofactura_list))

     return recibo_autofactura_list




def get_nota_mayor(invoice_id_list):
     nota_mayor = ""
     monto_nota_mayor = 0
     for nota_venta in invoice_id_list:
          grand_total = frappe.db.get_value("Sales Invoice", nota_venta, "grand_total")
          name = frappe.db.get_value("Sales Invoice", nota_venta, "name")
          if grand_total > monto_nota_mayor:
            monto_nota_mayor = grand_total
            nota_mayor = name
            
     return nota_mayor  


#Metodo que devuelve la forma de pago a utilizar, es la que se tiene en el monto mayor
def get_forma_de_pago_global(recibos_list):
     
#refactor: lo copio tal cual de ereceipts id hay que evitar el cuplicado, se tiene que hacer una funcion que tome el parametro que se da en get y regrese el listado fix fix fix fix
    receipts_invoice_id_list = []
    for recibo in recibos_list:
         recibo_sales_invoice_id = recibo.get('sales_invoice_id')
         receipts_invoice_id_list.append(recibo_sales_invoice_id)

    nota_mayor = get_nota_mayor(receipts_invoice_id_list)
    forma_de_pago = get_forma_de_pago(nota_mayor)

    return forma_de_pago


# Metodo que Verfica que se haya definido el usuario PUBLICO EN GENERAL de mnaera correcta


def validate_cliente_publico_en_general():
    msg_cliente_no_existe = "El cliente Público en General no ha sido definido o no ha sido asignado. Revisa que exista como cliente y que este dado de alta en la configuración de facturación"
    msg_rfc_incorrecto = "El RFC del cliente Público en General es incorrecto"
    rfc_correcto = "XAXX010101000"
    cliente_publico_general = frappe.db.get_single_value('Facturacion MX Settings', 'cliente_factura_global')
    datos_cliente_publico_general = frappe.get_doc('Customer', cliente_publico_general)
    if cliente_publico_general != "":
        tax_id= datos_cliente_publico_general.tax_id
        if tax_id != rfc_correcto:
             frappe.throw(msg_rfc_incorrecto)         
    else:
        frappe.throw(msg_cliente_no_existe)

    return cliente_publico_general


def validate_not_empty(variable, msg):
     if len(variable) == 0:
          frappe.throw(msg)


def validate_orden_fechas(fecha_inicial,fecha_final,msg):
     if (fecha_inicial > fecha_final):
          frappe.throw(msg)


def cambia_status_invoice_list_global(invoice_list, status):
    for invoice in invoice_list:
            actualizar_status_sales_invoice(invoice, status)


# Método para cancelar una factura

@frappe.whitelist()
def cancela_factura(doc, motivo):
    
    factura_document = frappe.get_doc('Factura', doc)
    factura_a_cancelar = get_factura_id(factura_document)
    api_token = get_api_token_live()

    headers ={ "Authorization": f"Bearer {api_token}"}
    factura_endpoint = frappe.db.get_single_value('Facturacion MX Settings', 'endpoint_cancelar_facturas')
    q = f"{factura_a_cancelar}?motive={motivo}"
    final_url= f"{factura_endpoint}{q}"
    
    response = requests.delete(final_url, headers=headers)
    
    respuesta_pac_cancelacion(factura_document, response)


    return response.json()
