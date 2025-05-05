/** @odoo-module */
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { patch } from "@web/core/utils/patch";

console.log("🔍 Cargando extensión de ubicación para Orderline...");

patch(Orderline, {
    static: {
        template: "todopintura_pos_custom.Orderline",
        props: {
            ...Orderline.props,
            line: {
                ...Orderline.props.line,
                shape: {
                    ...Orderline.props.line.shape,
                    locationName: { type: String, optional: true },
                    locationId: { type: Number, optional: true },
                },
            },
        }
    },

    // Añade este método para gestionar propiedades personalizadas
    setCustomProperty(key, value) {
        this.props.line[key] = value;
        this.render(true); // Forzar renderizado
        return this;
    },

    setup() {
        const originalSetup = super.setup(...arguments);
        const line = this.props.line;

        // Depuración más detallada
        if (line) {
            console.log(`%c🔍 Datos de línea en setup:`, 'background: #f1c40f; color: black; padding: 2px 5px;');
            console.log({
                producto: line.productName,
                precio: line.unitPrice,
                cantidad: line.qty,
                ubicación: line.locationName,
                propiedades: Object.keys(line)
            });
        }

        return originalSetup;
    },

    mounted() {
        const original = super.mounted(...arguments);
        const line = this.props.line;

        // Verificar si la línea tiene la propiedad locationName
        if (line) {
            if (line.locationName) {
                console.log(`%c✅ Ubicación visible: ${line.productName} → ${line.locationName}`,
                    'background: #27ae60; color: white; padding: 2px 5px; border-radius: 3px;');
            } else {
                console.log(`%c❌ Línea sin ubicación: ${line.productName}`,
                    'background: #e74c3c; color: white; padding: 2px 5px; border-radius: 3px;');

                // Mostrar todas las propiedades para diagnóstico
                console.log("Propiedades disponibles:", Object.keys(line));
            }
        }

        return original;
    }
});

console.log("✅ Patch de Orderline aplicado correctamente");

export default Orderline;
