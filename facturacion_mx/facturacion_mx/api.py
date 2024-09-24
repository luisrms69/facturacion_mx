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

def get_filename_from_cd(cd):
        if not cd:
                return None
        fname = re.findall('filename=(.+)', cd)
        if len(fname) == 0:
                return None
        return fname[0]

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
        filename_dir = path + filename
        with open(filename_dir, 'wb') as file:
                file.write(response.content)


        # download(filename)
        

        # with open("/home/erpnext/frappe-bench/apps/facturacion_mx/archivo.xml", 'wb') as local_file:
        #       for chunk in response.iter_content(chunk_size=128):
        #              local_file.write(chunk)


# def download(name):
#         frappe.msgprint("entramos")
#         file = frappe.get_doc("File", name)
#         frappe.response.filename = file.file_name
#         frappe.response.filecontent = file.get_content()
#         frappe.msgprint("entramos")
#         frappe.response.type="download"
#         frappe.response.display_content_as = "attatchment"

        