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


def get_filename_from_cd(cd):
        if not cd:
                return None
        fname = re.findall('filename=(.+)', cd)
        if len(fname) == 0:
                return None
        return fname[0]

def presenta_ultimos_caracteres(str_var, caracteres):
        length = len(str_var)
        str_final = str_var[length - caracteres:]

        return str_final

def save_to_factura(filename_dir):
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
                'docname': "FACT-24-09-22-0272"
        }
        response = requests.post(url=url, data=data, headers=headers, files=files)
        # response.dict = json.loads(response.text)

        # file_name = response.dict['message']['name']
        file_name = json.loads(response.text)['message']['name']
        frappe.errprint(response.__dict__)

        return file_name

# Metodo que se llaman en factura.js para descargar la factura
@frappe.whitelist()
def descarga_factura(current_document,format): 

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

        save_to_factura(filename_dir)
        
        # refactor option: con esto podemos disminuir el uso del ram
        # with open("/home/erpnext/frappe-bench/apps/facturacion_mx/archivo.xml", 'wb') as local_file:
        #       for chunk in response.iter_content(chunk_size=128):
        #              local_file.write(chunk)




# @frappe.whitelist()
# def test_crud(filename_dir):
#         # frappe.msgprint("Testing CRUD") 
#         api_secret='b93d45547b0fa48'
#         api_key= '542c9e12488dca5'
#         url = 'http://127.0.0.1:8000/api/method/upload_file'
#         headers = {"Authorization": f"token {api_key}:{api_secret}",
#                    'Accept': "application/json"
#                 #    'Content-Type': "pdf"
#                    }
#         files ={
#                 'file': open(filename_dir, 'rb'),
#         }
#         response = requests.post(url=url, headers=headers, files=files)
#         # response.dict = json.loads(response.text)

#         # file_name = response.dict['message']['name']
#         file_name = json.loads(response.text)['message']['name']
#         # frappe.msgprint(file_name)

#         return file_name