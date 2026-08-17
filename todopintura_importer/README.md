# Todopintura Client Importer

Módulo Odoo 19 para importar clientes desde archivos Excel del sistema Todopintura
(UMACLI.xlsx).

## Características

✅ **Importación masiva de clientes** desde archivos Excel ✅ **Identificación
automática** de clientes existentes (por `external_id` o `vat`) ✅ **Creación o
actualización** según corresponda ✅ **Validación de datos** antes de importar ✅
**Registro completo** de todas las operaciones ✅ **Campos personalizados** para
información específica de Todopintura ✅ **Vista previa** de datos antes de confirmar

## Instalación

1. Copiar el módulo en la carpeta de addons de Odoo:

   ```bash
   cp -r todopintura_importer /path/to/odoo/addons/
   ```

2. Instalar en Odoo:

   - Ir a `Aplicaciones` → Buscar `todopintura_importer` → Instalar

3. Verificar dependencias:
   - El módulo requiere `openpyxl` para leer archivos Excel
   - Instalar si es necesario: `pip install openpyxl`

## Uso

### 1. Acceder al importador

Menú → **Todopintura** → **Importar Clientes**

### 2. Seleccionar archivo

- Selecciona el archivo `UMACLI.xlsx` de Todopintura
- El sistema mostrará una vista previa de los datos
- Se validarán automáticamente los registros

### 3. Revisar advertencias

Si hay datos incompletos o inconsistencias, aparecerán en la sección "Advertencias".

### 4. Confirmar importación

- Si todo es correcto, haz clic en **"Importar"**
- El sistema procesará todos los registros
- Verás un resumen de:
  - Clientes creados
  - Clientes actualizados
  - Errores encontrados

### 5. Revisar histórico

Menú → **Todopintura** → **Histórico de Importaciones**

Aquí puedes ver todas las importaciones realizadas y el registro detallado de cada
operación.

## Mapeo de campos Excel → Odoo

| Campo Excel        | Campo Odoo                           | Tipo      | Notas                    |
| ------------------ | ------------------------------------ | --------- | ------------------------ |
| NUMERO CLIENTE     | `todopintura_external_id`            | Char      | Identificador único      |
| NOMBRE DE CLIENTE  | `name`                               | Char      | Nombre del cliente       |
| DIRECCION          | `street`                             | Char      | Dirección principal      |
| CODIGO POSTAL      | `zip`                                | Char      | Código postal            |
| TELEFONO 1         | `phone`                              | Char      | Teléfono principal       |
| TELEFONO 2         | `mobile`                             | Char      | Móvil/alternativo        |
| DNI O CFIF         | `vat`                                | Char      | NIF/VAT fiscal           |
| CORREO ELECTRONICO | `email`                              | Char      | Correo de contacto       |
| LIMITE DE CREDITO  | `todopintura_credit_limit`           | Float     | Límite de crédito        |
| DESCUENTO FIJO     | `todopintura_discount_fixed`         | Float     | Descuento % fijo         |
| PRONTO PAGO        | `todopintura_discount_early_payment` | Float     | Descuento % pronto pago  |
| NECESITA VALE      | `todopintura_needs_voucher`          | Selection | S/N                      |
| CONDICIONES PAGO   | `property_payment_term_id`           | Many2One  | Se busca en payment.term |
| OBSERVACIONES 1-4  | `comment`                            | Text      | Concatenadas con saltos  |

## Estrategia de identificación

Cuando se importa un cliente, el sistema busca:

1. **Primero**: Por `todopintura_external_id` (NUMERO CLIENTE)
2. **Si no encuentra**: Por `vat` (DNI/CIF)
3. **Si no existe**: Crea un cliente nuevo

Si encuentra un cliente existente, actualiza sus datos (excepto `name` y `external_id`
que no cambian).

## Campos personalizados en res.partner

Estos campos se agregan automáticamente a cada cliente:

- **todopintura_external_id**: Nº de Cliente (Todopintura)
- **todopintura_credit_limit**: Límite de Crédito
- **todopintura_discount_fixed**: Descuento Fijo (%)
- **todopintura_discount_early_payment**: Descuento Pronto Pago (%)
- **todopintura_needs_voucher**: Necesita Vale (S/N)
- **todopintura_last_sync**: Última Sincronización
- **todopintura_import_log**: Histórico de Importación

## Validaciones

El sistema valida automáticamente:

- ✅ Cliente sin nombre → Se rechaza el registro
- ✅ Cliente sin número → Se rechaza el registro
- ✅ Email inválido → Se guarda como está (si existe)
- ✅ Teléfono = "0" → Se ignora
- ✅ Duplicados en Excel → Se usa el último registro
- ✅ Límites de crédito negativos → Se convierte a 0.0
- ✅ Descuentos > 100% → Se aceptan (sin limitación)

## Solución de problemas

### "Error: Cannot read module..."

Asegúrate de que `openpyxl` está instalado:

```bash
pip install openpyxl
```

### "No se encontraron registros válidos"

- Verifica que el archivo sea un Excel válido (.xlsx)
- Comprueba que la primera fila sea el encabezado
- Verifica que haya al menos una fila de datos

### "Duplicados en el Excel"

- El sistema keepa el último registro encontrado
- Los anteriores se sobrescriben con una advertencia

### "El cliente no se actualiza"

- Solo se actualizan los campos de contacto, teléfono, email, etc.
- El nombre y número de cliente NO se pueden cambiar (son clave)
- Las observaciones se concatenan con el histórico

## Seguridad

- Solo usuarios con permisos de **Manager de Ventas** pueden importar
- Todos los cambios quedan registrados en el histórico
- Se mantiene auditoría completa de cada operación

## Desarrollo futuro

Posibles mejoras:

- [ ] Importar productos y precios desde Todopintura
- [ ] Sincronización bidireccional
- [ ] Importación de pedidos/facturas
- [ ] Validación automática de impagos históricos
- [ ] Creación de alertas para clientes con riesgo

## Soporte

Para reportar errores o sugerencias:

- Contacta al equipo de desarrollo de Xtendoo
- Email: desarrollo@xtendoo.es

---

**Versión**: 19.0.1.0.0 **Autor**: Xtendoo **Licencia**: LGPL-3
