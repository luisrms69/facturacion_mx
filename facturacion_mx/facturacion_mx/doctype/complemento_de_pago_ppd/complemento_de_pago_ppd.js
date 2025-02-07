// Copyright (c) 2024, Consultoria en Negocios y Aplicaciones and contributors
// For license information, please see license.txt

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
                                    // console.log("Entra a uuid")
                                    // console.log(u.message)
                                    if (u.message) {
                                            child.uuid = u.message;
                                    }
                                }
                            })
                            child.base = reference.allocated_amount/1.16;
                            child.type = "IVA"; //fix:requiere calcularse
                            child.rate = 16;  //fix:requiere calcularse
                            child.factor = "Tasa";  //fix:requiere calcularse
                            child.withholding = false;
                        });
                    }
                }
            })
        }
    }
})


// Codigo que genera boton en la Factura para desccargar el archivo deseados y llama al método PY de envio
frappe.ui.form.on('Complemento de Pago PPD', {
    refresh: function (frm) {
        if (frm.doc.status == "Facturado") {
            frm.add_custom_button(__('Descargar'), function () {
                let d = new frappe.ui.Dialog({
                    title: 'Selecciona el formato en que quieres descargar la factura del complemento de pago',
                    fields: [
                        {
                            label: 'Formato Deseado',
                            fieldname: 'format',
                            fieldtype: 'Select',
                            default: 'pdf',
                            options: "xml\npdf\nzip"
                        }
                    ],
                    size: 'small', // small, large, extra-large 
                    primary_action_label: 'Descargar',
                    primary_action: function () {
                        var data = d.get_values();
                        frappe.call({
                            method: 'facturacion_mx.facturacion_mx.api.descarga_archivo',
                            args: {
                                document_name: frm.doc.name,
                                format: data.format,
                                doctype: "Complemento de Pago PPD"
                            },
                            callback: function (r) {
                                // if (r.message) {
                                //     // console.log("#######server script message#########");
                                //     // console.log(r.message);
                                // }
                                frm.reload_doc()
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