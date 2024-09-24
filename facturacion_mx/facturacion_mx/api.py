# Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import requests  # Se utiliza para hacer el http request
from frappe.utils.password import get_decrypted_password #se importa para poder acceder al password
from frappe.utils import validate_email_address
from frappe.utils.response import *
import re #fix: Se incluye por que venía en el metodo para obtener el nombre del archivo en descarga factura, no estoy seguro si se usa
import json # lo cargo para utilizar json.loads



# Métodos que utilizan por los doctypes de facturacion_mx

#Se obtiene el nombre del cliente
def get_cliente(invoice_data):
    cliente = invoice_data.customer

    return cliente

#Obtiene todos los datos del cliente
def get_customer_data(cliente):
    customer_data = frappe.get_doc('Customer', cliente)

    return customer_data


#Utilizando los datos obtenidos del cliente, se obtiene el Rregimen fiscal, solo se regresan los primeros
#tres caracteres que son el numero (600 y tantos), es lo que utiliza el API
def get_regimen_fiscal(cliente):
    regimen_fiscal = get_customer_data(cliente).tax_category[:3]

    return regimen_fiscal



#Se obtiene la direccion del cliente, tiene que tener definida direccion primaria, la que tiene en la Constancia
#El regreso ya viene configurado para ser añadido al http request (data)
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
        frappe.throw("Hay un problema con la dirección de facturación registrada, revisa en la configuración del cliente, Direcciones y Contactos")

    return datos_direccion


#Utilizando los datos obtenidos del cliente, se obtiene el RFC
def get_tax_id(cliente):
    tax_id = get_customer_data(cliente).tax_id

    return tax_id



#Se optiene el product key, este es un campo que se añade por medio de fixtures
def get_product_key(item_code):
    product_key = frappe.db.get_value("Item", item_code, "product_key")
    return product_key

#Se obtienen los datos de producto, estan en un child table
def get_items_info(invoice_data):
    items_info = []
    for producto in invoice_data.items:
        detalle_item = {
            'quantity': producto.qty,
            'product': {
                'description': producto.item_name,
                'product_key': get_product_key(producto.item_code),
                'price': producto.rate
            }
        }
        if not detalle_item['product']['product_key']:
            frappe.throw("Todos los productos deben tener un código SAT válido (product_key).  Añadir en los productos seleccionados")
        items_info.append(detalle_item)

    return items_info

#Verifica si la respuesta fue exitosa, buscando la llave id en la respuesta
#refactor:fix: utilizar el metodo de abajo, corregir en Factura, CX Factura y Recibo
def check_pac_response_success(data_response):   #refactor: a lo mejor unir con el siguiente metodo
    if 'id' in data_response.keys():
        return 1
    else:
        return 0
    
#Verifica si la respuesta fue exitosa, buscando la llave id en la respuesta
def check_pac_response_success_keys(key, data_response):   #refactor: a lo mejor unir con el siguiente metodo
    if key in data_response.keys():
        return 1
    else:
        return 0


#Verifica la longitud del RFC, doce o trece son correctos
def validate_rfc_factura(tax_id):  #feat: Puede mejorar para revisar si es compañia o individuo
    if not tax_id:
        frappe.throw("La empresa no tiene registrado RFC. Para incluirlo debes acceder a los datos del cliente en la pestaña de impuestos")

    tax_id_lenght = len(tax_id)
    if tax_id_lenght != 12:
        if tax_id_lenght != 13:
            frappe.throw("RFC Incorrecto por favor verifícalo. Para modificar este dato debes acceder a los datos del cliente en la pestaña de impuestos")

#Verfica que el codigo sea de 5 letras    
def validate_cp_factura(zip_code):
    if len(zip_code) != 5:
        frappe.throw("El código postal es incorrecto, debe contener 5 numeros. La correccion de esta información se realiza directamente en los datos del cliente, en la direccion primaria de facturación")

#Verifica que el regimen fiscal este entre los numeros esperados y que no este vacía    
def validate_tax_category_factura(tax_category):
    valor_inferior = 600
    valor_superior = 627
    if not tax_category:
        frappe.throw("La empresa no tiene regimen fiscal seleccionado. Para incluirlo debes acceder a los datos del cliente en la pestaña de impuestos")
    if not valor_inferior <= int(tax_category[:3]) <= valor_superior:
        frappe.throw("El regimen fiscal no es correcto, debe iniciar con tres números entre el 601 y 626. Para modificar este dato debes acceder a los datos del cliente en la pestaña de impuestos")


