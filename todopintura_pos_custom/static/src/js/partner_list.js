/** @odoo-module */

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";
import { debounce } from "@web/core/utils/timing";
import { _t } from "@web/core/l10n/translation";

// Guardamos referencia al método original ANTES del patch
const originalSetup = PartnerList.prototype.setup;

patch(PartnerList.prototype, {
    setup() {
        // Llamamos al setup original con el contexto correcto
        originalSetup.call(this);

         this.state.isLoading = false;
        this.state.visibleLimit = 20; // Mostrar solo 20 resultados inicialmente

        // Optimización del debounce
        this.debouncedSearch = debounce(this.performSearch.bind(this), 300);
    },

    // Override del método onEnter para usar nuestra función debounced
    async onEnter() {
        if (!this.state.query) {
            return;
        }
        // Cancelamos el debounce pendiente y ejecutamos inmediatamente
        this.debouncedSearch.cancel();
        this._performSearch();
    },

    // Nuevo método que maneja cambios en el campo de búsqueda
    onQueryInput(value) {
        this.state.query = value;
        this.debouncedSearch.cancel();

        if (value) {
            // Indicador de carga
            this.state.isLoading = true;
            this.render();

            this.debouncedSearch();
        } else {
            this.partners = [];
            this.state.isLoading = false;
            this.render();
        }
    },
    async performSearch() {
        const result = await this.searchPartner();
        this.state.isLoading = false;
        this.partners = result || [];
        this.render();
    },

    // Sobrescribimos searchPartner para evitar búsquedas cuando no hay texto
    async searchPartner() {
        // Si no hay consulta y no es la carga inicial, no hacemos nada
        if (!this.state.query && this.hasInitialSearch) {
            return [];
        }

        // Marcamos que ya pasamos por la carga inicial
        this.hasInitialSearch = true;

        // Ejecutamos la búsqueda normal
        return await super.searchPartner();
    },

    async getNewPartners() {
        const limit = 20; // Siempre limitamos a 20 para mejor rendimiento
        let domain = [];

        if (this.state.query) {
            domain = [["name", "ilike", this.state.query + "%"]];
        } else {
            // Si no hay búsqueda, mostrar menos resultados o lista vacía
            return [];
        }

        return this.pos.data.searchRead("res.partner", domain, [], {
            limit: limit,
            offset: this.state.currentOffset,
            order: "name ASC"
        });
    }
});
