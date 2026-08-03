/**
 * Simple client-side filter for pricelist item one2many embedded list.
 * It hides/shows rows of the embedded list based on substring matches on the row text.
 * This is a lightweight UX enhancement without changing server side.
 */
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

/*
 * Patch ListRenderer to apply a simple client-side filter when the form contains
 * the `.todopintura-pricelist-filter` controls. This keeps the behaviour tightly
 * integrated with the list renderer and avoids global event handlers duplication.
 */
patch(ListRenderer.prototype, {
    setup() {
        if (super.setup) {
            super.setup();
        }
    },
    onPatched() {
        if (super.onPatched) {
            super.onPatched();
        }
        try {
            const form = this.tableRef.el.closest('form.o_form_view');
            if (!form) { return; }
            const filter = form.querySelector('.todopintura-pricelist-filter');
            if (!filter) { return; }

            // Avoid attaching handlers multiple times
            if (filter._todopintura_handlers_attached) {
                return;
            }

            let applyBtn = filter.querySelector('.todopintura-filter-apply');
            let clearBtn = filter.querySelector('.todopintura-filter-clear');
            let inputProduct = filter.querySelector('.search_product');
            let inputCateg = filter.querySelector('.search_categ');

            // If controls are not present in the XML (we inserted an empty div to avoid
            // view validation errors), create them dynamically in the DOM.
            if (!applyBtn) {
                const label = document.createElement('label');
                label.className = 'o_form_label';
                label.textContent = 'Buscar líneas:';
                filter.appendChild(label);

                // Row container for inputs (product + category) placed horizontally
                const inputsRow = document.createElement('div');
                inputsRow.style.display = 'flex';
                inputsRow.style.gap = '8px';
                inputsRow.style.alignItems = 'center';
                inputsRow.style.marginTop = '4px';

                inputProduct = document.createElement('input');
                inputProduct.type = 'text';
                inputProduct.className = 'form-control o_input search_product';
                inputProduct.placeholder = 'Producto (nombre o referencia)';
                inputProduct.style.flex = '1 1 60%';
                inputsRow.appendChild(inputProduct);

                inputCateg = document.createElement('input');
                inputCateg.type = 'text';
                inputCateg.className = 'form-control o_input search_categ';
                inputCateg.placeholder = 'Categoría';
                inputCateg.style.flex = '0 0 30%';
                inputsRow.appendChild(inputCateg);

                filter.appendChild(inputsRow);

                // Buttons row below inputs
                const buttonsRow = document.createElement('div');
                buttonsRow.style.marginTop = '6px';

                applyBtn = document.createElement('button');
                applyBtn.type = 'button';
                applyBtn.className = 'btn btn-primary todopintura-filter-apply';
                applyBtn.textContent = 'Aplicar';
                applyBtn.style.marginRight = '6px';
                buttonsRow.appendChild(applyBtn);

                clearBtn = document.createElement('button');
                clearBtn.type = 'button';
                clearBtn.className = 'btn btn-secondary todopintura-filter-clear';
                clearBtn.textContent = 'Limpiar';
                buttonsRow.appendChild(clearBtn);

                filter.appendChild(buttonsRow);
            }

            const applyFilter = () => {
                const product = (inputProduct && inputProduct.value || '').trim().toLowerCase();
                const categ = (inputCateg && inputCateg.value || '').trim().toLowerCase();
                const tbody = this.tableRef.el.querySelector('tbody');
                if (!tbody) { return; }
                for (const tr of tbody.querySelectorAll('tr')) {
                    const text = (tr.textContent || '').trim().toLowerCase();
                    let show = true;
                    if (product && text.indexOf(product) === -1) { show = false; }
                    if (categ && text.indexOf(categ) === -1) { show = false; }
                    tr.style.display = show ? '' : 'none';
                }
            };

            if (applyBtn) {
                applyBtn.addEventListener('click', applyFilter);
            }
            if (clearBtn) {
                clearBtn.addEventListener('click', function (){
                    if (inputProduct) { inputProduct.value = ''; }
                    if (inputCateg) { inputCateg.value = ''; }
                    applyFilter();
                });
            }

            filter._todopintura_handlers_attached = true;
        } catch (e) {
            // Fail silently to avoid breaking renderer on unexpected DOM
            console.error('todopintura pricelist filter error', e);
        }
    }
});


