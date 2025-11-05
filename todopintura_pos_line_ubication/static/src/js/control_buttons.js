/** @odoo-module */
import { patch } from "@web/core/utils/patch";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { _t } from "@web/core/l10n/translation";
import { LocationLineDialog } from "./location_line_dialog";
import { useService } from "@web/core/utils/hooks";

patch(ControlButtons.prototype, {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.notification = useService("notification");
    },

    async changeUbicationLine() {
        const pos = this.env?.services?.pos;

        if (!pos) {
            console.error('[UBICACION] POS no disponible');
            return;
        }

        // Obtener el pedido actual
        const order = pos.models?.['pos.order']?.get(pos.selectedOrderUuid);

        if (!order) {
            this.notification.add(_t("No hay pedido activo"), { type: "warning" });
            return;
        }

        // Obtener la línea seleccionada
        let selectedLine = null;
        if (order.uiState?.selected_orderline_uuid && order.lines) {
            const selectedLineUuid = order.uiState.selected_orderline_uuid;
            const linesArray = Object.values(order.lines);
            selectedLine = linesArray.find(line => line.uuid === selectedLineUuid);
        }

        if (!selectedLine) {
            this.notification.add(_t("Seleccione una línea de pedido"), { type: "warning" });
            return;
        }

        try {
            let locations = [];

            // ESTRATEGIA 1: Obtener desde pos.models si está disponible
            if (pos.models?.['stock.location']) {
                const allLocations = pos.models['stock.location'].getAll();
                locations = allLocations.filter(loc => {
                    const isInternal = loc.usage === 'internal';
                    const isStock = loc.complete_name && (
                        loc.complete_name.includes('Stock') ||
                        loc.complete_name.includes('stock') ||
                        loc.name?.includes('Stock') ||
                        loc.name?.includes('stock')
                    );
                    return isInternal && isStock;
                });
            }

            // ESTRATEGIA 2: Cargar desde el servidor
            if (locations.length === 0) {
                try {
                    const allLocations = await this.env.services.orm.searchRead(
                        'stock.location',
                        [
                            ['usage', '=', 'internal'],
                            '|',
                            ['name', 'ilike', 'Stock'],
                            ['complete_name', 'ilike', 'Stock']
                        ],
                        ['id', 'name', 'complete_name']
                    );

                    locations = allLocations.filter(loc =>
                        loc.complete_name?.includes('Stock') ||
                        loc.complete_name?.includes('stock') ||
                        loc.name?.includes('Stock') ||
                        loc.name?.includes('stock')
                    );
                } catch (error) {
                    console.error('[UBICACION] Error al cargar ubicaciones:', error);
                    // Fallback
                    locations.push({
                        id: 1,
                        name: 'Stock',
                        complete_name: 'WH/Stock'
                    });
                }
            }

            if (locations.length === 0) {
                this.notification.add(_t("No hay ubicaciones disponibles."), { type: "warning" });
                return;
            }

            // Mostrar el diálogo
            await new Promise(resolve => {
                this.dialog.add(LocationLineDialog, {
                    locations: locations,
                    currentLocationId: selectedLine.locationData?.id || locations[0].id,
                    inventoryData: {},
                    confirm: (locationData) => {
                        if (selectedLine.set_location) {
                            selectedLine.set_location(locationData.id, locationData.name);
                        } else {
                            selectedLine.locationData = locationData;
                        }
                        this.notification.add(_t("Ubicación actualizada"), { type: "success" });
                        resolve(true);
                    },
                    close: () => resolve(false)
                });
            });

        } catch (error) {
            console.error("[UBICACION] Error:", error);
            this.notification.add(_t("Error al cambiar la ubicación"), { type: "danger" });
        }
    },
});


