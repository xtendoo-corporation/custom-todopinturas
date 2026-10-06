from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    invoice_description = fields.Char(string="Invoice description", help="Invoice description")
    size_id = fields.Many2one('product.size', string='Tamaño', index=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ProductTemplate, self).default_get(fields_list)
        if 'route_ids' in fields_list:
            routes = self.env['stock.route'].search([('product_selectable', '=', True)])
            res['route_ids'] = [(6, 0, routes.ids)]
        # Valores por defecto en el formulario Nuevo Producto.
        # OJO: 'available_in_pos' e 'is_storable' tienen su propio default
        # (False) en sus módulos de origen, así que super() YA los deja en
        # `res` con valor False -- comprobar "not in res" nunca se cumple.
        # Hay que forzar el valor, no solo rellenar si falta la clave.
        if 'available_in_pos' in fields_list:
            res['available_in_pos'] = True
        # Rastrear inventario (is_storable) activado por defecto, para que
        # se vea la cantidad real (On Hand) desde el propio formulario Nuevo.
        if 'is_storable' in fields_list:
            res['is_storable'] = True

        # Nota: las líneas de tarifa no están mapeadas como un one2many directo en
        # product.template por defecto (son registros en product.pricelist.item),
        # por lo que no se pueden precrear fácilmente en el formulario sin
        # modificar la vista. Se crearán en el hook create() cuando el producto
        # se guarde (implementado en create()).
        if 'invoice_policy' in fields_list and 'invoice_policy' not in res:
            res['invoice_policy'] = 'delivery'
        # Nota: las líneas de tarifa no están mapeadas como un one2many directo en
        # product.template por defecto (son registros en product.pricelist.item),
        # por lo que no se pueden precrear fácilmente en el formulario sin
        # modificar la vista. Se crearán en el hook create() cuando el producto
        # se guarde.
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # Ensure sensible defaults for newly created products
        prepared = []
        for vals in vals_list:
            v = dict(vals)
            # Debug: mostrar los valores entrantes para cada create
            try:
                print('product.template.create incoming vals:', vals)
            except Exception:
                pass
            # Forzar available_in_pos a True para todos los productos creados
            v['available_in_pos'] = True
            # Rastrear inventario (cantidad real / On Hand visible) siempre
            # activado, igual que available_in_pos -- salvo para servicios,
            # donde no aplica y Odoo lo desactiva solo de todas formas.
            if v.get('type', 'consu') == 'consu':
                v['is_storable'] = True
            # política de facturación por entrega
            if 'invoice_policy' not in v:
                v['invoice_policy'] = 'delivery'
            prepared.append(v)

        records = super(ProductTemplate, self).create(prepared)

        # Asegurar que las variantes (product.product) también queden disponibles en POS
        try:
            variants = records.mapped('product_variant_ids')
            if variants:
                variants.write({'available_in_pos': True})
        except Exception:
            # no bloquear la creación si por alguna razón no se puede escribir en variantes
            pass

        # Añadir líneas de tarifa por defecto si existen las tarifas 'Tarifa 1'..'Tarifa 7'
        pricelist_names = ['Tarifa %d' % i for i in range(1, 8)]
        Pricelist = self.env['product.pricelist']
        pricelists = Pricelist.search([('name', 'in', pricelist_names)])
        # Si faltan pricelists con los nombres esperados, crearlas automáticamente
        existing_names = set(pricelists.mapped('name'))
        missing = [n for n in pricelist_names if n not in existing_names]
        if missing:
            for name in missing:
                try:
                    # Crear una lista de precios básica. Si tu instalación necesita
                    # configuraciones específicas (moneda, compañía), podemos
                    # ajustarlo aquí más adelante.
                    Pricelist.create({'name': name})
                except Exception:
                    # no bloquear la creación del producto si falla la creación
                    # de alguna pricelist
                    continue
            # volver a buscar todas las pricelists (incluyendo las creadas)
            pricelists = Pricelist.search([('name', 'in', pricelist_names)])
        Item = self.env['product.pricelist.item']
        if pricelists:
            for tmpl in records:
                for pl in pricelists:
                    # evitar duplicados
                    exists = Item.search([
                        ('pricelist_id', '=', pl.id),
                        ('product_tmpl_id', '=', tmpl.id),
                    ], limit=1)
                    if not exists:
                        try:
                            # Crear la línea como ajuste porcentual (descuento 0%)
                            Item.create({
                                'pricelist_id': pl.id,
                                'product_tmpl_id': tmpl.id,
                                'name': pl.name + ' - ' + (tmpl.name or ''),
                                'applied_on': '1_product',
                                'compute_price': 'percentage',
                                'percent_price': 0.0,
                            })
                        except Exception:
                            # no bloquear la creación de productos si por algún motivo
                            # no se puede crear la línea de tarifa (diferencias entre versiones)
                            continue

        return records

