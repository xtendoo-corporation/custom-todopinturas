/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { Dialog } from "@web/core/dialog/dialog";
import { useState, useRef, onMounted } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

// Componente del popup para precio personalizado
export class CustomPricePopup extends Dialog {
    static template = 'todopintura_pos_custom_price.CustomPricePopup';
    static components = { Dialog };

    static props = {
        product: { type: Object },
        partner: { type: Object, optional: true },
        pricelist: { type: Object, optional: true },
        confirm: { type: Function },
        close: { type: Function },
        // Props requeridas por Dialog
        title: { type: String, optional: true },
        body: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };

    setup() {
        super.setup();

        this.state = useState({
            customPrice: 0,
            discountInfo: '',
        });

        this.priceInput = useRef("priceInput");

        onMounted(() => {
            // Enfocar el input al abrir el popup
            if (this.priceInput.el) {
                this.priceInput.el.focus();
                this.priceInput.el.select();
            }
        });
    }

    async confirmPrice() {
        const customPrice = parseFloat(this.state.customPrice);

        if (isNaN(customPrice) || customPrice <= 0) {
            return;
        }

        // Calcular el descuento si existe
        let finalPrice = customPrice;
        let discount = 0;

        if (this.props.pricelist && this.props.partner) {
            // Verificar si hay descuento en la lista de precios
            const discountData = await this.getDiscountForProduct(
                this.props.product.id,
                this.props.pricelist.id,
                customPrice
            );

            if (discountData && discountData.discount > 0) {
                discount = discountData.discount;
                finalPrice = customPrice; // El descuento se aplicará en la línea
            }
        }

        this.props.confirm({
            price: customPrice,
            discount: discount,
        });

        this.props.close();
    }

    async getDiscountForProduct(productId, pricelistId, basePrice) {
        // Esta función verificaría en la lista de precios si hay descuento
        // Por ahora retornamos null, se puede implementar con una llamada RPC si es necesario
        return null;
    }
}