#Verifica que el correo electrónico no este vacío y su formato sea correcto
def validate_email_factura(email_id):
    if not email_id:
        frappe.throw("Se requiere capturar un correo electrónico para la dirección principal de facturación. La captura se realiza directamente en la sección de direcciones del cliente.")
    validate_email_address(email_id)
    # if not frappe.utils.validate_type(email_id, "email"):
    #     frappe.throw("El correo electrónico proporcionado no es válido o no esta definido")

















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

# Graba el archivo de factura descargado y lo añade al documento Factura respectivo
def save_to_factura(document_name,filename_dir):
        api_secret='b93d45547b0fa48'
        api_key= '542c9e12488dca5'
        url = 'http://127.0.0.1:8000/api/method/upload_file'
        headers = {"Authorization": f"token {api_key}:{api_secret}",
                   'Accept': "application/json"
                #    'Content-Type': "pdf"
                   }
        files ={
                'file': open(filename_dir, 'rb'),
        }
        data = {
                'is_private': 1,
                'doctype': "Factura",
                'docname': document_name
        }
        response = requests.post(url=url, data=data, headers=headers, files=files)
        # response.dict = json.loads(response.text)

        # file_name = response.dict['message']['name']
        file_name = json.loads(response.text)['message']['name']
        frappe.errprint(response.__dict__)

        return file_name

# Metodo que se llaman en factura.js para descargar la factura
@frappe.whitelist()
def descarga_factura(document_name,current_document,format): 

#Despues se arma el http request. endpoint, headers. Los valores de headers y endpoint se toman de settings

        factura_endpoint = frappe.db.get_single_value('Facturacion MX Settings','endpoint_descarga_factura')
        api_token = get_decrypted_password('Facturacion MX Settings','Facturacion MX Settings',"live_secret_key")
        headers = {"Authorization": f"Bearer {api_token}"}

        final_url= f"{factura_endpoint}/{current_document}/{format}"

        response = requests.get(final_url, headers=headers)

        path="/home/erpnext/files/" #Se requiere crear por separado manualmente
        filename = get_filename_from_cd(response.headers.get('content-disposition'))[1:-1]
        filename_short = presenta_ultimos_caracteres(filename,15)
        filename_dir = path + filename_short
        with open(filename_dir, 'wb') as file:
                file.write(response.content)  #refactor: ver opcion señalada abajo para no ocupar tanto ram

        save_to_factura(document_name,filename_dir)
        
        # refactor option: con esto podemos disminuir el uso del ram
        # with open("/home/erpnext/frappe-bench/apps/facturacion_mx/archivo.xml", 'wb') as local_file:
        #       for chunk in response.iter_content(chunk_size=128):
        #              local_file.write(chunk)



# Metodo que se llaman en factura.js para obtener alguna forma de pago, en caso de que exista
@frappe.whitelist()
def get_forma_de_pago(sales_invoice_id):
    filters = [
        ["Payment Entry Reference", "reference_doctype", "=", "Sales Invoice"],
        ["Payment Entry Reference", "reference_name", "=", sales_invoice_id]
    ]
    pay_entry = frappe.get_all("Payment Entry", filters=filters)
    forma_de_pago = frappe.db.get_value(
        "Payment Entry", pay_entry, "mode_of_payment")

    return forma_de_pago



# Metodo que se llaman en factura.js para enviar un correo de la factura
@frappe.whitelist()
def envia_factura_por_email(current_document, email_id):
#Primero solicita la definicion de variables del documento actual   

#Despues se arma el http request. endpoint, headers y data. Los valores de headers y endpoint se toman de settings
#Los valores de data se arman en este metodo, hacen llamadas a los metodos de la clase creada (Factura)
        factura_endpoint = frappe.db.get_single_value('Facturacion MX Settings','endpoint_enviar_correo')
        api_token = get_decrypted_password('Facturacion MX Settings','Facturacion MX Settings',"live_secret_key")
        headers = {"Authorization": f"Bearer {api_token}"}
        data = {
                "email": email_id
            }
        final_url= f"{factura_endpoint}/{current_document}/email"

# La respuesta se muestra en la pantalla
        response = requests.post(
            final_url, json=data, headers=headers)
        
        data_response =response.json()

#refactor: Los textos no me gustan hardcoded,
        if check_pac_response_success_keys("ok",data_response) == 1:
                frappe.msgprint(
                    msg="La información se envió al correo proporcionado", #refactor: Sería mejor que se incluyera el correo
                    title='Solicitud exitosa!!',
                    indicator='green'             
                )
        else:
                frappe.msgprint(
                msg=str(data_response),
                title='No se envió el correo',
                indicator='red'
            )
