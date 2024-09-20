// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

//refactor:deberia poder llamar a la funcion con el dotted path
//refactor: debe tenerse el codigo hardocded en alguna variable

frappe.ui.form.on('Cancelacion Factura', {
	refresh: function(frm) {
        if (frm.doc.status == "Cancelacion Requiere VoBo"){
            frm.add_custom_button(__('Revisar Status Cancelacion'), function(){
                frappe.call({
                        method: 'facturacion_mx.facturacion_mx.doctype.cancelacion_factura.api.status_check_cx_factura',
                        args: {
                            id_cx_factura: frm.doc.id_pac,
                            factura_a_cancelar: frm.docname
                        },
                        callback: function (r) {
                            if (r.message) {
                            // console.log("#######server script message#########");
                            // console.log(r.message);
                            }
                        }
                    });
            });
        }
	}
});