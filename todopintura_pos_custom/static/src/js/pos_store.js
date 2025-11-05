/** @odoo-module */
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { CouponAndAssignedPeopleDialog } from "./coupon_and_assigned_people";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";

const originalSetup = PosStore.prototype.setup;
patch(PosStore.prototype, {

    async selectPartner() {
        // Obtener la orden actual usando la API de Odoo 19
        const currentOrder = this.models["pos.order"].get(this.selectedOrderUuid);
        if (!currentOrder) {
            return false;
        }
        const currentPartner = currentOrder.partner_id;
        if (currentPartner && currentOrder.getHasRefundLines()) {
            this.dialog.add(AlertDialog, {
                title: _t("Can't change customer"),
                body: _t(
                    "This order already has refund lines for %s. We can't change the customer associated to it. Create a new order for the new customer.",
                    currentPartner.name
                ),
            });
            return currentPartner;
        }
        const payload = await makeAwaitable(this.dialog, PartnerList, {
            partner: currentPartner,
            getPayload: (newPartner) => {
                currentOrder.partner_id = newPartner;
                return newPartner;
            },
        });


        let newPartner = false;
        if (payload) {
        // Verificar si el cliente tiene personas asignadas o vales
        console.log("Payload:", payload);
        const tienePersonasAsignadas = payload.assigned_persons_info;
        const tieneVales = payload.voucher;
        console.log("Tiene personas asignadas:", tienePersonasAsignadas);
        console.log("Tiene vales:", tieneVales);
        console.log("Campo voucher:", payload.voucher);
        console.log("Campo assigned_persons:", payload.assigned_persons);
        console.log("Campo credit_sale:", payload.credit_sale);
        console.log("Nombre de ubicación:", payload.credit_location_id_name);
        if (payload.credit_sale) {
            console.log("Cliente con venta a crédito", payload.credit_location_id_name);

            try {
                const result = await this.env.services.orm.call(
                    'res.partner',
                    'check_credit_location_matches_pos',
                    [[payload.id], this.config.id]
                );

                console.log("Resultado verificación de ubicación:", result);

                // Guardar la información de coincidencia en el objeto cliente
                payload.credit_location_mismatch = !result.matches;

                if (!result.matches) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Ubicación incorrecta para realizar venta a crédito"),
                        body: _t("La ubicación de crédito del cliente (" + result.partner_location_name +
                              ") no coincide con la ubicación de esta caja (" + result.pos_location_name + "). En esta tienda no se puede realizar venta a crédito a este cliente."),
                    });
                }
            } catch (error) {
                console.error("Error al verificar ubicación:", error);
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t("No se pudo verificar la ubicación de crédito."),
                });
            }
        }
    // Mostrar el diálogo si tiene personas asignadas O vales
    if (tienePersonasAsignadas || tieneVales) {
        try {
            // Verificamos qué servicios están disponibles
            console.log("this.dialog:", this.dialog);
            console.log("this.env:", this.env);
            console.log("this.env?.services:", this.env?.services);

            const option = await new Promise(resolve => {
                this.dialog.add(CouponAndAssignedPeopleDialog, {
                    partner: payload,
                    assignedPeopleInfo: tienePersonasAsignadas || false, // Pasamos la información de personas asignadas o false
                    confirm: resolve,
                    close: () => resolve(false)
                });
            });
        } catch (error) {
            console.error("Error al mostrar el diálogo:", error);
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("No se pudo mostrar el diálogo: ") + (error.message || error),
            });
        }
    }

        newPartner = payload;
        currentOrder.partner_id = newPartner;
    } else {
        currentOrder.partner_id = false;
    }

    return currentPartner;
    },
    async ready() {
        const result = await this._super(...arguments);

        const allPartners = this.models["res.partner"].getAll();
        console.log(`Cargados ${allPartners.length} contactos al inicio`);

        if (allPartners.length < 1000) {
            try {
                await this.data.loadPartnersBackground();
                const partnersAfterLoad = this.models["res.partner"].getAll();
            } catch (error) {
                console.error("Error al cargar contactos:", error);
            }
        }

        return result;
    },

    async getProductInfo(product, quantity, priceExtra = 0) {
        // Obtener la orden actual usando la API de Odoo 19
        const order = this.models["pos.order"].get(this.selectedOrderUuid);
        if (!order) {
            return { productInfo: null };
        }

        // Mantenemos la llamada al backend para obtener información del producto
        const productInfo = await this.data.call("product.product", "get_product_info_pos", [
            [product.id],
            product.get_price(order.pricelist_id, quantity, priceExtra),
            quantity,
            this.config.id,
        ]);

        // Solo devolvemos la información del producto que contiene datos de stock
        return {
            productInfo,
        };
    },
     get firstScreen() {
        if (odoo.from_backend) {
            const url = new URL(window.location.href);
            url.searchParams.delete("from_backend");
            window.history.replaceState({}, "", url);
        }
        return "ProductScreen";
    },
    async setup() {
        await originalSetup.call(this, ...arguments);
        this.employeeBuffer = [];
        window.addEventListener("online", () => {
            this.employeeBuffer.forEach((employee) =>
                this.data.write("pos.session", [this.config.current_session_id.id], {
                    employee_id: employee.id,
                })
            );
            this.employeeBuffer = [];
        });
    },
});