// Fallback approach: inject controls when placeholder div is present, using domReady
// Use native DOMContentLoaded instead of requiring odoo's dom_ready module
function onDomReady(cb) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', cb, { once: true });
    } else {
        cb();
    }
}

onDomReady(function (){
    function createControlsIfMissing(filter) {
        if (!filter || filter._todopintura_controls_created) { return; }
        try {


            const mkInput = (cls, placeholder, flex) => {
                const i = document.createElement('input');
                i.type = 'text';
                i.className = `form-control o_input ${cls}`;
                i.placeholder = placeholder;
                i.style.display = 'block';
                i.style.flex = flex;
                return i;
            };

            const label = document.createElement('label');
            label.className = 'o_form_label';
            label.textContent = 'Buscar líneas:';
            filter.appendChild(label);

            const inputsRow = document.createElement('div');
            inputsRow.style.display = 'flex';
            inputsRow.style.gap = '8px';
            inputsRow.style.alignItems = 'center';
            inputsRow.style.marginTop = '4px';

            const inputProduct = mkInput('search_product', 'Producto (nombre o referencia)', '1 1 60%');
            const inputCateg = mkInput('search_categ', 'Categoría', '0 0 30%');
            inputsRow.appendChild(inputProduct);
            inputsRow.appendChild(inputCateg);
            filter.appendChild(inputsRow);

            const mkBtn = (cls, text) => {
                const b = document.createElement('button');
                b.type = 'button';
                b.className = `btn ${cls}`;
                b.textContent = text;
                b.style.marginRight = '6px';
                return b;
            };

            const buttonsRow = document.createElement('div');
            buttonsRow.style.marginTop = '6px';
            const applyBtn = mkBtn('btn-primary todopintura-filter-apply', 'Aplicar');
            const clearBtn = mkBtn('btn-secondary todopintura-filter-clear', 'Limpiar');
            buttonsRow.appendChild(applyBtn);
            buttonsRow.appendChild(clearBtn);
            filter.appendChild(buttonsRow);

            const findTbody = () => {
                const form = filter.closest('form.o_form_view');
                if (form) {
                    return form.querySelector('.o_field_x2many .o_list_view tbody') || form.querySelector('.o_list_view tbody');
                }
                return document.querySelector('.o_field_x2many .o_list_view tbody') || document.querySelector('.o_list_view tbody');
            };

            const applyFilter = () => {
                const product = (inputProduct.value || '').trim().toLowerCase();
                const categ = (inputCateg.value || '').trim().toLowerCase();
                const tbody = findTbody();
                if (!tbody) { return; }
                for (const tr of tbody.querySelectorAll('tr')) {
                    const text = (tr.textContent || '').trim().toLowerCase();
                    let show = true;
                    if (product && text.indexOf(product) === -1) { show = false; }
                    if (categ && text.indexOf(categ) === -1) { show = false; }
                    tr.style.display = show ? '' : 'none';
                }
            };

            applyBtn.addEventListener('click', applyFilter);
            clearBtn.addEventListener('click', function (){
                inputProduct.value = '';
                inputCateg.value = '';
                applyFilter();
            });

            filter._todopintura_controls_created = true;
        } catch (e) {
            console.error('Error creating pricelist controls', e);
        }
    }

    function scanAndInject(root) {
        if (!root) { root = document.body; }
        const placeholders = Array.from(root.querySelectorAll('.todopintura-pricelist-filter'));
        for (const p of placeholders) { createControlsIfMissing(p); }
    }

    // initial
    scanAndInject(document.body);

    const mo = new MutationObserver(function (mutations) {
        for (const m of mutations) {
            for (const n of m.addedNodes) {
                if (n.nodeType === 1) { scanAndInject(n); }
            }
        }
    });
    mo.observe(document.body, { childList: true, subtree: true });
});



