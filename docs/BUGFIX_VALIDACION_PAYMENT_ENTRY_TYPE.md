# Bugfix: Validación de Payment Entry Type en Complemento de Pago PPD

**Fecha:** 27 de octubre de 2025
**Tipo:** Corrección de error + Validaciones defensivas
**Prioridad:** Alta
**Estado:** Implementado en llantascs.dev

---

## Resumen del Problema

Se detectó que era posible seleccionar Payment Entries de tipo **"Pay"** (pagos a proveedores) en el formulario de Complemento de Pago PPD, cuando solo deberían permitirse Payment Entries tipo **"Receive"** (cobros a clientes).

### Manifestación del Error

```
ValueError: 'ACC-PAY-2025-00877' is not in list
```

Ocurre en `api.py:1326` dentro de `get_numero_de_pago()`.

**Mensaje de error adicional:**
> "No se ha encontrado ninguna factura con el numero de referencia, verifica que ya se haya elaborado la factura PPD por el pago que quieres facturar"

---

## Causa Raíz

### Problema Principal
Un Payment Entry de tipo **"Pay"** (pago a proveedor) fue seleccionado en el formulario:
- Payment Entry: ACC-PAY-2025-00877-1
- Tipo: "Pay" (debería ser "Receive")
- Party: Supplier "Tire Direct"
- Referencias: Purchase Invoices (no Sales Invoices)

### Cómo Ocurrió
El formulario fue abierto **ANTES** del `bench migrate` que aplicó el nuevo filtro. El navegador cargó el metadata antiguo en caché, permitiendo seleccionar Payment Entries inválidos.

### Cascada de Errores

1. JavaScript itera sobre `references` del Payment Entry
2. Las referencias son **Purchase Invoices** (no Sales Invoices)
3. Llama a `get_uuid_from_invoice(sales_invoice_id='52672')` donde 52672 es Purchase Invoice
4. Busca en doctype "Factura" con `sales_invoice_id='52672'`
5. No encuentra nada → Error "No se ha encontrado ninguna factura..."
6. También falla `get_numero_de_pago()` porque la lista está vacía

---

## Solución Implementada: Defensa en Profundidad

He implementado **3 capas de validación** para prevenir este error:

### Capa 1: Filtro en Base de Datos (Ya Existía)

**Archivo:** `complemento_de_pago_ppd.py:28-60`

```python
@frappe.whitelist()
def get_valid_payment_entries_for_ppd(...):
    return frappe.db.sql("""
        ...
        WHERE p.payment_type = 'Receive'  # Solo cobros a clientes
        ...
    """)
```

**Efectividad:** ✅ Previene que Payment Entries tipo "Pay" aparezcan en el dropdown

---

### Capa 2: Validación JavaScript en Selección (NUEVA)

**Archivo:** `complemento_de_pago_ppd.js:18-47`

Agregada validación inmediata cuando el usuario selecciona un Payment Entry:

```javascript
if (r.message.payment_type !== 'Receive') {
    frappe.msgprint({
        title: 'Payment Entry No Válido',
        indicator: 'red',
        message: `El Payment Entry es de tipo "${r.message.payment_type}".
                  Los Complementos de Pago PPD solo aplican para cobros a clientes (tipo "Receive").
                  Por favor selecciona un Payment Entry válido.`
    });
    frm.set_value('entrada_de_pago_id', null);
    return;
}
```

**Validaciones adicionales:**
- ✅ Verifica `payment_type === 'Receive'`
- ✅ Verifica que tenga al menos una referencia a Sales Invoice
- ✅ Muestra mensaje de error descriptivo
- ✅ Limpia el campo automáticamente

**Efectividad:** 🛡️ Capa de seguridad si el filtro es bypaseado (caché, etc.)

---

### Capa 3: Filtro en Loop de Referencias (NUEVA)

**Archivo:** `complemento_de_pago_ppd.js:81-84`

Agregado filtro en el loop que procesa las referencias:

```javascript
r.message.references.forEach(function (reference) {
    // Solo procesar Sales Invoices, ignorar otros tipos (Purchase Invoice, etc.)
    if (reference.reference_doctype !== 'Sales Invoice') {
        return;
    }
    // ... procesar child
});
```

**Efectividad:** 🛡️ Previene procesar Purchase Invoices aunque pasen las validaciones anteriores

---

## Comparación: Antes vs Después

| Escenario | Antes | Después |
|-----------|-------|---------|
| **Seleccionar Payment Entry tipo "Pay"** | ✅ Permitido | ⛔ Bloqueado por filtro DB |
| **Caché antiguo permite selección** | ❌ Error en runtime | ⛔ Validación JS bloquea + mensaje claro |
| **Payment Entry con Purchase Invoices** | ❌ Error en `get_uuid_from_invoice()` | ⛔ Loop ignora Purchase Invoices |
| **Mensaje de error al usuario** | ❓ Técnico y confuso | ✅ Claro y accionable |

---

## Archivos Modificados

```
facturacion_mx/facturacion_mx/doctype/complemento_de_pago_ppd/
└── complemento_de_pago_ppd.js
    ├── Líneas 18-47: Validación de payment_type y Sales Invoice
    └── Líneas 81-84: Filtro en loop de referencias
```

---

## Instrucciones para el Usuario

### Si Encuentras Este Error

