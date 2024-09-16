// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt


//debug: se tiene que apretar varias veces save antes de que realmente se guarde

//GET CLIENTE, FECHA DE VENTA, PRODUCTOS, RFC Y REGIMEN FISCAL
frappe.ui.form.on('Factura', {
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
                    // console.log("#######r message#########")
                    // console.log(r.message);
                    if (r.message) {
                        frm.set_value('cliente', r.message.customer);
                        frm.set_value('fecha_nota_de_venta', r.message.posting_date);
                        frm.clear_table('factura_product_array')


                        r.message.items.forEach(function (item) {
                            var child = frm.add_child('factura_product_array');
                            child.producto = item.item_code;
                            child.descripcion = item.description;
                            child.cantidad = item.qty;
                            child.precio = item.rate;
                        });
                        frm.refresh_field('factura_product_array');
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
                                    frm.set_value('tax_id', s.message.tax_id);
                                    frm.set_value('tax_category', s.message.tax_category);
                                }
                            }
                        });
                    }
                }
            }),
            frappe.call({
                method: 'facturacion_mx.facturacion_mx.doctype.factura.api.get_metodo_de_pago',
                args: {
                    sales_invoice_id: frm.doc.sales_invoice_id
                },
                callback: function (t) {
                    if (t.message) {
                    // console.log("#######server script message#########");
                    // console.log(t.message);
                    frm.set_value('referencia_de_pago', t.message);
                    } else {
                    frm.set_value('referencia_de_pago', "No hay referencia de forma de pago")
                }
            }
            });
        }
    }
});

// GET COMPLETE ADDRESS
frappe.ui.form.on("Factura", "billing_address_invoice", function(frm, cdt, cdn) {
    if(frm.doc.billing_address_invoice){
      return frm.call({
      method: "frappe.contacts.doctype.address.address.get_address_display",
      args: {
         "address_dict": frm.doc.billing_address_invoice
      },
      callback: function(t) {
        if(t.message)
            frm.set_value("full_address", t.message);
      }
     });
    }
    else{
        frm.set_value("full_address", "SIN INFORMACION");
    }
});
