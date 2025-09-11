# Todo Pintura POS Interface Custom

Este módulo personaliza completamente la interfaz del Point of Sale (POS) de Odoo 18 para Todo Pintura, optimizando el espacio de pantalla y mejorando la experiencia del usuario.

## Características Principales

### 🚫 Ocultar Productos y Categorías
- **Problema resuelto**: El área de productos y categorías que ocupa gran parte de la pantalla ahora está oculta por defecto
- **Beneficio**: Se libera aproximadamente el 60% del espacio de pantalla para información más útil

### 📊 Área de Pedido Ampliada
- **Líneas de pedido más grandes**: Cada línea ahora muestra más información y es más fácil de leer
- **Información adicional**: Se muestra referencia interna, categoría y margen de cada producto
- **Mejor visualización**: Las líneas seleccionadas se destacan visualmente

### 👤 Información Extendida del Cliente
- **Datos completos**: Nombre, email, teléfono, NIF/CIF, dirección completa
- **Información comercial**: Tarifa aplicada, límite de crédito, deuda pendiente
- **Alertas visuales**: Avisos cuando el cliente tiene deuda o supera límites

### 💳 Botones de Pago Mejorados
- **Tamaño aumentado**: Botones más grandes y fáciles de usar
- **Mejor diseño**: Colores y efectos visuales mejorados
- **Información adicional**: Estadísticas del pedido (cantidad de artículos, total, etc.)

### 📈 Información de Negocio
- **Márgenes**: Cálculo y visualización del margen de cada línea
- **Estadísticas**: Resumen del pedido con totales y promedios
- **Costos**: Información de precios de costo (si está disponible)

## Instalación

1. **Ubicación del módulo**: El módulo ya está en la ruta correcta:
   ```
   /odoo/custom/src/custom-todopinturas/todopintura_pos_interface_custom/
   ```

2. **Instalar el módulo**:
   - Ir a Apps en Odoo
   - Buscar "Todo Pintura POS Interface Custom"
   - Hacer clic en "Instalar"

3. **Reiniciar el servicio** (si es necesario):
   ```bash
   sudo systemctl restart odoo
   ```

## Estructura del Módulo

```
todopintura_pos_interface_custom/
├── __init__.py
├── __manifest__.py
├── views/
│   ├── pos_assets.xml
│   └── pos_templates.xml
└── static/
    └── src/
        ├── css/
        │   ├── pos_custom.css
        │   └── pos_enhanced.css
        └── js/
            ├── pos_custom.js
            └── pos_extended.js
```

## Funcionalidades Detalladas

### Vista Principal
- **Panel izquierdo ampliado**: Ocupa el 100% de la pantalla
- **Panel derecho oculto**: Los productos y categorías están ocultos
- **Botón de alternancia**: Posibilidad de mostrar/ocultar productos temporalmente

### Información del Cliente
```
┌─────────────────────────────────────┐
│ 👤 Juan Pérez Martínez              │
│ ✉️  juan.perez@email.com             │
│ 📞 +34 600 123 456                  │
│ 🏢 12345678A                        │
│ 📍 Calle Principal, 123, Madrid     │
│ 🏷️  Tarifa: Clientes Especiales     │
│ 💰 Límite: €5,000.00               │
│ ⚠️  Deuda: €1,200.00                │
└─────────────────────────────────────┘
```

### Líneas de Pedido Mejoradas
```
┌─────────────────────────────────────┐
│ Pintura Blanca Premium              │
│ Ref: PAINT-001 | Cat: Pinturas      │
│ 2.5 ud × €25.50 = €63.75          │
│ Margen: 35.2%                       │
└─────────────────────────────────────┘
```

### Estadísticas del Pedido
```
┌─────────────────────────────────────┐
│ 📦 Artículos: 8                     │
│ 📊 Cantidad total: 15.5 ud          │
│ 👤 Cliente: Juan Pérez               │
│ 💰 Total: €245.80                   │
└─────────────────────────────────────┘
```

## Personalización

### Modificar Colores
Editar el archivo `static/src/css/pos_custom.css`:
```css
/* Cambiar color principal */
.customer-info-extended {
    border-left: 4px solid #TU_COLOR_AQUI;
}
```

### Agregar Más Información
Modificar `static/src/js/pos_extended.js` para incluir campos adicionales del cliente.

### Mostrar/Ocultar Elementos
Comentar o descomentar secciones en los archivos CSS para personalizar qué elementos se muestran.

## Compatibilidad

- **Odoo**: Versión 18.0
- **Módulos requeridos**: point_of_sale
- **Navegadores**: Chrome, Firefox, Safari, Edge (versiones recientes)
- **Dispositivos**: Optimizado para pantallas táctiles y de escritorio

## Soporte y Mantenimiento

### Logs y Debugging
Para revisar posibles errores:
```bash
tail -f /var/log/odoo/odoo.log | grep pos_interface_custom
```

### Limpiar Cache
Si los cambios no se reflejan:
1. Ir a Configuración > Técnico > Vistas
2. Buscar vistas relacionadas con POS
3. Hacer clic en "Regenerar"

### Desinstalar
1. Ir a Apps
2. Buscar "Todo Pintura POS Interface Custom"
3. Hacer clic en "Desinstalar"

## Notas Importantes

⚠️ **Backup**: Siempre realiza un backup antes de instalar nuevos módulos
⚠️ **Testing**: Prueba el módulo en un entorno de desarrollo antes de producción
⚠️ **Usuarios**: Informa a los usuarios sobre los cambios en la interfaz

## Licencia

Este módulo es propietario de Todo Pintura y está diseñado específicamente para sus necesidades comerciales.
