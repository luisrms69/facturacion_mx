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
            }),
            frappe.call({
                method: 'facturacion_mx.facturacion_mx.doctype.factura.api.get_forma_de_pago',
                args: {
                    sales_invoice_id: frm.doc.sales_invoice_id
                },
                callback: function (t) {
                    if (t.message) {
                    frm.set_value('forma_de_pago_registrada', t.message);
                    } else {
                    frm.set_value('forma_de_pago_registrada', "No hay referencia de forma de pago")
                }
            }
            });
        }
    }
});

