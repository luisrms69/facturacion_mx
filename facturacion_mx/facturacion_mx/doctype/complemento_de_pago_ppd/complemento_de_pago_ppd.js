// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Complemento de Pago PPD", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Complemento de Pago PPD", {
    entrada_de_pago_id: function (frm) {
        if (frm.doc.entrada_de_pago_id) {
            frm.clear_table('documentos_relacionados_con_el_pago')
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: "Payment Entry",
                    filters: {
                        name: frm.doc.entrada_de_pago_id
                    }
                },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value('fecha_de_pago', r.message.posting_date);
                        frm.set_value('forma_de_pago', r.message.mode_of_payment);
                        frm.clear_table('documentos_relacionados_con_el_pago')
                        // console.log(r.message)
                        // refactor: los siguietnes datos deben quedar programados y no hardcoded
                        r.message.references.forEach(function (reference) {
                            var child = frm.add_child('documentos_relacionados_con_el_pago');
                            child.cantidad = reference.allocated_amount;
                            frappe.call({
                                method: 'facturacion_mx.facturacion_mx.api.get_numero_de_pago',
                                args: {
                                    sales_invoice_id : reference.reference_name,
                                    payment_entry_id : frm.doc.entrada_de_pago_id
                                },
                                callback: function (t) {
                                    if (t.message) {
                                            child.numero_de_pago = t.message;
                                    }
                                }
                            })
                            // child.numero_de_pago = 1; //fix:requiere calcularse
                            child.saldo_pendiente = reference.allocated_amount + reference.outstanding_amount;
                            child.sales_invoice_id = reference.reference_name;
                            frappe.call({
                                method: 'facturacion_mx.facturacion_mx.api.get_folio_from_invoice',
                                args: {
                                    sales_invoice_id : reference.reference_name
                                },
                                callback: function (s) {
                                    if (s.message) {
                                            child.folio = s.message;
                                    }
                                }
                            })
                            frappe.call({
                                method: 'facturacion_mx.facturacion_mx.api.get_uuid_from_invoice',
                                args: {
                                    sales_invoice_id : reference.reference_name
                                },
                                callback: function (u) {
                                    console.log("Entra a uuid")
                                    console.log(u.message)
                                    if (u.message) {
                                            child.uuid = u.message;
                                    }
                                }
                            })
                            child.base = reference.allocated_amount;
                            child.type = "IVA"; //fix:requiere calcularse
                            child.rate = 16;  //fix:requiere calcularse
                            child.factor = "Tasa";  //fix:requiere calcularse
                            child.withholding = false;
                        });
                    }
                }
            })
            // }),
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
// });
})


//refactor:deberia poder llamar a la funcion con el dotted path
//refactor: debe tenerse el codigo hardocded en alguna variable
//refactor: las siguientes funciones dependen que la factura tenga estado facturado, creo que pueden meterse en uno solo

// Codigo que genera boton en la Factura para hacer el envio por correo y llama al método PY de envio
// frappe.ui.form.on('Factura', {
//     refresh: function (frm) {
//         if (frm.doc.status == "Facturado") {
//             frm.add_custom_button(__('Enviar por Correo'), function () {
//                 let d = new frappe.ui.Dialog({
//                     title: 'Selecciona el correo electronico al que quieres enviar la factura',
//                     fields: [
//                         {
//                             label: 'Correo Electronioco',
//                             fieldname: 'email_id',
//                             fieldtype: 'Data',
//                             default: frm.doc.email_id
//                         }
//                     ],
//                     size: 'small', // small, large, extra-large 
//                     primary_action_label: 'Submit',
//                     primary_action: function () {
//                         var data = d.get_values();
//                         frappe.call({
//                             method: 'facturacion_mx.facturacion_mx.api.envia_factura_por_email',
//                             args: {
//                                 current_document: frm.doc.name,
//                                 email_id: data.email_id
//                             },
//                             callback: function (r) {
//                                 if (r.message) {
//                                     console.log("#######server script message#########");
//                                     console.log(r.message);
//                                 }
//                                 d.hide();
//                             }
//                         });
//                     }
//                 });

//                 d.show();
//             })
//         }
//     }
// });

// // Codigo que genera boton en la Factura para desccargar el archivo deseados y llama al método PY de envio
// frappe.ui.form.on('Factura', {
//     refresh: function (frm) {
//         if (frm.doc.status == "Facturado") {
//             frm.add_custom_button(__('Descargar'), function () {
//                 let d = new frappe.ui.Dialog({
//                     title: 'Selecciona el formato en que quieres descargar la factura',
//                     fields: [
//                         {
//                             label: 'Formato Deseado',
//                             fieldname: 'format',
//                             fieldtype: 'Select',
//                             default: 'zip',
//                             options: "xml\npdf\nzip"
//                         }
//                     ],
//                     size: 'small', // small, large, extra-large 
//                     primary_action_label: 'Submit',
//                     primary_action: function () {
//                         var data = d.get_values();
//                         frappe.call({
//                             method: 'facturacion_mx.facturacion_mx.api.descarga_factura',
//                             args: {
//                                 document_name: frm.doc.name,
//                                 // current_document: frm.doc.id_pac,
//                                 format: data.format
//                             },
//                             callback: function (r) {
//                                 if (r.message) {
//                                     console.log("#######server script message#########");
//                                     console.log(r.message);
//                                 }
//                                 d.hide();
//                             }
//                         });
//                     }
//                 });

