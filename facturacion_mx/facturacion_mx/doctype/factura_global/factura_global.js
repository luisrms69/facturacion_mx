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
                method: 'facturacion_mx.facturacion_mx.api.get_receipts_factura_global',
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
                            child.receipt = nota.name
                            child.cliente = nota.cliente;
                            child.fecha_nota_de_venta = nota.creation;
                            child.sales_invoice_id = nota.sales_invoice_id;
                            child.total = nota.total_factura;
                        });
                        frm.refresh_field('notas_de_venta');
                    }
                }
            })
        }
    }
});


//fix: esto esta duplicado debe corregirse, ya me dio un dolor de cabeza por que se borraban los datos corregidos
//fix: objeto de impuesto esta a mano
frappe.ui.form.on('Factura Global', {
    fecha_inicial: function (frm) {
        if (frm.doc.fecha_inicial) {
            frappe.call({
                method: 'facturacion_mx.facturacion_mx.api.get_receipts_factura_global',
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
                            // console.log(nota)
                            var child = frm.add_child('notas_de_venta');
                            child.receipt = nota.name
                            child.cliente = nota.cliente;
                            child.fecha_nota_de_venta = nota.creation;
                            child.sales_invoice_id = nota.sales_invoice_id;
                            child.total = nota.total_factura;
                            // child.objeto_de_impuesto = "02";
                        });
                        frm.refresh_field('notas_de_venta');
                    }
                }
            })
        }
    }
});