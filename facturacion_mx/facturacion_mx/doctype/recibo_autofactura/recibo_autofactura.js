// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Recibo Autofactura", {
// 	refresh(frm) {

// 	},
// });


frappe.ui.form.on('Recibo Autofactura', {
    sales_invoice_id: function (frm) {
        if (frm.doc.sales_invoice_id) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: "Sales Invoice",
                    filters: {
                        name: frm.doc.sales_invoice_id
                    }
                },
                callback: function (r) {
                    if (r.message) {
                        // frm.set_value('fecha_nota_de_venta', r.message.posting_date);
                        frm.clear_table('recibo_product_array')

                        // refactor: esto es igual a factura.js
                        r.message.items.forEach(function (item) {
                            var child = frm.add_child('recibo_product_array');
                            child.producto = item.item_code;
                            child.descripcion = item.description;
                            child.cantidad = item.qty;
                            child.precio = item.rate;
                        });
                        frm.refresh_field('recibo_product_array');
                        frappe.call({
                            method: 'frappe.client.get',
                            args: {
                                doctype: "Customer",
                                filters: {
                                    name: r.message.customer
                                }
                            },
                            callback: function (s) {
                                if (s.message) {
                                    frm.set_value('rfc', s.message.tax_id);
                                    // frm.set_value('tax_category', s.message.tax_category);
                                }
                            }
                        });
                    }
                }
            }), //refactor:duplicado con factura
            frappe.call({
                    method: 'facturacion_mx.facturacion_mx.api.get_forma_de_pago',
                args: {
                    sales_invoice_id: frm.doc.sales_invoice_id
                },
                callback: function (t) {
                    console.log(t.message)
                    if (t.message) {
                    frm.set_value('forma_de_pago_registrada', t.message);
                    } else {
                    frm.set_value('forma_de_pago_registrada', "No hay referencia de forma de pago");
                    frappe.msgprint("No existe registro de forma de pago, no es posible emitir recibo");
                }
            }
            });
        }
    }
});

//refactor:deberia poder llamar a la funcion con el dotted path
//refactor: debe tenerse el codigo hardocded en alguna variable

// Codigo que genera un boton en la forma Cancelacion Factura, unicamnete para los casos donde se requiere
//VOBO del cliente.  El boton llama a revisar el status actual y tomar las acciones reaultantes
frappe.ui.form.on('Recibo Autofactura', {
	refresh: function(frm) {
        if (frm.doc.status == "Abierto"){
            frm.add_custom_button(__('Actualizar Status Recibo'), function(){
                frappe.call({
                        method: 'facturacion_mx.facturacion_mx.api.status_check_receipt',
                        args: {
                            id_receipt: frm.doc.respuestas_del_pac[0].id,
                            receipt_docname: frm.docname
                        },
                        callback: function (r) {
                            if (r.message) {
                            // console.log("#######server script message#########");
                            // console.log(r.message);
                            }
                        }
                    });
            });
            frm.add_custom_button(__('Facturar Recibo'), function(){
                var openlink = window.open(frm.doc.respuestas_del_pac[0].self_invoice_url)
            });
        }
	}
});