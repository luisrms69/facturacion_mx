# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password
# from frappe.utils import validate_email_address
from .api import *


class Factura(Document):

# refactor: facturado y rechazada son estados del documento, mejor en variable

#Se optiene el product key, este es un campo que se añade por medio de fixtures
    # def get_product_key(item_code):
    #     product_key = frappe.db.get_value("Item", item_code, "product_key")
    #     return product_key

# #Se obtienen los datos de producto, estan en un child table
#     def get_items_info(invoice_data):
#         items_info = []
#         for producto in invoice_data.items:
#             detalle_item = {
#                 'quantity': producto.qty,
#                 'product': {
#                     'description': producto.item_name,
#                     'product_key': Factura.get_product_key(producto.item_code),
#                     'price': producto.rate
#                 }
#             }
#             if not detalle_item['product']['product_key']:
#                 frappe.throw("Todos los productos deben tener un código SAT válido (product_key).  Añadir en los productos seleccionados")
#             items_info.append(detalle_item)

#         return items_info

# #Verifica si la respuesta fue exitosa, buscando la llave id en la respuesta
#     def check_pack_response_success(data_response):   #refactor: a lo mejor unir con el siguiente metodo
#         if 'id' in data_response.keys():
#             return 1
#         else:
#             return 0
    
#refactor: este codigo ya no tiene sentido asi, ya verificamos el status en el metodo anterior
#toma la respuesta y las llaves deseadas y la prepara para escritura en el documento
    def check_pac_response(data_response,keys):
        pac_response = {'status' : "Facturado" }
        for key in keys:
            if key in data_response.keys():
                pac_response[key] = data_response[key]
            else:
                pac_response = { 'status' : "Rechazada" }

        return pac_response

# #Verifica la longitud del RFC, doce o trece son correctos
#     def validate_rfc_factura(tax_id):  #feat: Puede mejorar para revisar si es compañia o individuo
#         if not tax_id:
#             frappe.throw("La empresa no tiene registrado RFC. Para incluirlo debes acceder a los datos del cliente en la pestaña de impuestos")

#         tax_id_lenght = len(tax_id)
#         if tax_id_lenght != 12:
#             if tax_id_lenght != 13:
#                 frappe.throw("RFC Incorrecto por favor verifícalo. Para modificar este dato debes acceder a los datos del cliente en la pestaña de impuestos")

# #Verfica que el codigo sea de 5 letras    
#     def validate_cp_factura(zip_code):
#         if len(zip_code) != 5:
#             frappe.throw("El código postal es incorrecto, debe contener 5 numeros. La correccion de esta información se realiza directamente en los datos del cliente, en la direccion primaria de facturación")

# #Verifica que el regimen fiscal este entre los numeros esperados y que no este vacía    
#     def validate_tax_category_factura(tax_category):
#         valor_inferior = 600
#         valor_superior = 627
#         if not tax_category:
#             frappe.throw("La empresa no tiene regimen fiscal seleccionado. Para incluirlo debes acceder a los datos del cliente en la pestaña de impuestos")
#         if not valor_inferior <= int(tax_category[:3]) <= valor_superior:
#             frappe.throw("El regimen fiscal no es correcto, debe iniciar con tres números entre el 601 y 626. Para modificar este dato debes acceder a los datos del cliente en la pestaña de impuestos")


# #Verifica que el correo electrónico no este vacío y su formato sea correcto
#     def validate_email_factura(email_id):
#         if not email_id:
#             frappe.throw("Se requiere capturar un correo electrónico para la dirección principal de facturación. La captura se realiza directamente en la sección de direcciones del cliente.")
#         validate_email_address(email_id)
#         # if not frappe.utils.validate_type(email_id, "email"):
#         #     frappe.throw("El correo electrónico proporcionado no es válido o no esta definido")