// Patch del ProductScreen para interceptar cuando se añade un producto
patch(ProductScreen.prototype, {
    setup() {
        super.setup();
        this.pos_user_can_edit_price = false;
        this.dialog = useService("dialog");

        // Usar onMounted para interceptar el barcode reader cuando todo esté listo
        onMounted(() => {
            const pos = this.env.services.pos;
            // Cargar permisos desde el módulo todopintura_extend_pos_conventional
            (async () => {
                try {
                    const res = await fetch('/todopintura_extend_pos_conventional/user_permissions', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({}),
                    });
                    const data = await res.json();
                    this.pos_user_can_edit_price = !!data.pos_can_edit_price;
                    console.debug('[CUSTOM PRICE] pos_user_can_edit_price=', this.pos_user_can_edit_price);
                } catch (e) {
                    console.warn('[CUSTOM PRICE] No se pudo cargar permisos de usuario:', e);
                    this.pos_user_can_edit_price = false;
                }
            })();
            if (pos && pos.barcodeReader) {
                // Guardar referencia al método original
                const originalScan = pos.barcodeReader.scan;
                if (originalScan) {
                    // Reemplazar el método scan
                    pos.barcodeReader.scan = async (code) => {
                        // Intentar interceptar si es un producto
                        if (pos?.models?.['product.product']) {
                            const productModel = pos.models['product.product'];
                            let products = [];

                            if (productModel.records instanceof Map) {
                                products = Array.from(productModel.records.values());
                            } else if (productModel.records) {
                                products = Object.values(productModel.records);
                            }

                            const searchCode = typeof code === 'string' ? code : code.code;
                            const product = products.find(p => p.barcode === searchCode || p.default_code === searchCode);

                            if (product) {
                                // Si el usuario no tiene permiso, no mostramos el popup de precio
                                if (!this.pos_user_can_edit_price) {
                                    return originalScan.call(pos.barcodeReader, code);
                                }

                                const shouldShow = await this.shouldShowCustomPricePopup(product);
                                if (shouldShow) {
                                    await this.showCustomPricePopup(product);
                                    return; // No llamar al método original
                                }
                            }
                        }

                        // Llamar al método original si no se interceptó
                        return originalScan.call(pos.barcodeReader, code);
                    };
                }
            }
        });
    },


    // Método auxiliar para verificar si debe mostrar el popup
    async shouldShowCustomPricePopup(product) {
        const pos = this.env.services.pos;
        let requireCustomPrice = false;

        // Verificar si la categoría requiere precio personalizado
        const category = product.categ_id;

        if (category && pos.models && pos.models['product.category']) {
            // Extraer el ID correctamente - en Odoo 19 puede ser un Proxy object
            let categoryId;
            if (typeof category === 'object' && category.id !== undefined) {
                categoryId = category.id;
            } else if (Array.isArray(category)) {
                categoryId = category[0];
            } else {
                categoryId = category;
            }

            const categoryModel = pos.models['product.category'];
            let allCategories = [];

            if (categoryModel.records instanceof Map) {
                allCategories = Array.from(categoryModel.records.values());
            } else if (categoryModel.records) {
                allCategories = Object.values(categoryModel.records);
            }

            const categoryData = categoryModel.get ? categoryModel.get(categoryId) :
                                allCategories.find(c => c.id === categoryId);

            if (categoryData) {
                requireCustomPrice = categoryData.pos_require_custom_price || false;
                if (requireCustomPrice) {
                    console.log('[CUSTOM PRICE] ✅ Categoría requiere precio personalizado:', categoryData.name);
                }
            }
        }

        return requireCustomPrice;
    },

    // Método auxiliar para mostrar el popup
    async showCustomPricePopup(product) {
        const pos = this.env.services.pos;

        // Obtener el cliente y lista de precios actuales
        const order = pos.get_order ? pos.get_order() :
                     (pos.selectedOrderUuid && pos.models['pos.order']?.get(pos.selectedOrderUuid));

        const partner = order?.partner_id ?
            (pos.models['res.partner']?.get(
                Array.isArray(order.partner_id) ? order.partner_id[0] : order.partner_id
            )) : null;

        const pricelist = order?.pricelist_id ?
            (pos.models['product.pricelist']?.get(
                Array.isArray(order.pricelist_id) ? order.pricelist_id[0] : order.pricelist_id
            )) : null;

        console.log('[CUSTOM PRICE] 🎯 Mostrando popup para:', product.display_name);

        try {
            return new Promise((resolve) => {
                this.dialog.add(CustomPricePopup, {
                    product: product,
                    partner: partner,
                    pricelist: pricelist,
                    slots: {},
                    confirm: async (priceData) => {
                        await this.addProductWithCustomPrice(product, priceData.price, priceData.discount);
                        resolve(true);
                    },
                    close: () => {
                        resolve(false);
                    },
                });
            });
        } catch (error) {
            console.error('[CUSTOM PRICE] ❌ ERROR al mostrar popup:', error);
            return super._onProductScan(...arguments);
        }
    },

    async addProductWithCustomPrice(product, customPriceWithTax, discount) {
        const pos = this.env.services.pos;

        // Protección cliente: si el usuario no tiene permiso, no permitir añadir con precio personalizado
        if (!this.pos_user_can_edit_price) {
            this.env.services.notification.add(_t('No tienes permiso para modificar precios en TPV'), { type: 'warning' });
            return;
        }

        if (!pos) {
            console.error('[CUSTOM PRICE] ❌ POS no disponible');
            return;
        }

        // Obtener la orden actual
        const order = pos.get_order ? pos.get_order() :
                     (pos.selectedOrderUuid && pos.models['pos.order']?.get(pos.selectedOrderUuid));

        if (!order) {
            console.error('[CUSTOM PRICE] ❌ No hay orden activa');
            return;
        }

        // PASO 1: Obtener la tasa de IVA del producto
        let taxRate = 0;
        if (product.taxes_id && product.taxes_id.length > 0) {
            let taxId = Array.isArray(product.taxes_id) ? product.taxes_id[0] : product.taxes_id;

            // Extraer el ID si es un Proxy object
            if (typeof taxId === 'object' && taxId.id !== undefined) {
                taxId = taxId.id;
            }

            if (pos.models && pos.models['account.tax']) {
                const taxModel = pos.models['account.tax'];
                let tax = null;

                if (taxModel.records instanceof Map) {
                    tax = taxModel.records.get(taxId);
                } else if (taxModel.get) {
                    tax = taxModel.get(taxId);
                }

                if (tax) {
                    taxRate = tax.amount || 0;
                }
            }
        }

        // PASO 2: CALCULAR PRECIO BASE SIN IVA
        const taxMultiplier = 1 + (taxRate / 100);
        const priceBase = customPriceWithTax / taxMultiplier;

        console.log('[CUSTOM PRICE] ═══════════════════════════════════════');
        console.log('[CUSTOM PRICE] 💰 PRECIO INTRODUCIDO (con IVA):', customPriceWithTax.toFixed(2), '€');
        console.log('[CUSTOM PRICE] 📊 IVA:', taxRate + '%');
        console.log('[CUSTOM PRICE] 📝 Precio base (sin IVA):', priceBase.toFixed(2), '€');

        // PASO 3: Verificar si hay descuento en la lista de precios
        let pricelistDiscount = discount || 0;

        if (!pricelistDiscount || pricelistDiscount === 0) {
            pricelistDiscount = await this.checkPricelistDiscount(product, order, priceBase);
        }

        // CÁLCULO FINAL
        const discountMultiplier = 1 - (pricelistDiscount / 100);
        const priceAfterDiscount = priceBase * discountMultiplier;
        const totalWithTax = priceAfterDiscount * taxMultiplier;

        if (pricelistDiscount > 0) {
            console.log('[CUSTOM PRICE] 🎯 Descuento aplicado:', pricelistDiscount + '%');
        }
        console.log('[CUSTOM PRICE] 💵 TOTAL FINAL (con IVA):', totalWithTax.toFixed(2), '€');
        console.log('[CUSTOM PRICE] ═══════════════════════════════════════');

        // PASO 4: Añadir la línea al pedido
        try {
            if (typeof order.add_product === 'function') {
                order.add_product(product, {
                    quantity: 1,
                    price: priceBase,
                    discount: pricelistDiscount,
                });
            } else if (order.lines && pos.models['pos.order.line']) {
                const Line = pos.models['pos.order.line'];
                Line.create({
                    order_id: order,
                    product_id: product,
                    qty: 1,
                    price_unit: priceBase,
                    discount: pricelistDiscount,
                });
            } else {
                console.error('[CUSTOM PRICE] ❌ No se encontró método para añadir producto');
            }

            this.env.services.notification.add(
                _t('✅ Producto añadido - Total: ') + totalWithTax.toFixed(2) + '€',
                { type: 'success' }
            );

        } catch (error) {
            console.error('[CUSTOM PRICE] ❌ Error:', error);
            this.env.services.notification.add(
                _t('Error al añadir el producto'),
                { type: 'danger' }
            );
        }
    },

    async checkPricelistDiscount(product, order, basePrice) {
        const pos = this.env.services.pos;

        // Obtener la lista de precios del pedido
        let pricelistId = order?.pricelist_id ?
            (Array.isArray(order.pricelist_id) ? order.pricelist_id[0] : order.pricelist_id) : null;

        // Extraer ID si es un Proxy object
        if (typeof pricelistId === 'object' && pricelistId?.id !== undefined) {
            pricelistId = pricelistId.id;
        }

        if (!pricelistId) {
            console.log('[CUSTOM PRICE] ⚠️ No hay lista de precios asignada al pedido');
            return 0;
        }

        // Obtener nombre de la pricelist
        const pricelistModel = pos.models['product.pricelist'];
        let pricelistName = 'Desconocida';
        if (pricelistModel?.records instanceof Map) {
            const pricelistRecord = pricelistModel.records.get(pricelistId);
            pricelistName = pricelistRecord?.name || `ID: ${pricelistId}`;
        }

        console.log('[CUSTOM PRICE] 🔍 Buscando descuento en pricelist:', pricelistName, `(ID: ${pricelistId})`);

        // Buscar items de lista de precios para este producto
        if (pos.models && pos.models['product.pricelist.item']) {
            const itemsModel = pos.models['product.pricelist.item'];
            let items = [];

            // Obtener items desde Map o records
            if (itemsModel.records instanceof Map) {
                items = Array.from(itemsModel.records.values());
            } else if (itemsModel.records) {
                items = Object.values(itemsModel.records);
            }

            // Extraer IDs de los campos relacionados del producto
            let productCategId = product.categ_id;
            if (typeof productCategId === 'object' && productCategId?.id !== undefined) {
                productCategId = productCategId.id;
            } else if (Array.isArray(productCategId)) {
                productCategId = productCategId[0];
            }

            let productTmplId = product.product_tmpl_id;
            if (typeof productTmplId === 'object' && productTmplId?.id !== undefined) {
                productTmplId = productTmplId.id;
            } else if (Array.isArray(productTmplId)) {
                productTmplId = productTmplId[0];
            }


            // Filtrar items que apliquen a este producto y lista de precios
            const applicableItems = items.filter(item => {
                // Extraer IDs del item
                let itemPricelistId = item.pricelist_id;
                if (typeof itemPricelistId === 'object' && itemPricelistId?.id !== undefined) {
                    itemPricelistId = itemPricelistId.id;
                } else if (Array.isArray(itemPricelistId)) {
                    itemPricelistId = itemPricelistId[0];
                }

                // Verificar si aplica a esta lista de precios
                if (itemPricelistId !== pricelistId) {
                    return false;
                }

                // Extraer IDs de producto/template/categoría del item
                let itemProductId = item.product_id;
                if (typeof itemProductId === 'object' && itemProductId?.id !== undefined) {
                    itemProductId = itemProductId.id;
                } else if (Array.isArray(itemProductId)) {
                    itemProductId = itemProductId[0];
                }

                let itemProductTmplId = item.product_tmpl_id;
                if (typeof itemProductTmplId === 'object' && itemProductTmplId?.id !== undefined) {
                    itemProductTmplId = itemProductTmplId.id;
                } else if (Array.isArray(itemProductTmplId)) {
                    itemProductTmplId = itemProductTmplId[0];
                }

                let itemCategId = item.categ_id;
                if (typeof itemCategId === 'object' && itemCategId?.id !== undefined) {
                    itemCategId = itemCategId.id;
                } else if (Array.isArray(itemCategId)) {
                    itemCategId = itemCategId[0];
                }

                // Verificar aplicabilidad
                if (itemProductId && itemProductId === product.id) {
                    return true;
                }

                if (itemProductTmplId && itemProductTmplId === productTmplId) {
                    return true;
                }

                if (itemCategId && itemCategId === productCategId) {
                    return true;
                }

                if (item.applied_on === '3_global') {
                    return true;
                }

                return false;
            });


            if (applicableItems.length > 0) {
                // Usar el primer item encontrado (podríamos ordenar por prioridad)
                const item = applicableItems[0];

                // ACCEDER DIRECTAMENTE A LAS PROPIEDADES (no usar Object.keys por ser Proxy)
                const computePrice = item.compute_price;
                const percentPrice = item.percent_price;
                const priceDiscount = item.price_discount;
                const fixedPrice = item.fixed_price;
                const base = item.base;
                const basePricelistId = item.base_pricelist_id;

                // Determinar qué tipo de aplicación es
                let aplicationType = 'Desconocido';
                if (item.product_id) {
                    aplicationType = 'Producto específico';
                } else if (item.product_tmpl_id) {
                    aplicationType = 'Template de producto';
                } else if (item.categ_id) {
                    aplicationType = 'Categoría';
                } else if (item.applied_on === '3_global') {
                    aplicationType = 'Global';
                }

                console.log('[CUSTOM PRICE] ═══════════════════════════════════════');
                console.log('[CUSTOM PRICE] 📋 ITEM ENCONTRADO EN PRICELIST');
                console.log('[CUSTOM PRICE] ═══════════════════════════════════════');
                console.log('[CUSTOM PRICE] Tipo de aplicación:', aplicationType);
                console.log('[CUSTOM PRICE] Método de cálculo (compute_price):', computePrice);
                console.log('[CUSTOM PRICE] Base de cálculo (base):', base);

                // BUSCAR DESCUENTO EN TODOS LOS CAMPOS POSIBLES
                let discount = 0;

                // 1. Descuento directo (percent_price)
                if (percentPrice && percentPrice > 0) {
                    discount = percentPrice;
                    console.log('[CUSTOM PRICE] ✅ Descuento encontrado en percent_price:', discount + '%');
                    return discount;
                }

                // 2. Descuento en fórmula (price_discount)
                if (priceDiscount && priceDiscount > 0) {
                    discount = priceDiscount;
                    console.log('[CUSTOM PRICE] ✅ Descuento encontrado en price_discount:', discount + '%');
                    return discount;
                }

                // 3. Precio fijo - calcular descuento equivalente
                if (fixedPrice && fixedPrice > 0 && basePrice > 0) {
                    if (fixedPrice < basePrice) {
                        discount = ((basePrice - fixedPrice) / basePrice) * 100;
                        console.log('[CUSTOM PRICE] ✅ Descuento calculado desde fixed_price:', discount + '%');
                        return discount;
                    }
                }

                // 4. Si usa base de otra lista de precios - BÚSQUEDA RECURSIVA
                if (base === 'pricelist' && basePricelistId) {
                    // Extraer el ID de la pricelist base
                    let basePricelistIdNum = basePricelistId;
                    if (typeof basePricelistIdNum === 'object' && basePricelistIdNum?.id !== undefined) {
                        basePricelistIdNum = basePricelistIdNum.id;
                    } else if (Array.isArray(basePricelistIdNum)) {
                        basePricelistIdNum = basePricelistIdNum[0];
                    }

                    // Obtener nombre de la pricelist base
                    let basePricelistName = `ID: ${basePricelistIdNum}`;
                    if (pricelistModel?.records instanceof Map) {
                        const basePricelistRecord = pricelistModel.records.get(basePricelistIdNum);
                        basePricelistName = basePricelistRecord?.name || basePricelistName;
                    }

                    console.log('[CUSTOM PRICE] 🔗 Buscando en pricelist base:', basePricelistName);

                    // BUSCAR RECURSIVAMENTE en la pricelist base
                    const baseItems = items.filter(baseItem => {
                        // Extraer ID de pricelist del item base
                        let baseItemPricelistId = baseItem.pricelist_id;
                        if (typeof baseItemPricelistId === 'object' && baseItemPricelistId?.id !== undefined) {
                            baseItemPricelistId = baseItemPricelistId.id;
                        } else if (Array.isArray(baseItemPricelistId)) {
                            baseItemPricelistId = baseItemPricelistId[0];
                        }

                        // Debe pertenecer a la pricelist base
                        if (baseItemPricelistId !== basePricelistIdNum) {
                            return false;
                        }

                        // Extraer IDs para comparar
                        let baseItemProductId = baseItem.product_id;
                        if (typeof baseItemProductId === 'object' && baseItemProductId?.id !== undefined) {
                            baseItemProductId = baseItemProductId.id;
                        } else if (Array.isArray(baseItemProductId)) {
                            baseItemProductId = baseItemProductId[0];
                        }

                        let baseItemProductTmplId = baseItem.product_tmpl_id;
                        if (typeof baseItemProductTmplId === 'object' && baseItemProductTmplId?.id !== undefined) {
                            baseItemProductTmplId = baseItemProductTmplId.id;
                        } else if (Array.isArray(baseItemProductTmplId)) {
                            baseItemProductTmplId = baseItemProductTmplId[0];
                        }

                        let baseItemCategId = baseItem.categ_id;
                        if (typeof baseItemCategId === 'object' && baseItemCategId?.id !== undefined) {
                            baseItemCategId = baseItemCategId.id;
                        } else if (Array.isArray(baseItemCategId)) {
                            baseItemCategId = baseItemCategId[0];
                        }

                        // Verificar si aplica al producto
                        return (baseItemProductId && baseItemProductId === product.id) ||
                               (baseItemProductTmplId && baseItemProductTmplId === productTmplId) ||
                               (baseItemCategId && baseItemCategId === productCategId) ||
                               (baseItem.applied_on === '3_global');
                    });

                    if (baseItems.length > 0) {
                        const baseItem = baseItems[0];
                        const basePercentPrice = baseItem.percent_price;
                        const basePriceDiscount = baseItem.price_discount;

                        // Buscar descuento en el item base
                        if (basePercentPrice && basePercentPrice > 0) {
                            discount = basePercentPrice;
                            console.log('[CUSTOM PRICE] ✅ DESCUENTO ENCONTRADO:', discount + '% en', basePricelistName);
                            console.log('[CUSTOM PRICE] ═══════════════════════════════════════');
                            return discount;
                        }

                        if (basePriceDiscount && basePriceDiscount > 0) {
                            discount = basePriceDiscount;
                            console.log('[CUSTOM PRICE] ✅ DESCUENTO ENCONTRADO:', discount + '% en', basePricelistName);
                            console.log('[CUSTOM PRICE] ═══════════════════════════════════════');
                            return discount;
                        }

                        console.log('[CUSTOM PRICE] ⚠️ Item encontrado en pricelist base pero sin descuento');
                    } else {
                        console.log('[CUSTOM PRICE] ⚠️ No se encontraron items aplicables en pricelist base');
                    }

                    console.log('[CUSTOM PRICE] ═══════════════════════════════════════');
                    return 0;
                }

                console.log('[CUSTOM PRICE] ⚠️ No se encontró descuento aplicable en el item');
                console.log('[CUSTOM PRICE] ═══════════════════════════════════════');
                return 0;
            }
        } else {
            console.log('[CUSTOM PRICE] ⚠️ No hay modelo product.pricelist.item disponible');
        }

        console.log('[CUSTOM PRICE] No se encontró descuento aplicable');
        return 0;
    },
});

console.log('[CUSTOM PRICE] Módulo cargado correctamente');

