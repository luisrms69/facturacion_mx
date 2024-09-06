// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

// frappe.ui.form.on("factura", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on('factura', {
    sales_invoice_id: function(frm) {
    if (frm.doc.sales_invoice_id) {
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: "Sales Invoice",
                filters: {
                    name: frm.doc.sales_invoice_id
                }
            },
            callback: function(r) {
                if (r.message) {
                    console.log("------------", r.message);
                    frm.set_value('cliente', r.message.customer);
                    frm.set_value('fecha_nota_de_venta', r.message.posting_date);
                    
                    frm.clear_table('factura_product_array');
                    
                    r.message.items.forEach(function(item) {
                        var child = frm.add_child('factura_product_array');
                        
                        child.producto = item.item_code;
                        child.descripcion = item.description;
                        child.cantidad = item.qty;
                        child.precio = item.rate;
                    });
                    
                    frm.refresh_field('factura_product_array');
                }
            }
        });
    }
    }
});
