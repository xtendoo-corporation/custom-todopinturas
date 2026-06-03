/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

console.log("TODOPINTURA: Barcode service loading...");

export const todopinturaBarcodeService = {
    dependencies: ["barcode", "orm", "action", "notification"],

    start(env, { barcode, orm, action, notification }) {
        console.log("TODOPINTURA: Barcode service started");
        console.log("TODOPINTURA: Dependencies:", { barcode, orm, action, notification });

        // Escuchar eventos de barcode
        barcode.bus.addEventListener("barcode_scanned", async (ev) => {
            const scannedBarcode = ev.detail.barcode;

            console.log("========================================");
            console.log("TODOPINTURA: BARCODE EVENT CAPTURED!");
            console.log("TODOPINTURA: Barcode:", scannedBarcode);
            console.log("TODOPINTURA: Target:", ev.detail.target);
            console.log("========================================");

            // Verificar si estamos en un formulario de stock.picking
            const currentController = env.services.action?.currentController;
            console.log("TODOPINTURA: Current controller:", currentController);

            if (!currentController) {
                console.log("TODOPINTURA: No current controller, ignoring barcode");
                return;
            }

            // Intentar múltiples formas de obtener el record
            let record = currentController.model?.root;

            // Si no hay root, intentar obtener desde props
            if (!record && currentController.props?.resModel && currentController.props?.resId) {
                console.log("TODOPINTURA: Getting record from controller props");
                console.log("TODOPINTURA: resModel:", currentController.props.resModel);
                console.log("TODOPINTURA: resId:", currentController.props.resId);

                const resModel = currentController.props.resModel;
                const resId = currentController.props.resId;

                if (resModel === "stock.picking" && resId) {
                    console.log("TODOPINTURA: We are in a stock.picking form!");
                    console.log("TODOPINTURA: Picking ID:", resId);
                    console.log("TODOPINTURA: Calling on_barcode_scanned via RPC...");

                    try {
                        // Llamar al método on_barcode_scanned directamente
                        const result = await orm.call(
                            "stock.picking",
                            "on_barcode_scanned",
                            [resId, scannedBarcode]
                        );

                        console.log("TODOPINTURA: RPC call successful!");
                        console.log("TODOPINTURA: Result:", result);

                        // Recargar la acción actual para mostrar los cambios
                        await action.doAction("reload");
                        console.log("TODOPINTURA: Action reloaded");

                        // Mostrar mensaje de éxito si hay un warning en el resultado
                        if (result && result.warning) {
                            notification.add(
                                result.warning.message,
                                {
                                    title: result.warning.title,
                                    type: "warning",
                                }
                            );
                        } else {
                            // Mostrar notificación de éxito
                            notification.add(
                                `Código ${scannedBarcode} escaneado correctamente`,
                                {
                                    type: "success",
                                }
                            );
                        }

                    } catch (error) {
                        console.error("TODOPINTURA: ERROR calling on_barcode_scanned:", error);
                        console.error("TODOPINTURA: Error details:", error.message, error.data);

                        notification.add(
                            error.message || "Error al procesar el código de barras",
                            {
                                type: "danger",
                            }
                        );
                    }
                } else {
                    console.log("TODOPINTURA: Not a stock.picking form, ignoring barcode");
                }
                return;
            }

            console.log("TODOPINTURA: Current record:", record);

            if (!record) {
                console.log("TODOPINTURA: No current record, ignoring barcode");
                return;
            }

            console.log("TODOPINTURA: Record resModel:", record.resModel);
            console.log("TODOPINTURA: Record resId:", record.resId);
            console.log("TODOPINTURA: Record data:", record.data);

            if (record.resModel === "stock.picking" && record.resId) {
                console.log("TODOPINTURA: We are in a stock.picking form!");
                console.log("TODOPINTURA: Picking ID:", record.resId);
                console.log("TODOPINTURA: Calling on_barcode_scanned via RPC...");

                try {
                    // Llamar al método on_barcode_scanned directamente
                    const result = await orm.call(
                        "stock.picking",
                        "on_barcode_scanned",
                        [record.resId, scannedBarcode]
                    );

                    console.log("TODOPINTURA: RPC call successful!");
                    console.log("TODOPINTURA: Result:", result);

                    // Recargar el registro para mostrar los cambios
                    await record.load();
                    console.log("TODOPINTURA: Record reloaded");

                    // Mostrar mensaje de éxito si hay un warning en el resultado
                    if (result && result.warning) {
                        notification.add(
                            result.warning.message,
                            {
                                title: result.warning.title,
                                type: "warning",
                            }
                        );
                    } else {
                        // Mostrar notificación de éxito
                        notification.add(
                            `Código ${scannedBarcode} escaneado correctamente`,
                            {
                                type: "success",
                            }
                        );
                    }

                } catch (error) {
                    console.error("TODOPINTURA: ERROR calling on_barcode_scanned:", error);
                    console.error("TODOPINTURA: Error details:", error.message, error.data);

                    notification.add(
                        error.message || "Error al procesar el código de barras",
                        {
                            type: "danger",
                        }
                    );
                }
            } else {
                console.log("TODOPINTURA: Not a stock.picking form, ignoring barcode");
            }
        });

        console.log("TODOPINTURA: Barcode event listener registered");
    },
};

registry.category("services").add("todopintura_barcode_service", todopinturaBarcodeService);

console.log("TODOPINTURA: Barcode service registered");

