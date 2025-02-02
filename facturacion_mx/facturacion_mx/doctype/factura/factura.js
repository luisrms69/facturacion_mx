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
                                    frm.set_value('usocfdi', s.message.custom_uso_cfdi)
                                }
                            }
                        });
                    }
                }
            });
                // frappe.call({
                //     method: 'facturacion_mx.facturacion_mx.api.get_forma_de_pago',
                //     args: {
                //         sales_invoice_id: frm.doc.sales_invoice_id
                //     },
                //     callback: function (t) {
                //         if (t.message) {
                //             // console.log("#######server script message#########");
                //             // console.log(t.message);
                //             frm.set_value('referencia_de_pago', t.message);
                //         } else {
                //             frm.set_value('referencia_de_pago', "No hay referencia de forma de pago")
                //         }
                //     }
                // });
        }
    }
});



// GET notes from factura depending on mode of payment
frappe.ui.form.on('Factura', {
    // metodo_pago_sat: function (frm) {
        refresh: function (frm) {
        if (frm.doc.metodo_pago_sat && frm.doc.sales_invoice_id) {
            frm.refresh_field('notas');
            frappe.call({
                method: 'facturacion_mx.facturacion_mx.api.get_factura_notes',
                args: {
                    metodo_de_pago: frm.doc.metodo_pago_sat,
                    sales_invoice_id: frm.doc.sales_invoice_id,
                },
                callback: function (r) {
                    // console.log("#######notas son#########")
                    // console.log(r.message);
                    if (r.message) {
                        frm.set_value('notas', r.message);
                    }
                    else {
                        frm.set_value('notas',"")
                    }
                    frm.refresh_field('notas');
                }
            });
        }
    }
});







//refactor:deberia poder llamar a la funcion con el dotted path
//refactor: debe tenerse el codigo hardocded en alguna variable
//refactor: las siguientes funciones dependen que la factura tenga estado facturado, creo que pueden meterse en uno solo

// Codigo que genera boton en la Factura para hacer el envio por correo y llama al método PY de envio
frappe.ui.form.on('Factura', {
    refresh: function (frm) {
        if (frm.doc.status == "Facturado") {
            frm.add_custom_button(__('Enviar por Correo'), function () {
                let d = new frappe.ui.Dialog({
                    title: 'Selecciona el correo electronico al que quieres enviar la factura',
                    fields: [
                        {
                            label: 'Correo Electronioco',
                            fieldname: 'email_id',
                            fieldtype: 'Data',
                            default: frm.doc.email_id
                        }
                    ],
                    size: 'small', // small, large, extra-large 
                    primary_action_label: 'Submit',
                    primary_action: function () {
                        var data = d.get_values();
                        frappe.call({
                            method: 'facturacion_mx.facturacion_mx.api.envia_factura_por_email',
                            args: {
                                current_document: frm.doc.name,
                                email_id: data.email_id
                            },
                            callback: function (r) {
                                if (r.message) {
                                    console.log("#######server script message#########");
                                    console.log(r.message);
                                }
                                d.hide();
                            }
                        });
                    }
                });

                d.show();
            })
        }
    }
});

// Codigo que genera boton en la Factura para desccargar el archivo deseados y llama al método PY de envio
frappe.ui.form.on('Factura', {
    refresh: function (frm) {
        if (frm.doc.status == "Facturado") {
            frm.add_custom_button(__('Descargar'), function () {
                let d = new frappe.ui.Dialog({
                    title: 'Selecciona el formato en que quieres descargar la factura',
                    fields: [
                        {
                            label: 'Formato Deseado',
                            fieldname: 'format',
                            fieldtype: 'Select',
                            default: 'zip',
                            options: "xml\npdf\nzip"
                        }
                    ],
                    size: 'small', // small, large, extra-large 
                    primary_action_label: 'Submit',
                    primary_action: function () {
                        var data = d.get_values();
                        frappe.call({
                            method: 'facturacion_mx.facturacion_mx.api.descarga_factura',
                            args: {
                                document_name: frm.doc.name,
                                // current_document: frm.doc.id_pac,
                                format: data.format
                            },
                            callback: function (r) {
                                if (r.message) {
                                    console.log("#######server script message#########");
                                    console.log(r.message);
                                }
                                d.hide();
                            }
                        });
                    }
                });

                d.show();
            })
        }
    }
});



