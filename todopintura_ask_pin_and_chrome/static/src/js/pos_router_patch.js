/** @odoo-module **/
console.info('[todopintura] pos_router_patch.js asset executing');
window.__TODOPINTURA_POS_ROUTER_PATCH_LOADED = true;
import { PosRouter } from "@point_of_sale/app/services/pos_router_service";
import { patch } from "@web/core/utils/patch";

// Estado sentinel para evitar retroceso
try {
    // Añadir un estado extra para que el historial tenga un entry de seguridad
    window.history.replaceState({ todopintura_sentinel: true }, '', window.location.href);
    window.history.pushState({ todopintura_sentinel: true }, '', window.location.href);
    console.info('[todopintura] sentinel history state pushed');
} catch (e) {
    console.error('[todopintura] could not push sentinel state:', e);
}

function _getPosModel() {
    return window.posmodel || window.pos || (window.odoo && window.odoo.pos) || null;
}

function hasOpenOrder() {
    try {
        const posmodel = _getPosModel();
        if (!posmodel) {
            return false;
        }
        // varios getters usados en distintos addons/versions
        if (typeof posmodel.get_order === 'function' && posmodel.get_order()) {
            return true;
        }
        if (typeof posmodel.getOrder === 'function' && posmodel.getOrder()) {
            return true;
        }
        if (posmodel.selectedOrderUuid) {
            return true;
        }
        if (posmodel.openOrder && Object.keys(posmodel.openOrder || {}).length) {
            return true;
        }
        // fallback: buscar en modelos pos.models['pos.order'] un open
        if (posmodel.models && posmodel.models['pos.order']) {
            try {
                const all = posmodel.models['pos.order'].getAll ? posmodel.models['pos.order'].getAll() : null;
                if (Array.isArray(all) && all.length) {
                    // comprobar si existe alguna abierta
                    for (const o of all) {
                        if (!o.finalized && o.state !== 'paid') {
                            return true;
                        }
                    }
                }
            } catch (e) {
                // ignore
            }
        }
    } catch (e) {
        console.error('[todopintura] error in hasOpenOrder:', e);
    }
    return false;
}

// --- NEW: global onbeforeunload handler to catch navigations that leave the document ---
try {
    const originalOnBeforeUnloadGlobal = window.onbeforeunload;
    window.__TODOPINTURA_ORIGINAL_ONBEFOREUNLOAD = originalOnBeforeUnloadGlobal;
    window.onbeforeunload = function (event) {
        try {
            if (hasOpenOrder()) {
                const message = '¿Seguro que deseas salir?';
                event.returnValue = message;
                console.debug('[todopintura] onbeforeunload: blocked navigation due to open order');
                return message;
            }
            if (originalOnBeforeUnloadGlobal && typeof originalOnBeforeUnloadGlobal === 'function') {
                return originalOnBeforeUnloadGlobal.call(window, event);
            }
        } catch (e) {
            console.error('[todopintura] error in global onbeforeunload handler:', e);
        }
        return undefined;
    };
    window.__TODOPINTURA_ONBEFOREUNLOAD_SET = true;
    console.info('[todopintura] global onbeforeunload handler set');
} catch (e) {
    console.error('[todopintura] could not set global onbeforeunload handler:', e);
}

// Handler de guard global (se registra ya al cargar el módulo)
function todopinturaGlobalGuard(event) {
    try {
        const hasOrder = hasOpenOrder();
        if (hasOrder) {
            console.debug('[todopintura] GLOBAL guard: bloqueo popstate por orden activa');
            if (event.stopImmediatePropagation) {
                event.stopImmediatePropagation();
            }
            // reinsertamos el sentinel state en la siguiente vuelta de loop para minimizar flicker
            setTimeout(() => {
                try {
                    // intentar avanzar en el historial para anular el retroceso
                    history.forward();
                    console.debug('[todopintura] GLOBAL guard: history.forward() llamado para anular popstate');
                } catch (e) {
                    console.error('[todopintura] error al pushState (global guard):', e);
                }
            }, 0);
        }
    } catch (e) {
        console.error('[todopintura] error en todopinturaGlobalGuard:', e);
    }
}

try {
    window.addEventListener('popstate', todopinturaGlobalGuard, true);
    window.__TODOPINTURA_GLOBAL_GUARD_ATTACHED = true;
    console.info('[todopintura] GLOBAL popstate guard attached (capture)');
} catch (e) {
    console.error('[todopintura] could not attach global popstate guard:', e);
}