//                 d.show();
//             })
//         }
//     }
// });



// // Codigo que genera boton en la Factura para cancelar y llama al método PY de envio
// // Se deben tener que automatizar para utilizar el doctype Motivo de Cancelacion
// //refactor: estaba originalmente en un loop pero al seleccionar cualquier opcion se tomaba el valor de "i", que era el final del loop

// frappe.call({
//     method: "frappe.client.get_list",
//     args: {
//         doctype: "Motivo de Cancelacion",
//         fields: ["motivo_de_cancelación", "descripcion"],
//     },
//     async: false,
//     callback(r) {
//         if (r.message) {
//             motivos_de_cancelacion = r.message
//             // console.log(motivos_de_cancelacion)
//             // console.log(motivos_de_cancelacion[1])
//             // console.log(motivos_de_cancelacion[1].descripcion)
//             // console.log(motivos_de_cancelacion[1].motivo_de_cancelación)
//             // console.log(r.message)
//         }
//     },
// });

// // motivos_cancelacion =["01 Comprobante emitido con errores con relación", "02 Comprobante emitido con errores sin relación", "03 No se llevó a cabo la operación", "04 Operación nominativa relacionada en la factura global"] //refactor: tomar de la variable global
// frappe.ui.form.on('Factura', {
//     refresh: function (frm) {
//         if (frm.doc.status == "Facturado") {  //refactor: tomar de la variable global
//             frm.add_custom_button(__(motivos_de_cancelacion[0].descripcion), function () {  // Debo obtener el valor de la cancelacion automaticamente
//                 frappe.call({
//                     method: 'facturacion_mx.facturacion_mx.api.cancela_factura',
//                     args: {
//                         doc: frm.doc.name,
//                         motivo: motivos_de_cancelacion[0].motivo_de_cancelación
//                     },
//                     callback: function (r) {
//                         if (r.message) {
//                             console.log("#######server script message#########");
//                             console.log(r.message);
//                         }
//                     }
//                 });
//             }, __("Cancelaciones")
//             );
//             frm.add_custom_button(__(motivos_de_cancelacion[1].descripcion), function () {  // Debo obtener el valor de la cancelacion automaticamente
//                 frappe.call({
//                     method: 'facturacion_mx.facturacion_mx.api.cancela_factura',
//                     args: {
//                         doc: frm.doc.name,
//                         motivo: motivos_de_cancelacion[1].motivo_de_cancelación
//                     },
//                     callback: function (r) {
//                         if (r.message) {
//                             console.log("#######server script message#########");
//                             console.log(r.message);
//                         }
//                     }
//                 });
//             }, __("Cancelaciones")
//             );
//             frm.add_custom_button(__(motivos_de_cancelacion[2].descripcion), function () {  // Debo obtener el valor de la cancelacion automaticamente
//                 frappe.call({
//                     method: 'facturacion_mx.facturacion_mx.api.cancela_factura',
//                     args: {
//                         doc: frm.doc.name,
//                         motivo: motivos_de_cancelacion[2].motivo_de_cancelación
//                     },
//                     callback: function (r) {
//                         if (r.message) {
//                             console.log("#######server script message#########");
//                             console.log(r.message);
//                         }
//                     }
//                 });
//             }, __("Cancelaciones")
//             );

//             frm.add_custom_button(__(motivos_de_cancelacion[3].descripcion), function () {  // Debo obtener el valor de la cancelacion automaticamente
//                 frappe.call({
//                     method: 'facturacion_mx.facturacion_mx.api.cancela_factura',
//                     args: {
//                         doc: frm.doc.name,
//                         motivo: motivos_de_cancelacion[3].motivo_de_cancelación
//                     },
//                     callback: function (r) {
//                         if (r.message) {
//                             console.log("#######server script message#########");
//                             console.log(r.message);
//                         }
//                     }
//                 });
//             }, __("Cancelaciones")
//             );
//         }
//     }
// });


// forma_pago_ppd_ingreso = "99" //refactor: tomar del doctype ambas
// name_metodo_ppd = "METODOPAGO-PPD-Pago en parcialidades o diferido"

// frappe.ui.form.on("Factura", "metodo_pago_sat", function (frm) {
//     if (frm.doc.metodo_pago_sat == name_metodo_ppd) {
//         frm.set_value("foma_de_pago_sat", forma_pago_ppd_ingreso)
//     };
// })
