# Todopintura User Groups

Perfiles de usuario, menús del cliente, permisos, reglas por almacén y TPV de Todopintura
(Odoo 19 Community). Toda la configuración está versionada con ID externo: se puede
reinstalar, actualizar (`-u`) y migrar sin duplicar ni perder nada.

## Perfiles

Cada usuario tiene **un único perfil** (categoría de seguridad *Todopintura*). Cada perfil
implica los grupos granulares (uno por pantalla del menú del cliente), el grupo técnico
`Todopintura: acceso limitado a sus permisos` y los grupos estándar mínimos de Odoo.

| Perfil | Menú raíz | Pantallas |
|---|---|---|
| Pedidos de clientes | Pedidos de clientes | Grabación de ventas, Consulta de ofertas, Consulta de precios, Consulta de existencias, Reimpresión de documentos, Consulta de clientes |
| Pedidos de y para tiendas | Pedidos de y para tiendas | Reposición semanal, Partes de movimiento, Actualización de existencias (*), Reimpresión de partes, Traspasos entre sucursales |
| Entradas de proveedor | Entradas de proveedor | Pedidos a proveedores, Repaso, Vuelco a pendientes, Existencias, Control de stock, Búsqueda de artículo, Códigos de barras, Bajo mínimos + precio de proveedor, Precios y tarifas |
| Ventas de almacén central | Ventas de almacén central | Grabación de ventas (TPV, solo las cajas autorizadas del usuario), Cuadre de caja, Consulta de precios, Existencias, Reimpresión + submenú *Traspasos y ventas de otras tiendas* |
| Traspasos y ventas de otras tiendas (almacén central) | Ventas de almacén central | Solo el submenú de traspasos |
| Ventas de POS | Ventas de POS | Solo TPV (sin presupuestos ni pedidos de venta): TPV, Cuadre de caja, Precios, Existencias, Reimpresión de tickets, Ventas acumuladas, Ventas a cuenta, submenú *Traspasos…* (sin ofertas por compras), *Consulta varias* |
| Traspasos y ventas de otras tiendas (tiendas) | Ventas de POS | Submenú de traspasos y *Consulta varias* |
| Comerciales | Comerciales | Gestión de ofertas, Ofertas por compras, Informes estadísticos, Mantenimiento de clientes, Rutas, Ofertas outlets, Existencias, Consulta de clientes |
| Informes estadísticos | Comerciales | Todo lo de Comerciales salvo Gestión de ofertas y Ofertas por compras |
| Dirección | Todos | Implica los nueve perfiles, ve todas las ventas y parametriza comisiones |

(*) Pendiente de validar con el cliente: se mapea al ajuste de inventario físico.

Los menús estándar de Odoo **no** se muestran a estos perfiles (solo a administradores de
Ajustes): `models/ir_ui_menu.py` filtra los menús por los grupos Todopintura del usuario.
`models/ir_model_access.py` limita además el acceso a modelos a los concedidos en
`security/ir.model.access.csv`.

## Permisos transversales

* **Crear/modificar clientes**: Comerciales, Ventas de POS y Dirección. El resto, solo consulta
  (vistas de solo lectura en `views/actions.xml`).
* **Códigos de barras, precios y tarifas**: solo Entradas de proveedor y Dirección
  (`perm_m020` y `perm_pricelist_maintenance`).
* **Costes, precios de proveedor y márgenes**: solo quien tiene el grupo
  `Todopintura: ver costes, precios de proveedor y márgenes` (Entradas de proveedor, Dirección y
  administradores). Se oculta en las vistas de producto, variantes, proveedor, valoración de
  stock y pedido TPV (`views/cost_views.xml`) y, a nivel de campo, en `margin`/`margin_percent`
  de pedidos y líneas de TPV y en el informe de TPV (`models/pos_order.py`), de modo que no
  aparecen como medida en pivote ni gráfico. El coste total almacenado de la línea TPV solo se
  oculta en la vista porque se escribe al crear los pedidos.
* **Comerciales**: ven todos los clientes pero solo sus ofertas, pedidos e informes (reglas
  estándar del grupo «Vendedor: documentos propios»). Dirección tiene «todos los documentos».

## Almacenes permitidos por usuario

Campo `allowed_warehouse_ids` (Ajustes › Usuarios › pestaña *Derechos de acceso*, justo antes de
los grupos). Con el campo **vacío no hay restricción**. Con almacenes asignados, cuatro reglas
globales (`security/ir_rule.xml`) limitan:

* `stock.picking`: el almacén del tipo de operación, o el de la ubicación origen, o el de la
  destino. Así los traspasos entre tiendas los ven origen y destino.
* `sale.order`: `warehouse_id`.
* `pos.order` y `pos.session`: almacén del tipo de operación del TPV.

Un usuario no puede ampliar sus propios almacenes (solo administradores).

## Datos

* `data/pos_config.xml` (noupdate): 9 almacenes (central + 8 tiendas) y sus 10 TPV (central
  Caja 1 y Caja 2, y uno por tienda) con el tipo de operación *Pedidos de TPV* de su almacén.
  El almacén «Ecopintura» **no** se toca.
* `data/pricelist_outlet.xml` (noupdate): tarifa «Ofertas clientes/outlets».
* `data/weekday.xml`: días de visita.

## Desarrollos a medida

* **Rutas de comerciales**: modelo `todopintura.route` (zona + comercial responsable), campos
  `route_id` y `visit_day_ids` en el cliente y planificación semanal (pivote/lista) por comercial
  y día en *Comerciales › Rutas de comerciales*.
* **Ventas para comisiones**: informe SQL `todopintura.commission.report` por comercial y mes.
  La regla de cálculo está **pendiente**: `todopintura.commission.rate` permite un porcentaje por
  comercial, por categoría o por ambos (el más específico prevalece, con periodo opcional). No se
  entrega ningún porcentaje: sin parametrizar la comisión es 0.
* **Historial de compras**: botón en la oferta que abre las líneas de pedido ya entregadas o
  facturadas del cliente (y sus contactos) agrupadas por producto. Sin duplicar datos.
* **Venta con recogida en otra tienda** y **ventas a cuenta**: ya existen en
  `todopintura_extend_pos_conventional` (`pickup_warehouse_id`, traspaso diferido ligado al pedido
  TPV, política de crédito por ubicación). No se duplican aquí; ver el resumen de entrega.

## Migración de lo creado a mano (adoptar, no sustituir)

`hooks.py` (`pre_init_hook` en instalación y `migrations/19.0.1.1.0/pre-migration.py` en
actualización) asigna ID externo, por nombre, a los registros creados por RPC (categoría,
privilegios, grupos, menús por ruta, reglas basadas en `x_warehouse_ids`, ACL por modelo+grupo,
almacenes —también a través de su TPV—, TPV y tarifa). Después los datos del módulo los actualizan
en lugar de duplicarlos. La parte posterior (`post_init_hook` / `post-migration.py`) copia
`x_warehouse_ids` en `allowed_warehouse_ids` y elimina el campo manual y su vista. Todo es
idempotente. Un registro con nombre ambiguo no se adopta y queda un `WARNING` en el log.

Antes de actualizar producción: probar en una copia, revisar el log (`hooks: ... not adopted`) y
comprobar que los nombres de almacenes/TPV coinciden con `data/pos_config.xml`.

## Tests

```bash
odoo -d <db> -i todopintura_user_groups --test-enable \
     --test-tags /todopintura_user_groups --stop-after-init
```

Cubren matriz de accesos por perfil, menús visibles, reglas por almacén, costes ocultos,
adopción/migración, rutas, comisiones e historial de compras.
