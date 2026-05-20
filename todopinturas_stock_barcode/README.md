# Todopinturas Stock Barcode

Módulo para gestionar solicitudes de reposición al almacén central desde las tiendas como movimientos internos de `stock.picking`. La seguridad específica por almacén se añadirá en una fase posterior.

> Estado actual: el módulo queda temporalmente sin grupos ni reglas personalizadas.
> Primero se deja estable la parte funcional y más adelante se reintroducirá la seguridad específica de Todopinturas.

## Qué incluye

- Vista dentro de `Xtendoo Barcode` para revisar solicitudes al almacén central.
- Las solicitudes se interpretan como movimientos internos cuyo origen está en el almacén central.
- Vista rápida en kanban/lista agrupable por tienda destino y estado.
- Marca de almacén central en `stock.warehouse`.
- Flujo simple sin grupos personalizados por ahora.

## Configuración mínima

1. Marcar un almacén con `Almacén central para solicitudes`.
2. Crear o revisar movimientos internos con origen en ese almacén central.
3. No es necesario configurar grupos personalizados en esta fase.

