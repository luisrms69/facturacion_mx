// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Factura Global", {
// 	refresh(frm) {

// 	},
// });


//fix: objeto de impuesto esta a mano
frappe.ui.form.on('Factura Global', {
    fecha_final: function (frm) {
        if (frm.doc.fecha_final) {
            frappe.call({
                method: 'facturacion_mx.facturacion_mx.api.get_invoices_factura_global',
                args: {
                    fecha_inicial : frm.doc.fecha_inicial,
                    fecha_final: frm.doc.fecha_final
                },
                callback: function (r) {
                    // console.log("#######r message#########")
                    // console.log(r.message);
                    if (r.message) {
                        // frm.set_value('fecha_nota_de_venta', r.message.posting_date);
                        frm.clear_table('notas_de_venta')
                        // console.log("#######inside r message#########")
                        // console.log(r.message);


                        r.message.forEach(function (nota) {
                            var child = frm.add_child('notas_de_venta');
                            child.sales_invoice_id = nota.name;
                            child.fecha_nota_de_venta = nota.posting_date;
                            child.valor_unitario = nota.base_total;
                            child.descuento = nota.base_total - nota.base_net_total;
                            child.objeto_de_impuesto = "02";
                        });
                        frm.refresh_field('notas_de_venta');
                    }
                }
            })
        }
    }
});


//fix: esto esta duplicado debe corregirse
//fix: objeto de impuesto esta a mano
frappe.ui.form.on('Factura Global', {
    fecha_inicial: function (frm) {
        if (frm.doc.fecha_inicial) {
            frappe.call({
                method: 'facturacion_mx.facturacion_mx.api.get_invoices_factura_global',
                args: {
                    fecha_inicial : frm.doc.fecha_inicial,
                    fecha_final: frm.doc.fecha_final
                },
                callback: function (r) {
                    // console.log("#######r message#########")
                    // console.log(r.message);
                    if (r.message) {
                        // frm.set_value('fecha_nota_de_venta', r.message.posting_date);
                        frm.clear_table('notas_de_venta')
                        // console.log("#######inside r message#########")
                        // console.log(r.message);


                        r.message.forEach(function (nota) {
                            var child = frm.add_child('notas_de_venta');
                            child.sales_invoice_id = nota.name;
                            child.fecha_nota_de_venta = nota.posting_date;
                            child.valor_unitario = nota.base_total;
                            child.descuento = nota.base_total - nota.base_net_total;
                            child.objeto_de_impuesto = "02";
                        });
                        frm.refresh_field('notas_de_venta');
                    }
                }
            })
        }
    }
});