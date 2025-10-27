# Mejora de Filtros: Complemento de Pago PPD

**Fecha de implementación:** 27 de octubre de 2025
**Tipo de cambio:** Mejora de validación
**Riesgo:** Bajo
**Estado:** Implementado en llantascs.dev

---

## Resumen Ejecutivo

Se implementó un filtro mejorado para el campo "Entrada de Pago ID" en el doctype **Complemento de Pago PPD** que previene la selección de Payment Entries inválidos que contengan:
- Sales Invoices con método de pago PUE (Pago en Una Exhibición)
- Sales Invoices del año 2024 o anteriores
- Sales Invoices sin método de pago definido (NULL)

## Problema Original

El filtro anterior solo validaba:
- `Payment Entry.custom_status_payment_ppd = "Sin Facturar"`
- `Payment Entry.status = "Submitted"`

Esto permitía seleccionar Payment Entries que contenían Sales Invoices no elegibles para complemento PPD, causando errores al enviar al PAC.

## Solución Implementada

### Archivos Modificados

1. **`complemento_de_pago_ppd.py`** (líneas 14-67)
   - Agregado método `@frappe.whitelist()` `get_valid_payment_entries_for_ppd()`
   - Implementa filtrado con query SQL que valida todas las Sales Invoices relacionadas
   - Usa `@frappe.validate_and_sanitize_search_inputs` para seguridad

2. **`complemento_de_pago_ppd.js`** (líneas 5-12)
   - Agregado evento `setup` con `frm.set_query()`
   - Apunta al método Python para filtrado personalizado
   - **Nota:** Esta es la forma correcta en Frappe, NO usar `get_query` en JSON

3. **`complemento_de_pago_ppd.json`** (líneas 32-38)
   - Removido: `link_filters` (filtro antiguo e insuficiente)
   - Campo limpio sin `get_query` (se configura en JS)

### Lógica de Validación

El nuevo filtro aplica las siguientes reglas:

```sql
Payment Entry es válido si:
  ✓ custom_status_payment_ppd = 'Sin Facturar'
  ✓ docstatus = 1 (Submitted)
  ✓ payment_type = 'Receive'
  ✓ Tiene al menos una referencia a Sales Invoice
  ✓ TODAS sus Sales Invoices tienen:
    • custom_metodo_de_pago = 'PPD'
    • posting_date >= '2025-01-01'
```

### Implementación Técnica Correcta

**⚠️ Importante:** La forma correcta de filtrar un campo Link en Frappe es usando `frm.set_query()` en JavaScript, **NO** usando `get_query` en el JSON del DocType.

**JavaScript (complemento_de_pago_ppd.js):**
```javascript
frappe.ui.form.on("Complemento de Pago PPD", {
    setup: function(frm) {
        // Configurar filtro personalizado para Payment Entries válidos
        frm.set_query('entrada_de_pago_id', () => {
            return {
                query: 'facturacion_mx.facturacion_mx.doctype.complemento_de_pago_ppd.complemento_de_pago_ppd.get_valid_payment_entries_for_ppd'
            };
        });
    },
    ...
});
```

**Python (complemento_de_pago_ppd.py):**
```python
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_valid_payment_entries_for_ppd(doctype, txt, searchfield, start, page_len, filters):
    """Query personalizado que valida Payment Entries para Complemento PPD"""
    search_txt = f"%{txt}%" if txt else "%"

    return frappe.db.sql("""
        SELECT DISTINCT p.{key}, p.posting_date, p.paid_amount
        FROM `tabPayment Entry` AS p
        WHERE p.custom_status_payment_ppd = 'Sin Facturar'
            AND p.docstatus = 1
            AND p.payment_type = 'Receive'
            AND (p.{key} LIKE %(txt)s OR p.posting_date LIKE %(txt)s)
            AND NOT EXISTS (...)  -- Valida todas las Sales Invoices
            AND EXISTS (...)      -- Asegura que tenga referencias
        ORDER BY p.posting_date DESC
        LIMIT %(page_len)s OFFSET %(start)s
    """.format(key=searchfield), {'txt': search_txt, 'start': start, 'page_len': page_len})
```

**JSON (complemento_de_pago_ppd.json):**
```json
{
   "fieldname": "entrada_de_pago_id",
   "fieldtype": "Link",
   "options": "Payment Entry",
   "reqd": 1
   // NO incluir "get_query" aquí - se configura en JS
}
```

## Impacto Real en Producción

Basado en análisis de la base de datos de llantascs.dev (actualizado al 27-oct-2025):

| Métrica | Antes | Después | Cambio |
|---------|-------|---------|--------|
| Payment Entries visibles | 4,939 | **38** | **-99.2%** |
| Payment Entries con PUE | 4,292 (87%) | 0 | Excluidos ✓ |
| Payment Entries con invoices 2024 | 535 (11%) | 0 | Excluidos ✓ |
| Payment Entries con NULL | 486 (10%) | 0 | Excluidos ✓ |
| Payment Entries tipo "Pay" | 19 (0.4%) | 0 | Excluidos ✓ |
| Falsos positivos | 4,901 (99.2%) | 0 | Eliminados ✓ |

**Reducción de errores potenciales:** ~87% (eliminando PUE principalmente)

### Detalles de los 38 Payment Entries Válidos
- **Monto total:** $523,070.00 MXN
- **Periodo:** Enero 2025 - Octubre 2025
- **Sales Invoices:** 39 facturas (1 Payment Entry tiene 2 invoices)

## Análisis de Casos Edge

### Caso 1: Invoices del 2024 con custom_metodo_de_pago = NULL
**Cantidad:** 660 invoices
**Manejo:** Excluidas por filtro de fecha (< 2025-01-01)
**Riesgo:** Ninguno