// Wrap window.onpopstate (por si alguna parte del código usa asignación en lugar de addEventListener)
(function wrapOnPopState() {
    try {
        const originalOnPopState = window.onpopstate;
        window.__TODOPINTURA_ORIGINAL_ONPOPSTATE = originalOnPopState;
        window.onpopstate = function (event) {
            try {
                if (hasOpenOrder()) {
                    console.debug('[todopintura] window.onpopstate blocked due to open order');
                    try {
                        history.forward();
                        console.debug('[todopintura] window.onpopstate wrapper: history.forward() llamado');
                    } catch (e) {
                        console.error('[todopintura] error pushing sentinel in onpopstate wrapper:', e);
                    }
                    return;
                }
            } catch (e) {
                console.error('[todopintura] error in onpopstate wrapper:', e);
            }
            if (typeof originalOnPopState === 'function') {
                try {
                    return originalOnPopState.call(window, event);
                } catch (e) {
                    console.error('[todopintura] error calling original onpopstate:', e);
                }
            }
        };
        window.__TODOPINTURA_ONPOPSTATE_WRAPPED = true;
        console.info('[todopintura] window.onpopstate wrapped');
    } catch (e) {
        console.error('[todopintura] could not wrap window.onpopstate:', e);
    }
})();

// Guardamos referencia al setup original
const originalSetup = PosRouter.prototype.setup;

patch(PosRouter.prototype, {
    setup() {
        // Llamamos al setup original
        originalSetup.apply(this, arguments);

        console.debug('[todopintura] PosRouter patched - setup called');

        // Añadimos un listener en fase de captura que se ejecuta antes que
        // el listener por defecto del router. Si hay una orden activa, evitamos
        // que otros listeners manejen el evento y forzamos que la URL vuelva al estado actual.
        const guardHandler = (event) => {
            try {
                const hasOrder = hasOpenOrder();
                if (hasOrder) {
                    console.debug('[todopintura] pos_router guard: bloqueo popstate por orden activa');
                    if (event.stopImmediatePropagation) {
                        event.stopImmediatePropagation();
                    }
                    setTimeout(() => {
                        try {
                            history.forward();
                            console.debug('[todopintura] pos_router guard: history.forward() llamado para anular popstate');
                        } catch (e) {
                            console.error('[todopintura] error al pushState:', e);
                        }
                    }, 0);
                }
            } catch (e) {
                console.error('[todopintura] error en guardHandler:', e);
            }
        };

        try {
            window.addEventListener('popstate', guardHandler, true);
            this._todopintura_guardHandler = guardHandler;
            console.debug('[todopintura] pos_router guardHandler attached on this PosRouter instance');
        } catch (e) {
            console.error('[todopintura] no se pudo registrar guardHandler en popstate:', e);
        }
    },
    // Evitar que llamadas a router.back() hagan retroceso si hay orden activa
    back() {
        try {
            const hasOrder = hasOpenOrder();
            if (hasOrder) {
                console.debug('[todopintura] PosRouter.back bloqueado: orden activa');
                return;
            }
        } catch (e) {
            console.error('[todopintura] error comprobando orden en back():', e);
        }
        // Si no hay orden activa, delegamos al comportamiento por defecto
        history.back();
    },
});

// Wrap history.back and history.go to block programmatic back navigation when an order is open
(function wrapHistory() {
    try {
        const origBack = history.back.bind(history);
        const origGo = history.go.bind(history);
        history.back = function () {
            try {
                if (hasOpenOrder()) {
                    console.debug('[todopintura] history.back blocked due to open order');
                    return;
                }
            } catch (e) {
                console.error('[todopintura] error in history.back wrapper:', e);
            }
            return origBack();
        };
        history.go = function (delta) {
            try {
                if (delta < 0 && hasOpenOrder()) {
                    console.debug('[todopintura] history.go blocked (delta < 0) due to open order');
                    return;
                }
            } catch (e) {
                console.error('[todopintura] error in history.go wrapper:', e);
            }
            return origGo(delta);
        };
        console.info('[todopintura] history.back/go wrapped');
        window.__TODOPINTURA_HISTORY_WRAPPED = true;
    } catch (e) {
        console.error('[todopintura] could not wrap history methods:', e);
    }
})();

// Función de diagnóstico accesible desde la consola
window.__TODOPINTURA_DIAG = function () {
    return {
        chromeLoaded: !!window.__TODOPINTURA_CHROME_LOADED,
        posRouterPatchLoaded: !!window.__TODOPINTURA_POS_ROUTER_PATCH_LOADED,
        globalGuardAttached: !!window.__TODOPINTURA_GLOBAL_GUARD_ATTACHED,
        posmodel: _getPosModel(),
        hasOpenOrder: hasOpenOrder(),
        location: window.location.href,
    };
};
