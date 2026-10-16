# Todopintura User Groups

Grupos de permisos de usuario de Todopintura, según el documento "menus de usuarios".

- **9 grupos de bloque** (texto en negrita del documento), cada uno en su propio
  privilegio de la categoría *Todopintura*, de modo que un usuario puede tener varios.
- **54 grupos de permiso** (cada opción del documento: V01ALM, M02P, VA03…). Cada bloque
  implica los permisos de su lista. Los permisos con el mismo código se comparten.
- `group_todopintura_restricted`: grupo técnico que implican todos los bloques.

## Qué limita a un usuario con estos grupos (admin excluido)

1. **Menús** (`models/ir_ui_menu.py`): solo ve los menús asignados a sus permisos
   (`data/res_groups.xml`, sección de menús) y sus menús padre.
2. **Modelos** (`models/ir_model_access.py`): solo puede leer/escribir/crear/borrar los
   modelos concedidos por las ACL de sus permisos (`security/ir.model.access.csv`).
   Los modelos de infraestructura (mail, ir.*, wizards…) quedan exentos.
3. Los grupos estándar mínimos que cada permiso necesita (vendedor, usuario de almacén,
   compras, TPV) se implican por `implied_ids`, de modo que se mantienen sus reglas de
   registro (p. ej. el vendedor solo ve sus propios pedidos).

## Limitaciones conocidas

- El control de escritura es por modelo, no por campo (M020 permite escribir en producto).
- `RC00 Rutas de comerciales` no tiene equivalente en Odoo: el grupo existe sin menú.
- Para añadir un permiso nuevo: ampliar el diccionario de mapeo, regenerar y ejecutar los tests.

## Tests

    odoo -d <db> -u todopintura_user_groups --test-tags /todopintura_user_groups --stop-after-init
