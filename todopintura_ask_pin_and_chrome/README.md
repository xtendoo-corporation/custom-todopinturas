# Módulo: todopintura_ask_pin_and_chrome

## Descripción
Este módulo modifica el comportamiento del POS de Odoo 19 Enterprise para:

1. **Prevenir navegación hacia atrás** desde el POS
2. **Mostrar advertencia** al intentar salir o recargar la página con una orden activa
3. **Solicitar PIN del empleado** al crear una nueva venta (después de la primera)

## Características Principales

### 1. Chrome Modifications (`chrome.js`)
- Previene la navegación hacia atrás usando `history.pushState`
- Implementa un manejador `onbeforeunload` para advertir al salir
- Preserva el comportamiento original si ya había un manejador

### 2. Router Patch (`pos_router_patch.js`)
- Implementa un guard global para prevenir retroceso con orden activa
- Gestiona el estado sentinel del historial
- Maneja múltiples métodos para detectar órdenes abiertas

### 3. Solicitud de PIN al Crear Nueva Venta (`ask_pin_new_order.js`)

#### Funcionamiento:
1. **Primera venta**: No se solicita PIN (comportamiento normal)
2. **Ventas siguientes**: Al hacer clic en "Nueva Venta" o botón "+":
   - Se muestra un popup con la lista de empleados
   - El empleado debe seleccionarse (obligatorio)
   - Si tiene PIN configurado, se solicita
   - El popup **NO se puede cerrar** sin seleccionar un empleado válido

#### Características:
- **No se puede cancelar**: Los popups no tienen botón de cancelar
- **Validación de PIN**: Si el PIN es incorrecto, vuelve a solicitarlo
- **Bucle obligatorio**: El usuario debe completar el proceso
- **Máximo de intentos**: 100 intentos para evitar bucles infinitos
- **Mensajes de error**: Claros y en español

### 4. Patch de Popups (`popup_no_close_patch.js`)

#### Funcionamiento:
- Patchea `AbstractAwaitablePopup` para bloquear el cierre
- Detecta popups de selección de empleado/PIN
- Previene:
  - Cerrar con ESC
  - Cerrar haciendo click fuera
  - Cerrar con el botón X
- Solo activo cuando `window.__TODOPINTURA_BLOCK_POPUP_CLOSE = true`

## Flujo de Trabajo

```
Usuario hace clic en "Nueva Venta"
    ↓
¿Es la primera venta?
    ↓ No
Activar bloqueo de cierre de popups
    ↓
Mostrar lista de empleados (obligatorio)
    ↓
Usuario selecciona empleado
    ↓
¿Tiene PIN?
    ↓ Sí
Solicitar PIN (obligatorio)
    ↓
¿PIN correcto?
    ↓ No → Volver a solicitar
    ↓ Sí
Establecer empleado como cajero
    ↓
Desactivar bloqueo de cierre
    ↓
Crear nueva orden
```

## Configuración

### Requisitos:
- Odoo 19 Enterprise
- Módulos: `point_of_sale`, `l10n_es_pos`

### Instalación:
1. Copiar el módulo a `custom/src/custom-todopinturas/`
2. Actualizar la lista de módulos
3. Instalar `todopintura_ask_pin_and_chrome`

### Configuración de Empleados:
1. Ir a **Empleados** → **Configuración**
2. Para cada empleado, establecer un **PIN** en la pestaña de POS
3. Los empleados sin PIN pueden usarse, pero se solicita confirmación

## Archivos del Módulo

```
todopintura_ask_pin_and_chrome/
├── __init__.py
├── __manifest__.py
└── static/
    └── src/
        └── js/
            ├── chrome.js                   # Modificaciones del Chrome
            ├── pos_router_patch.js         # Prevención de navegación
            ├── popup_no_close_patch.js     # Bloqueo de cierre de popups
            └── ask_pin_new_order.js        # Solicitud de PIN
```

## Notas Técnicas

### Variables Globales:
- `window.__TODOPINTURA_CHROME_LOADED`: Indica que chrome.js se cargó
- `window.__TODOPINTURA_POS_ROUTER_PATCH_LOADED`: Indica que pos_router_patch.js se cargó
- `window.__TODOPINTURA_BLOCK_POPUP_CLOSE`: Activa/desactiva el bloqueo de cierre de popups
- `isRequestingPin`: Previene solicitudes concurrentes de PIN

### Compatibilidad:
- Compatible con Odoo 19 Enterprise
- Usa el sistema de patches moderno de Odoo
- Implementa hooks de OWL (onMounted, onWillUnmount)

## Seguridad

- **PIN obligatorio**: Solo los empleados con credenciales válidas pueden crear ventas
- **No se puede omitir**: El flujo es obligatorio y no se puede cancelar
- **Trazabilidad**: Se registra en consola cada cambio de empleado

## Mantenimiento

### Logs de Consola:
- `[todopintura] addNewOrder interceptado`: Se interceptó la creación de orden
- `[todopintura] Solicitando PIN para nueva orden`: Se inició el proceso de PIN
- `[todopintura] Empleado seleccionado: XXX`: Se seleccionó un empleado válido
- `[todopintura] Bloqueando cierre de popup`: Se bloqueó el intento de cerrar

### Troubleshooting:

**Problema**: El popup se puede cerrar
- **Solución**: Verificar que `popup_no_close_patch.js` se carga antes que `ask_pin_new_order.js`

**Problema**: No se solicita PIN
- **Solución**: Verificar que hay órdenes existentes en el sistema

**Problema**: Error "No hay empleados disponibles"
- **Solución**: Verificar que hay empleados configurados en el sistema

## Autor
Abraham (Xtendoo)

## Licencia
LGPL-3

