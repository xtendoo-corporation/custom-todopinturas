# Todopintura Stock Min Lines

Extiende **Transferencias internas** (`xtendoo_stock_barcode`) con la reposición bajo mínimos.

## Flujo
1. En «Transferencias internas» se elige el almacén (diálogo «Seleccionar Almacén»).
2. Al continuar se carga, en un traslado de reposición **almacén central → almacén elegido**,
   una línea por cada producto que ahora mismo está **bajo su mínimo** en ese almacén
   (puntos de pedido: `stock.warehouse.orderpoint`).
3. La pantalla PDA muestra un aviso con los productos bajo mínimos y, en cada línea:
   existencias del almacén destino, mínimo y cantidad a enviar.

## Reglas
- **A enviar** = mínimo − existencias del destino − lo que ya va en camino, sin pasar de lo
  disponible en el almacén central (el almacén marcado «Es Almacén Central (Hub)»).
- Si no hay stock en central, la línea no se carga y el aviso lo indica.
- Si el almacén elegido es el central, no hay reposición.
- Entrar otra vez en el mismo almacén **reutiliza** el traslado: añade lo nuevo, ajusta las
  líneas sin escanear y retira las que ya no están bajo mínimos. Las líneas con algo
  escaneado no se tocan.
- Escanear un producto que no está bajo mínimos avisa («No está bajo mínimos en X»), pero
  se puede añadir.
- El formulario del traslado muestra las mismas columnas en sus líneas.
