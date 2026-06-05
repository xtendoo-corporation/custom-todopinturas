/** @odoo-module **/

import './stock_picking_barcode_refresh_field.js';

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

                        // Mostrar mensaje de éxito/warning
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
                                `✓ Cantidad actualizada`,
                                {
                                    type: "success",
                                }
                            );
                        }

                        // Recargar solo el registro actual sin recargar toda la página.
                        // Usamos una función que intenta varias rutas de recarga no disruptivas
                        console.log("TODOPINTURA: Attempting non-disruptive record reload...");
                        const reloadCurrentRecord = async () => {
                            try {
                                console.log("TODOPINTURA: currentController keys:", Object.keys(currentController || {}));
                                console.log("TODOPINTURA: currentController.props keys:", currentController?.props ? Object.keys(currentController.props) : null);
                                console.log("TODOPINTURA: currentController.view keys:", currentController?.view ? Object.keys(currentController.view) : null);
                                console.log("TODOPINTURA: currentController.renderer:", currentController?.renderer);
                                // debug: try to find any candidate object that looks like a record root
                                // 1) Si el controlador expone props.record (componentes que pasan record)
                                if (currentController.props && currentController.props.record) {
                                    console.log("TODOPINTURA: Reload via currentController.props.record.model.root.load()");
                                    await currentController.props.record.model.root.load();
                                    return true;
                                }
                                // 2) Si el controlador tiene model.root (form controllers)
                                if (currentController.model && currentController.model.root) {
                                    console.log("TODOPINTURA: Reload via currentController.model.root.load()");
                                    await currentController.model.root.load();
                                    return true;
                                }
                                // 2b) Try view.model.root
                                if (currentController.view && currentController.view.model && currentController.view.model.root) {
                                    console.log("TODOPINTURA: Reload via currentController.view.model.root.load()");
                                    await currentController.view.model.root.load();
                                    return true;
                                }
                                // 3) Si el renderer tiene props.record
                                if (currentController.renderer && currentController.renderer.props && currentController.renderer.props.record) {
                                    console.log("TODOPINTURA: Reload via currentController.renderer.props.record.model.root.load()");
                                    await currentController.renderer.props.record.model.root.load();
                                    return true;
                                }
                                // 4) Try to find any nested record-like object by scanning properties
                                for (const key of Object.keys(currentController || {})) {
                                    const cand = currentController[key];
                                    if (cand && cand.model && cand.model.root && typeof cand.model.root.load === 'function') {
                                        console.log(`TODOPINTURA: Reload via currentController.${key}.model.root.load()`);
                                        await cand.model.root.load();
                                        return true;
                                    }
                                }
                                console.log("TODOPINTURA: No known record object to reload");
                                return false;
                            } catch (err) {
                                console.error("TODOPINTURA: Error reloading record:", err);
                                return false;
                            }
                        };

                        try {
                            const reloaded = await reloadCurrentRecord();
                            // If we couldn't reload the record via OWL model, try a DOM-level optimistic update
                            if (!reloaded && result && result.updated && result.move_id) {
                                try {
                                    console.log("TODOPINTURA: Attempting DOM optimistic update for move", result.move_id);
                                    const moveRow = document.querySelector(`tr.o_data_row[data-id='${result.move_id}']`);
                                    if (moveRow) {
                                        const qtyCell = moveRow.querySelector("td[name='quantity']") || moveRow.querySelector("td[name=quantity]");
                                        if (qtyCell) {
                                            qtyCell.innerText = (typeof result.quantity === 'number') ? result.quantity.toFixed(2) : result.quantity;
                                            console.log("TODOPINTURA: DOM updated for move", result.move_id, "qty:", result.quantity);
                                        } else {
                                            console.log("TODOPINTURA: Could not find quantity cell in move row");
                                        }
                                    } else {
                                        console.log("TODOPINTURA: Could not find move row in DOM for move_id", result.move_id);
                                    }
                                } catch (domErr) {
                                    console.error("TODOPINTURA: Error performing DOM optimistic update:", domErr);
                                }
                            }
                        } catch (err) {
                            console.error("TODOPINTURA: Unexpected error during record reload:", err);
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

                    // Recargar el registro para mostrar los cambios (intentar varias formas no disruptivas)
                    // Recargar el registro para mostrar los cambios (intentar varias formas no disruptivas)
                    try {
                        let reloaded = false;
                        if (record && record.load) {
                            console.log("TODOPINTURA: Reload via record.load()");
                            await record.load();
                            reloaded = true;
                        } else if (currentController && currentController.model && currentController.model.root) {
                            console.log("TODOPINTURA: Fallback reload via currentController.model.root.load()");
                            await currentController.model.root.load();
                            reloaded = true;
                        }
                        console.log("TODOPINTURA: Record reload attempted, reloaded=", reloaded);
                        if (!reloaded && result && result.updated && result.move_id) {
                            // DOM optimistic update as fallback
                            try {
                                console.log("TODOPINTURA: Attempting DOM optimistic update for move", result.move_id);
                                const moveRow = document.querySelector(`tr.o_data_row[data-id='${result.move_id}']`);
                                if (moveRow) {
                                    const qtyCell = moveRow.querySelector("td[name='quantity']") || moveRow.querySelector("td[name=quantity]");
                                    if (qtyCell) {
                                        qtyCell.innerText = (typeof result.quantity === 'number') ? result.quantity.toFixed(2) : result.quantity;
                                        console.log("TODOPINTURA: DOM updated for move", result.move_id, "qty:", result.quantity);
                                    } else {
                                        console.log("TODOPINTURA: Could not find quantity cell in move row");
                                    }
                                } else {
                                    console.log("TODOPINTURA: Could not find move row in DOM for move_id", result.move_id);
                                }
                            } catch (domErr) {
                                console.error("TODOPINTURA: Error performing DOM optimistic update:", domErr);
                            }
                        }
                    } catch (err) {
                        console.error("TODOPINTURA: Error reloading record:", err);
                    }

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

