# Módulo: todopintura_pos_custom_price

## Descripción
Este módulo permite definir precios personalizados al escanear productos en el Punto de Venta (POS).

## Estructura del Módulo

```
todopintura_pos_custom_price/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── product_category.py      # Añade campo pos_require_custom_price
│   └── pos_session.py            # Carga el campo en el POS
├── views/
│   └── product_category_views.xml  # Vista del campo en categoría
└── static/
    └── src/
        ├── js/
        │   └── product_screen.js    # Lógica del popup y precio personalizado
        └── xml/
            └── custom_price_popup.xml  # Template del popup
```

## Funcionalidades

### 1. Campo en Categoría de Producto
- Se añade el campo **"Requiere Precio Personalizado en POS"** en las categorías de producto
- Accesible desde: Inventario > Configuración > Categorías de Productos

### 2. Popup de Precio Personalizado
- Se muestra automáticamente al escanear un producto de una categoría marcada
- Permite introducir un precio personalizado
- Muestra información del producto
- Muestra información de descuentos aplicables

### 3. Aplicación Automática de Descuentos
- Verifica la lista de precios del cliente actual
- Aplica automáticamente los descuentos configurados en la lista de precios
- Soporta descuentos por:
  - Producto específico
  - Plantilla de producto
  - Categoría de producto
  - Descuento global

### 4. Integración con POS
- Compatible con Odoo 19
- Se integra con el flujo normal de escaneo de productos
- Actualiza la orden automáticamente con el precio y descuento

## Instalación

1. **Copiar el módulo** en la carpeta custom-todopinturas
2. **Actualizar lista de aplicaciones** en Odoo
3. **Instalar el módulo** "Todopintura POS Custom Price"
4. **Reiniciar la sesión de POS** para cargar los cambios

## Configuración

### Paso 1: Marcar Categorías
1. Ir a **Inventario > Configuración > Categorías de Productos**
2. Seleccionar la categoría deseada
3. Activar el campo **"Requiere Precio Personalizado en POS"**
4. Guardar

### Paso 2: Configurar Listas de Precios (Opcional)
1. Ir a **Ventas > Productos > Tarifas**
2. Seleccionar o crear una lista de precios
3. Añadir reglas de descuento según necesidad:
   - Por producto
   - Por categoría
   - Descuento global

## Uso en POS

1. **Abrir sesión de POS**
2. **Seleccionar un cliente** (opcional, pero recomendado para aplicar descuentos)
3. **Escanear un producto** de una categoría marcada
4. **Aparecerá el popup** de precio personalizado
5. **Introducir el precio** deseado
6. **Click en Confirmar**
7. El producto se añadirá con:
   - El precio introducido
   - El descuento de la lista de precios (si aplica)

## Ejemplo de Flujo

```
Usuario escanea producto "Pintura Especial"
↓
Sistema detecta que su categoría requiere precio personalizado
↓
Muestra popup "Introducir Precio Personalizado"
↓
Usuario introduce: 45.50 €
↓
Sistema verifica lista de precios del cliente "Juan Pérez"
↓
Encuentra descuento del 10% para esa categoría
↓
Añade producto con:
  - Precio base: 45.50 €
  - Descuento: 10%
  - Precio final: 40.95 €
```

## Detalles Técnicos

### Modelos Extendidos
- `product.category`: Añade campo `pos_require_custom_price`
- `pos.session`: Carga el campo en el POS

### Componentes JavaScript
- `CustomPricePopup`: Diálogo para introducir precio
- `ProductScreen`: Patch para interceptar escaneo de productos

### Métodos Principales
- `_onProductScan()`: Intercepta el escaneo
- `addProductWithCustomPrice()`: Añade producto con precio custom
- `checkPricelistDiscount()`: Verifica descuentos en lista de precios

## Compatibilidad
- Odoo 19 Enterprise/Community
- Compatible con otros módulos de todopintura_pos_*

## Notas Importantes

1. **Los descuentos se aplican sobre el precio introducido**, no sobre el precio original del producto
2. **Si no hay cliente seleccionado**, no se aplicarán descuentos de lista de precios
3. **El popup solo aparece para productos escaneados**, no para productos añadidos manualmente
4. **Se recomienda marcar solo las categorías necesarias** para no interrumpir el flujo normal

## Soporte y Mantenimiento
- Autor: Xtendoo
- Versión: 19.0.1.0.0
- Licencia: LGPL-3

