#!/usr/bin/env bash
# Instala la impresión de tickets TodoPintura para una Epson TM-T88IV (UB-U05, USB) en CUPS.
#
# Uso:  sudo ./install.sh [NOMBRE_COLA] [URI_USB]
#   NOMBRE_COLA  por defecto: TicketTPV
#   URI_USB      por defecto: la primera impresora usb:// que detecte CUPS
#                (p. ej. usb://Unknown/Printer o usb://EPSON/TM-T88IV?serial=XXXX)
# Para quitarlo:  sudo ./install.sh --remove [NOMBRE_COLA]
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
FILTER_DST=/usr/lib/cups/filter/pdf2escpos8
PPD_DIR=/usr/share/cups/model/todopintura
PPD_DST="$PPD_DIR/todopintura-ticket.ppd"
CONF_DST=/etc/todopintura-printer.conf

if [[ $EUID -ne 0 ]]; then
    echo "Ejecuta con sudo:  sudo $0 $*" >&2
    exit 1
fi

if [[ "${1:-}" == "--remove" ]]; then
    QUEUE="${2:-TicketTPV}"
    lpadmin -x "$QUEUE" 2>/dev/null || true
    rm -f "$FILTER_DST" "$PPD_DST"
    echo "Cola $QUEUE, filtro y PPD eliminados (se conserva $CONF_DST)."
    exit 0
fi

QUEUE="${1:-TicketTPV}"
URI="${2:-}"

echo "==> Instalando dependencias (python3-pil, poppler-utils, cups)"
apt-get install -y python3-pil poppler-utils cups >/dev/null

echo "==> Instalando filtro y PPD"
install -o root -g root -m 755 "$HERE/pdf2escpos8" "$FILTER_DST"
install -d -m 755 "$PPD_DIR"
install -o root -g root -m 644 "$HERE/todopintura-ticket.ppd" "$PPD_DST"
if [[ -f "$CONF_DST" ]] && ! cmp -s "$HERE/todopintura-printer.conf" "$CONF_DST"; then
    cp "$CONF_DST" "$CONF_DST.bak"
    echo "    (se sustituye $CONF_DST; copia anterior en $CONF_DST.bak)"
fi
install -o root -g root -m 644 "$HERE/todopintura-printer.conf" "$CONF_DST"

if [[ -z "$URI" ]]; then
    URI="$(lpinfo -v 2>/dev/null | awk '$2 ~ /^usb:\/\// {print $2; exit}')"
fi
if [[ -z "$URI" ]]; then
    echo "No se detecta ninguna impresora USB. Enciende la Epson ANTES de conectarla," >&2
    echo "comprueba 'lsusb | grep 04b8' y repite, o pasa la URI como segundo parámetro." >&2
    exit 1
fi

echo "==> Creando la cola $QUEUE en $URI"
lpadmin -p "$QUEUE" -E -v "$URI" -P "$PPD_DST" -o printer-is-shared=false
cupsenable "$QUEUE"
cupsaccept "$QUEUE"

echo
echo "Listo. En Chrome, al imprimir un ticket del TPV elige la impresora '$QUEUE'."
echo "Prueba: lp -d $QUEUE /usr/share/cups/data/testprint   (o imprime un ticket desde el TPV)"
echo "Ajustes de ancho/avance: $CONF_DST"
