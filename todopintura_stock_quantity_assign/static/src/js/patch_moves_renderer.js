/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { useService, useBus } from "@web/core/utils/hooks";

// We cannot import core stock modules by path inside our asset bundle. Instead
// we look up the registered field component for 'stock_move_one2many' and
// retrieve its ListRenderer class to patch it at runtime. This keeps the
// modification inside the custom module and avoids touching core files.
const fieldDesc = registry.category("fields").get("stock_move_one2many");
const MovesListRenderer = fieldDesc?.component?.components?.ListRenderer;
if (MovesListRenderer) {
    const _origSetup = MovesListRenderer.prototype.setup;
    patch(MovesListRenderer.prototype, {
        setup() {
            if (typeof _origSetup === "function") {
                _origSetup.apply(this, arguments);
            }
            try {
                // useService/useBus are OWL hooks and valid inside component setup
                this.barcode = useService("barcode");
                this._barcodeReloadScheduled = false;
                useBus(this.barcode.bus, "barcode_scanned", async () => {
                    if (this._barcodeReloadScheduled) {
                        return;
                    }
                    this._barcodeReloadScheduled = true;
                    setTimeout(async () => {
                        try {
                            if (this.env?.model?.root) {
                                await this.env.model.root.load();
                            }
                        } catch (e) {
                            console.warn("todopintura: error reloading picking after barcode:", e);
                        } finally {
                            this._barcodeReloadScheduled = false;
                        }
                    }, 200);
                });
                console.log("todopintura: MovesListRenderer barcode subscription installed");
            } catch (err) {
                console.debug("todopintura: could not install barcode subscription on MovesListRenderer", err);
            }
        },
    }, "todopintura.patch_moves_renderer");
} else {
    // If the field isn't registered yet at asset evaluation time, retry once
    // shortly after. This handles ordering issues between bundles.
    const tryLater = () => {
        const desc = registry.category("fields").get("stock_move_one2many");
        const R = desc?.component?.components?.ListRenderer;
        if (R) {
            const _origSetup = R.prototype.setup;
            patch(R.prototype, {
                setup() {
                    if (typeof _origSetup === "function") {
                        _origSetup.apply(this, arguments);
                    }
                    try {
                        this.barcode = useService("barcode");
                        this._barcodeReloadScheduled = false;
                        useBus(this.barcode.bus, "barcode_scanned", async () => {
                            if (this._barcodeReloadScheduled) {
                                return;
                            }
                            this._barcodeReloadScheduled = true;
                            setTimeout(async () => {
                                try {
                                    if (this.env?.model?.root) {
                                        await this.env.model.root.load();
                                    }
                                } catch (e) {
                                    console.warn("todopintura: error reloading picking after barcode:", e);
                                } finally {
                                    this._barcodeReloadScheduled = false;
                                }
                            }, 200);
                        });
                        console.log("todopintura: MovesListRenderer barcode subscription installed (deferred)");
                    } catch (err) {
                        console.debug("todopintura: deferred install failed", err);
                    }
                },
            }, "todopintura.patch_moves_renderer");
        } else {
            setTimeout(tryLater, 500);
        }
    };
    setTimeout(tryLater, 200);
}

