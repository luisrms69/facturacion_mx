// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt


//debug: se tiene que apretar varias veces save antes de que realmente se guarde

//GET FECHA DE VENTA, PRODUCTOS, RFC Y REGIMEN FISCAL
// Se hace una llamada al metod client.get utilizando como entrada el sales_invoice_id capturado
// El callback se utiliza para definir la fecha de venta, los productos, el RFC y el regimen fiscal
// Para los productos se tiene que hacer un loop
// Para el RFC y el regimen fiscal se tiene que utilizar un segundo call a client get utilizando el valor de customer obtenido
// El tercer call es a un script elaborado en esta app para encontrar, si existiera, alguna forma de pago utilizada para pagar la venta
// El valor del tercer call se utiliza como referencia al usuario, pero este tiene que seleccionar manualmente
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
                method: 'facturacion_mx.facturacion_mx.doctype.factura.api.get_forma_de_pago',
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





//refactor:deberia poder llamar a la funcion con el dotted path
//refactor: debe tenerse el codigo hardocded en alguna variable

// Codigo que genera botones en la Factura
frappe.ui.form.on('Factura', {
	refresh: function(frm) {
        if (frm.doc.status == "Facturado"){
            frm.add_custom_button(__('Enviar por Correo'), function(){
                frappe.call({
                        method: 'facturacion_mx.facturacion_mx.doctype.factura.api.envia_factura_por_email',
                        args: {
                            doc: frm.doc
                        },
                        callback: function (r) {
                            if (r.message) {
                            console.log("#######server script message#########");
                            console.log(r.message);
                            }
                        }
                    });
            });
        }
	}
});