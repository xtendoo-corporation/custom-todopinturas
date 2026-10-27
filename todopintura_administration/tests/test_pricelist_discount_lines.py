from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPricelistDiscountLines(TransactionCase):
    """El precio de tarifa se muestra como PVP + descuento sin duplicarlo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.discount_group = cls.env.ref("sale.group_discount_per_so_line")
        cls.product = cls.env["product.product"].create({
            "name": "Pintura plástica",
            "list_price": 100.0,
            "taxes_id": [(5,)],
        })
        cls.cheap_product = cls.env["product.product"].create({
            "name": "Rodillo",
            "list_price": 10.0,
            "taxes_id": [(5,)],
        })
        cls.partner = cls.env["res.partner"].create({"name": "Pintor"})
        cls.pricelist_percentage = cls._create_pricelist(
            "Tarifa 30%", compute_price="percentage", percent_price=30.0
        )
        cls.pricelist_fixed = cls._create_pricelist(
            "Tarifa fija", compute_price="fixed", fixed_price=80.0
        )
        cls.pricelist_formula = cls._create_pricelist(
            "Tarifa fórmula", compute_price="formula", price_discount=25.0
        )
        cls.pricelist_surcharge = cls._create_pricelist(
            "Tarifa recargo", compute_price="fixed", fixed_price=120.0
        )

    @classmethod
    def _create_pricelist(cls, name, **rule_vals):
        return cls.env["product.pricelist"].create({
            "name": name,
            "item_ids": [(0, 0, dict(
                applied_on="0_product_variant",
                product_id=cls.product.id,
                **rule_vals,
            ))],
        })

    def _set_discount_feature(self, enabled):
        user_group = self.env.ref("base.group_user")
        if enabled:
            user_group.implied_ids |= self.discount_group
            self.env.user.group_ids |= self.discount_group
        else:
            user_group.implied_ids -= self.discount_group
            self.env.user.group_ids -= self.discount_group
        self.env.invalidate_all()
        self.env.registry.clear_cache("groups")

    def _create_sale_line(self, pricelist, **line_vals):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "pricelist_id": pricelist.id,
            "order_line": [(0, 0, dict(
                product_id=self.product.id, product_uom_qty=1.0, **line_vals
            ))],
        })
        return order.order_line

    def _assert_sale_line(self, line, price_unit, discount, subtotal):
        self.assertAlmostEqual(line.price_unit, price_unit, places=2)
        self.assertAlmostEqual(line.discount, discount, places=2)
        self.assertAlmostEqual(line.price_subtotal, subtotal, places=2)

    # --- Pedido de venta -------------------------------------------------

    def test_sale_line_shows_public_price_and_discount(self):
        for enabled in (False, True):
            self._set_discount_feature(enabled)
            for pricelist, discount in (
                (self.pricelist_percentage, 30.0),
                (self.pricelist_fixed, 20.0),
                (self.pricelist_formula, 25.0),
            ):
                with self.subTest(pricelist=pricelist.name, discount_feature=enabled):
                    line = self._create_sale_line(pricelist)
                    self._assert_sale_line(line, 100.0, discount, 100.0 - discount)

    def test_sale_line_quantity_change_does_not_double_discount(self):
        for enabled in (False, True):
            self._set_discount_feature(enabled)
            for pricelist, discount in (
                (self.pricelist_percentage, 30.0),
                (self.pricelist_fixed, 20.0),
            ):
                with self.subTest(pricelist=pricelist.name, discount_feature=enabled):
                    line = self._create_sale_line(pricelist)
                    line.product_uom_qty = 2.0
                    self._assert_sale_line(
                        line, 100.0, discount, 2 * (100.0 - discount)
                    )

    def test_sale_line_with_pricelist_price_as_unit_price(self):
        """Una línea creada con el precio neto (p. ej. desde el TPV) se
        normaliza al recalcular, sin acumular el descuento."""
        self._set_discount_feature(False)
        line = self._create_sale_line(
            self.pricelist_fixed, price_unit=80.0, discount=20.0
        )
        self._assert_sale_line(line, 80.0, 20.0, 64.0)
        line.product_uom_qty = 3.0
        self._assert_sale_line(line, 100.0, 20.0, 240.0)

    def test_sale_line_update_prices_after_pricelist_change(self):
        self._set_discount_feature(False)
        line = self._create_sale_line(self.pricelist_percentage)
        order = line.order_id
        order.pricelist_id = self.pricelist_fixed
        order.action_update_prices()
        self._assert_sale_line(line, 100.0, 20.0, 80.0)

    def test_sale_line_surcharge_keeps_pricelist_price(self):
        for enabled in (False, True):
            self._set_discount_feature(enabled)
            with self.subTest(discount_feature=enabled):
                line = self._create_sale_line(self.pricelist_surcharge)
                self._assert_sale_line(line, 120.0, 0.0, 120.0)

    def test_sale_line_stale_discount_is_reset_without_feature(self):
        self._set_discount_feature(False)
        line = self._create_sale_line(self.pricelist_percentage)
        line.product_id = self.cheap_product
        self._assert_sale_line(line, 10.0, 0.0, 10.0)

    def test_sale_note_line_is_ignored(self):
        self._set_discount_feature(False)
        line = self._create_sale_line(self.pricelist_percentage)
        note = self.env["sale.order.line"].create({
            "order_id": line.order_id.id,
            "display_type": "line_note",
            "name": "Nota",
        })
        self.assertFalse(note.discount)
        self.assertEqual(note._tp_get_pricelist_discount(), 0.0)

    # --- Línea de TPV (onchange del formulario backend) -------------------

    def _new_pos_line(self, pricelist, product, **line_vals):
        order = self.env["pos.order"].new({
            "partner_id": self.partner.id,
            "pricelist_id": pricelist.id,
        })
        return self.env["pos.order.line"].new(dict(
            order_id=order, product_id=product.id, qty=1.0, **line_vals
        ))

    def _assert_pos_line(self, line, price_unit, discount, subtotal):
        self.assertAlmostEqual(line.price_unit, price_unit, places=2)
        self.assertAlmostEqual(line.discount, discount, places=2)
        self.assertAlmostEqual(line.price_subtotal, subtotal, places=2)
        self.assertAlmostEqual(line.price_subtotal_incl, subtotal, places=2)

    def test_pos_line_onchange_shows_public_price_and_discount(self):
        line = self._new_pos_line(self.pricelist_percentage, self.product)
        line._onchange_product_id()
        self._assert_pos_line(line, 100.0, 30.0, 70.0)

    def test_pos_line_reselect_product_does_not_double_discount(self):
        """Caso real: la línea ya tenía PVP + descuento y se vuelve a
        seleccionar el producto. Antes el subtotal quedaba en 100*0.7*0.7."""
        line = self._new_pos_line(
            self.pricelist_percentage, self.product,
            price_unit=100.0, discount=30.0,
            price_subtotal=70.0, price_subtotal_incl=70.0,
        )
        line._onchange_product_id()
        self._assert_pos_line(line, 100.0, 30.0, 70.0)

    def test_pos_line_quantity_change(self):
        line = self._new_pos_line(
            self.pricelist_fixed, self.product, price_unit=100.0, discount=20.0
        )
        line.qty = 3.0
        line._onchange_product_id()
        self._assert_pos_line(line, 100.0, 20.0, 240.0)

    def test_pos_line_product_without_discount_resets_old_discount(self):
        line = self._new_pos_line(
            self.pricelist_percentage, self.cheap_product,
            price_unit=100.0, discount=30.0,
        )
        line._onchange_product_id()
        self._assert_pos_line(line, 10.0, 0.0, 10.0)

    def test_pos_line_surcharge_keeps_pricelist_price(self):
        line = self._new_pos_line(self.pricelist_surcharge, self.product)
        line._onchange_product_id()
        self._assert_pos_line(line, 120.0, 0.0, 120.0)
