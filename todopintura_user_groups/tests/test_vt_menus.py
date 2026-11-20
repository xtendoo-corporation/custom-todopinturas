# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import tagged

from .common import TodopinturaTestCase

MODULE = "todopintura_user_groups"


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestVentasPosMenus(TodopinturaTestCase):
    def test_removed_menus_of_ventas_de_pos(self):
        """«Ventas de POS» ya no tiene el listado de traspasos pendientes ni la
        grabación de ventas con recogida en otra tienda."""
        for name in (
            "menu_vt_transfers_pending",
            "menu_vt_transfers_pickup",
            "menu_vt_transfers_pickup_quotes",
        ):
            self.assertFalse(
                self.env.ref(f"{MODULE}.{name}", raise_if_not_found=False), name
            )

    def test_pedidos_de_y_para_tiendas_keeps_its_menus(self):
        for name in ("menu_pt_transfers_pending", "menu_pt_transfers_pickup"):
            self.assertTrue(self.env.ref(f"{MODULE}.{name}"), name)

    def test_rest_of_the_transfers_submenu_is_kept(self):
        for name in (
            "menu_vt_transfers_send",
            "menu_vt_transfers_receive",
            "menu_vt_transfers_print",
            "menu_vt_transfers_credit",
        ):
            self.assertTrue(self.env.ref(f"{MODULE}.{name}"), name)

    def test_account_sales_of_another_store_is_called_deposit(self):
        """«Grabación de ACUENTAS de otra tienda» pasa a «Grabación depósito de otra tienda»."""
        for name in ("menu_vt_transfers_credit", "menu_pt_transfers_credit"):
            menu = self.env.ref(f"{MODULE}.{name}")
            self.assertEqual(menu.name, "Grabación depósito de otra tienda", name)
        group = self.env.ref(f"{MODULE}.perm_va01pas2")
        self.assertEqual(group.name, "Grabación depósito de otra tienda")
        self.assertNotIn("ACUENTAS", menu.complete_name)