// Codigo que genera boton en la Factura para cancelar y llama al método PY de envio
// Se deben tener que automatizar para utilizar el doctype Motivo de Cancelacion
//refactor: estaba originalmente en un loop pero al seleccionar cualquier opcion se tomaba el valor de "i", que era el final del loop

frappe.call({
    method: "frappe.client.get_list",
    args: {
        doctype: "Motivo de Cancelacion",
        fields: ["motivo_de_cancelación", "descripcion"],
    },
    async: false,
    callback(r) {
        if (r.message) {
            motivos_de_cancelacion = r.message
            // console.log(motivos_de_cancelacion)
            // console.log(motivos_de_cancelacion[1])
            // console.log(motivos_de_cancelacion[1].descripcion)
            // console.log(motivos_de_cancelacion[1].motivo_de_cancelación)
            // console.log(r.message)
        }
    },
});

// motivos_cancelacion =["01 Comprobante emitido con errores con relación", "02 Comprobante emitido con errores sin relación", "03 No se llevó a cabo la operación", "04 Operación nominativa relacionada en la factura global"] //refactor: tomar de la variable global
frappe.ui.form.on('Factura', {
    refresh: function (frm) {
        if (frm.doc.status == "Facturado" && frappe.user.has_role('Facturacion MX Manager')) {  //refactor: tomar de la variable global
            frm.add_custom_button(__(motivos_de_cancelacion[0].descripcion), function () {  // Debo obtener el valor de la cancelacion automaticamente
                frappe.call({
                    method: 'facturacion_mx.facturacion_mx.api.cancela_factura',
                    args: {
                        doc: frm.doc.name,
                        motivo: motivos_de_cancelacion[0].motivo_de_cancelación
                    },
                    callback: function (r) {
                        if (r.message) {
                            console.log("#######server script message#########");
                            console.log(r.message);
                        }
                    }
                });
            }, __("Cancelaciones")
            );
            frm.add_custom_button(__(motivos_de_cancelacion[1].descripcion), function () {  // Debo obtener el valor de la cancelacion automaticamente
                frappe.call({
                    method: 'facturacion_mx.facturacion_mx.api.cancela_factura',
                    args: {
                        doc: frm.doc.name,
                        motivo: motivos_de_cancelacion[1].motivo_de_cancelación
                    },
                    callback: function (r) {
                        if (r.message) {
                            console.log("#######server script message#########");
                            console.log(r.message);
                        }
                    }
                });
            }, __("Cancelaciones")
            );
            frm.add_custom_button(__(motivos_de_cancelacion[2].descripcion), function () {  // Debo obtener el valor de la cancelacion automaticamente
                frappe.call({
                    method: 'facturacion_mx.facturacion_mx.api.cancela_factura',
                    args: {
                        doc: frm.doc.name,
                        motivo: motivos_de_cancelacion[2].motivo_de_cancelación
                    },
                    callback: function (r) {
                        if (r.message) {
                            console.log("#######server script message#########");
                            console.log(r.message);
                        }
                    }
                });
            }, __("Cancelaciones")
            );

            frm.add_custom_button(__(motivos_de_cancelacion[3].descripcion), function () {  // Debo obtener el valor de la cancelacion automaticamente
                frappe.call({
                    method: 'facturacion_mx.facturacion_mx.api.cancela_factura',
                    args: {
                        doc: frm.doc.name,
                        motivo: motivos_de_cancelacion[3].motivo_de_cancelación
                    },
                    callback: function (r) {
                        if (r.message) {
                            console.log("#######server script message#########");
                            console.log(r.message);
                        }
                    }
                });
            }, __("Cancelaciones")
            );
        }
    }
});


forma_pago_ppd_ingreso = "99" //refactor: tomar del doctype ambas
name_metodo_ppd = "METODOPAGO-PPD-Pago en parcialidades o diferido"

frappe.ui.form.on("Factura", "metodo_pago_sat", function (frm) {
    if (frm.doc.metodo_pago_sat == name_metodo_ppd) {
        frm.set_value("foma_de_pago_sat", forma_pago_ppd_ingreso)
    };
})



//refactor: deberia aparecer solo cuando ya hay info en la tabla

frappe.ui.form.on('Factura', {
	refresh: function(frm) {
        if (frappe.user.has_role('Facturacion MX Manager')){
            frm.add_custom_button(__('Revisar Status'), function(){
                frappe.call({
                        method: 'facturacion_mx.facturacion_mx.api.status_check_factura',
                        args: {
                            id_factura: frm.doc.response_pac[0].id,
                            factura_docname: frm.docname
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