**Paso 1: Limpiar caché del navegador**
```
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)
```

**Paso 2: Cerrar formulario actual**
- Descartar cambios no guardados
- Cerrar la pestaña

**Paso 3: Abrir nuevo formulario**
- Ir a: Complemento de Pago PPD > Nuevo
- Ahora el filtro debería funcionar correctamente

**Paso 4: Verificar tipo de Payment Entry**
- Solo deberían aparecer Payment Entries tipo "Receive"
- Si seleccionas uno inválido (por error), verás mensaje de advertencia

---

## Pruebas Realizadas

### Test 1: Filtro DB Excluye Payment Entries "Pay"
```python
resultado = get_valid_payment_entries_for_ppd(txt="ACC-PAY-2025-00877", ...)
# Resultado: 0 (correctamente excluido)
```
✅ Pasado

### Test 2: Validación JS con Payment Entry "Pay"
- Abrir formulario nuevo
- Intentar seleccionar Payment Entry tipo "Pay" (si logra bypasear filtro)
- **Resultado esperado:** Mensaje de error + campo se limpia
✅ Implementado (requiere prueba manual post-caché limpio)

### Test 3: Loop Ignora Purchase Invoices
- Seleccionar Payment Entry con Purchase Invoices
- **Resultado esperado:** No se agregan filas a `documentos_relacionados_con_el_pago`
✅ Implementado (requiere prueba manual)

---

## Monitoreo Post-Implementación

### Métricas a Revisar
- Cantidad de errores `ValueError` en logs (debería reducirse a 0)
- Reportes de usuarios sobre Payment Entries no disponibles
- Complementos PPD creados exitosamente

### Casos a Investigar
Si un usuario reporta que **NO** encuentra Payment Entries válidos:

1. Verificar en DB:
```sql
SELECT p.name, p.posting_date, p.payment_type, p.custom_status_payment_ppd
FROM `tabPayment Entry` p
WHERE p.custom_status_payment_ppd = 'Sin Facturar'
AND p.docstatus = 1
AND p.payment_type = 'Receive'
LIMIT 10;
```

2. Si la query retorna resultados pero el usuario no los ve:
   - Problema de caché (limpiar caché del navegador)
   - Problema de permisos (verificar roles)

3. Si la query NO retorna resultados:
   - No hay Payment Entries válidos pendientes
   - Revisar criterios de filtrado (PPD, 2025, etc.)

---

## Mejoras Futuras (Opcional)

### Validación en Python (Backend)

Para máxima robustez, considerar agregar validación en `complemento_de_pago_ppd.py:validate()`:

```python
def validate(self):
    if self.entrada_de_pago_id:
        pe = frappe.get_doc("Payment Entry", self.entrada_de_pago_id)

        # Validar tipo
        if pe.payment_type != "Receive":
            frappe.throw(f"El Payment Entry {self.entrada_de_pago_id} es tipo '{pe.payment_type}'. "
                        "Solo se permiten Payment Entries tipo 'Receive' (cobros a clientes).")

        # Validar que tenga Sales Invoices
        has_sales_invoice = any(
            ref.reference_doctype == "Sales Invoice"
            for ref in pe.references
        )
        if not has_sales_invoice:
            frappe.throw(f"El Payment Entry {self.entrada_de_pago_id} no tiene referencias a Sales Invoices.")
```

**Ventaja:** Validación servidor-side imposible de bypasear
**Desventaja:** Requiere más cambios, puede romper documentos existentes
**Recomendación:** Implementar solo si persisten problemas

---

## Rollback (Si es Necesario)

Si esta corrección causa problemas inesperados, revertir cambios en:

**complemento_de_pago_ppd.js:**

```javascript
// Líneas 18-47: Eliminar validaciones agregadas
// Líneas 81-84: Eliminar filtro de reference_doctype
```

Luego:
```bash
cd /home/erpnext/frappe-bench
bench --site llantascs.dev clear-cache
```

---

## Contexto Adicional

### ¿Por Qué Existen Payment Entries "Pay" con custom_status_payment_ppd?

Hay 19 Payment Entries de tipo "Pay" con este campo. Esto sugiere:
1. El campo se agregó globalmente a todos los Payment Entries
2. O hubo un caso de uso anterior (ahora deprecado) para pagos a proveedores
3. O es un error de configuración histórico

**Recomendación:** Considerar remover `custom_status_payment_ppd` de Payment Entries tipo "Pay" en una limpieza futura.

---

## Referencias

- **Reporte relacionado:** Complementos de pago PPD pendientes
- **Doctype:** Complemento de Pago PPD
- **Issue anterior:** MEJORA_FILTROS_COMPLEMENTO_PPD_2025.md
- **API afectada:** `get_numero_de_pago()`, `get_uuid_from_invoice()`, `get_folio_from_invoice()`

---

## Lecciones Aprendidas

1. **Caché del navegador** puede causar que metadata antiguo persista después de migrate
2. **Validaciones defensivas** en múltiples capas previenen errores cascada
3. **Mensajes de error claros** mejoran UX cuando algo falla
4. **Filtros en loops** previenen procesar datos inválidos silenciosamente

---

## Contacto

Para preguntas sobre esta corrección:
- **Implementado por:** Claude Code
- **Fecha:** 2025-10-27
- **Ambiente:** llantascs.dev