# refactor: deberia poder tener la info de los campos a actualizar en una lista como la funcion de check_pac
# Añade informacion en caso de exito al documento
    def update_pac_response(self,pac_response):
        self.db_set({
            'id_pac': pac_response['id'],
            'uuid' : pac_response['uuid'],
            'url_de_verificación' : pac_response['verification_url'],
            'serie_de_la_factura' : pac_response['series'],
            'folio_de_factura' : pac_response['folio_number'],
            'fecha_timbrado' : pac_response['created_at'],  #refactor: no se trata de la fecha de timbrado es la fehca de emision
            'status' : pac_response['status'],
            'monto_total' : pac_response['total']
        })

#Actualiza el sales invoice como facturado Normal
    def update_sales_invoice_status(sales_invoice_id):
        frappe.set_value('Sales Invoice', sales_invoice_id, 'custom_status_facturacion', "Factura Normal")
    
#Metodo para solicitar la creacion de una factura
    def create_cfdi(self):
#Primero solicita la definicion de variables del documento actual   
        current_document = self.get_title()
        sales_invoice_id = frappe.db.get_value(
            'Factura', current_document, 'sales_invoice_id')
        invoice_data = frappe.get_doc('Sales Invoice', sales_invoice_id)
        cliente = get_cliente(invoice_data)
        datos_direccion = get_datos_direccion_facturacion(cliente)
        tax_id = get_tax_id(cliente)
        email_id = datos_direccion.email_id

#Despues se arma el http request. endpoint, headers y data. Los valores de headers y endpoint se toman de settings
#Los valores de data se arman en este metodo, hacen llamadas a los metodos de la clase creada (Factura)
        facturapi_endpoint = frappe.db.get_single_value('Facturacion MX Settings','endpoint_crear_facturas')
        api_token = get_decrypted_password('Facturacion MX Settings','Facturacion MX Settings',"live_secret_key")
        headers = {"Authorization": f"Bearer {api_token}"}
        data = {
            "payment_form": frappe.db.get_value('Factura', current_document, 'foma_de_pago_sat')[:2],
            "use": frappe.db.get_value('Factura', current_document, 'usocfdi'),
            "payment_method": frappe.db.get_value('Factura', current_document, 'metodo_pago_sat')[:3],
            "customer": {
                "legal_name": cliente,
                "tax_id": tax_id,
                "tax_system": get_regimen_fiscal(cliente),
                "email": email_id,
                "address": {
                    "zip": datos_direccion.pincode
                },
            },
            "items": get_items_info(invoice_data)
        }

# La respuesta se almacena, se convierte a JSON y se verifica si fue exitosa o rechazada
#se avisa al usuario el resultado y se escribe en el documento dependiendo del resultado
# Si fue exitosa se marca en sales invoice com facturado
        response = requests.post(
            facturapi_endpoint, json=data, headers=headers)
        
        data_response =response.json()


        if check_pac_response_success(data_response) == 1:
            factura_pac_keys = ['id','uuid','verification_url','series','folio_number', 'created_at', 'total']
            pac_response = Factura.check_pac_response(data_response,factura_pac_keys)

            if pac_response['status'] == "Facturado":
                self.update_pac_response(pac_response)
                Factura.update_sales_invoice_status(sales_invoice_id)
                frappe.msgprint(
                    msg="La solicitud de facturación ha sido exittosa, puedes consultar los detalles de la confirmación proporcionados por el PAC en la parte inferior de este documento",
                    title='Solicitud exitosa!!',
                    indicator='green'             
                )
            else:
                self.db_set['status'] = "Rechazada" # refactor: no creo que sea necesario este else
        else:
            self.db_set({
                'status' : "Rechazada",
                'response_rechazada' : str(data_response)  #refactor: dejar en una sola seccion exito y fracaso
                         })
            frappe.msgprint(
                msg=str(data_response),
                title='La solicitud de facturacion no fue exitosa',
                indicator='red'
            )

#Metodo que se corre para validar si los campos son correctos        
    def validate(self):
        validate_rfc_factura(self.tax_id)
        validate_cp_factura(self.zip_code)
        validate_tax_category_factura(self.tax_category)
        validate_email_factura(self.email_id)

#Metodo que se corre al enviar (submit) solicitar creacion de la factura
    def on_submit(self):
        self.create_cfdi()