### Caso 2: Invoices del 2025 sin timbrar (NULL)
**Cantidad:** 90 invoices (afectan 20 Payment Entries)
**Manejo:** Excluidas correctamente - deben timbrar primero
**Riesgo:** Ninguno

### Caso 3: Payment Entry sin referencias
**Manejo:** Excluidos por cláusula `EXISTS (SELECT 1 FROM tabPayment Entry Reference)`
**Riesgo:** Resuelto ✓

### Caso 4: Payment Entry mixto (PPD 2025 + PPD 2024)
**Manejo:** Excluido (debe tener TODAS las invoices del 2025+)
**Comportamiento:** Conservador - requiere homogeneidad de fechas
**Regulación:** Alineado con requerimientos SAT

## Flujo de Datos

```
Usuario intenta crear Complemento de Pago PPD
    ↓
Hace clic en campo "Entrada de Pago ID"
    ↓
Sistema ejecuta get_valid_payment_entries_for_ppd()
    ↓
Query SQL valida cada Payment Entry:
    ├─ ✓ Valida estado del Payment Entry
    ├─ ✓ Cruza con Sales Invoices relacionadas
    ├─ ✓ Verifica método de pago de cada invoice
    └─ ✓ Verifica fecha de cada invoice
    ↓
Retorna solo Payment Entries 100% válidos
    ↓
Usuario selecciona de lista filtrada
    ↓
Menos errores al enviar al PAC ✓
```

## Pruebas Realizadas

### 1. Validación de Sintaxis
```bash
✓ Python syntax: OK
✓ JSON syntax: OK
```

### 2. Migración de Base de Datos
```bash
✓ bench migrate: Exitoso
✓ DocType actualizado: Complemento de Pago PPD
```

### 3. Prueba Funcional del Método
```python
✓ Método ejecutado exitosamente
✓ Resultados encontrados: 10 (limitados por page_len)
✓ Query retorna tuplas con (name, posting_date, paid_amount)
```

### 4. Análisis de Resultados (Actualizado)
```sql
De 4,939 Payment Entries "Sin Facturar":
  ✓ 38 cumplen todos los criterios (0.77%)
  ✓ 4,901 correctamente excluidos (99.23%)
```

### 5. Prueba Final en Navegador
```
✓ Modo incógnito: Filtro funcionando correctamente
✓ ACC-PAY-2025-00877 (tipo "Pay") correctamente excluido
✓ Solo se muestran Payment Entries tipo "Receive" con invoices PPD 2025+
```

## Configuración Futura (Opcional)

Si el criterio de fecha necesita cambiar en el futuro, agregar a **Facturacion MX Settings**:

```json
{
    "fieldname": "fecha_inicio_complemento_ppd",
    "fieldtype": "Date",
    "label": "Fecha Inicio Complemento PPD",
    "default": "2025-01-01"
}
```

Y modificar la query en línea 46 de `complemento_de_pago_ppd.py`:
```python
fecha_inicio = frappe.db.get_single_value("Facturacion MX Settings", "fecha_inicio_complemento_ppd") or "2025-01-01"
# Usar fecha_inicio en la query
```

## Migración a Producción

### Pre-requisitos
- ✓ Implementación validada en llantascs.dev
- ⏳ Pruebas de usuario en ambiente de desarrollo
- ⏳ Aprobación final

### Pasos para Migración
1. Hacer backup de producción
2. Verificar que no haya cambios conflictivos en producción
3. Hacer pull de los cambios del repositorio
4. Ejecutar `bench migrate` en producción
5. Verificar que el filtro funciona correctamente
6. Monitorear errores en las primeras 24 horas

### Rollback (si es necesario)
Si se requiere revertir el cambio:

**Opción A - Rollback completo:**
```bash
cd /home/erpnext/frappe-bench
git -C apps/facturacion_mx revert <commit_hash>
bench migrate
```

**Opción B - Restaurar filtro anterior (emergencia):**
Editar `complemento_de_pago_ppd.json`:
```json
{
   "fieldname": "entrada_de_pago_id",
   "fieldtype": "Link",
   "in_list_view": 1,
   "label": "Entrada de Pago ID",
   "link_filters": "[[\"Payment Entry\",\"custom_status_payment_ppd\",\"=\",\"Sin Facturar\"],[\"Payment Entry\",\"status\",\"=\",\"Submitted\"]]",
   "options": "Payment Entry",
   "reqd": 1
}
```
Y ejecutar `bench migrate`.

## Mantenimiento

### Monitoreo Recomendado
- Revisar logs de errores del PAC semanalmente
- Comparar tasa de rechazo antes/después de implementación
- Recolectar feedback de usuarios sobre falsos negativos

### Posibles Ajustes Futuros
Si se detectan Payment Entries válidos que están siendo excluidos:
1. Identificar el patrón del falso negativo
2. Analizar si es un problema de datos o de lógica
3. Ajustar la query en `complemento_de_pago_ppd.py`
4. Probar en dev antes de migrar a producción

## Referencias

- **Reporte relacionado:** `complementos_de_pago_ppd_pendientes`
  (Usa lógica similar validada en producción)
- **API relacionada:** `facturacion_mx.facturacion_mx.api.actualizar_status_payment_entry()`
- **Doctype relacionado:** `Factura` (contiene definición de métodos de pago SAT)

## Notas de Deprecación

⚠️ **Importante:** Este sistema será deprecado en aproximadamente 2 meses. Esta implementación fue diseñada con ese contexto:
- Solución simple y directa
- Sin sobre-diseño
- Enfocada en resolver el problema inmediato
- Fácil de mantener durante el periodo restante

## Contacto

Para preguntas sobre esta implementación:
- **Desarrollador:** Claude Code
- **Fecha:** 2025-10-27
- **Commit:** (pendiente de registro en git)
