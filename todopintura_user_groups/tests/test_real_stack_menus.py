# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import tagged

from .common import PROFILES, OperationsCase

SHOP_PROFILES = (
    "group_04_ventas_de_almacen_central",
    "group_05_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie",
    "group_06_ventas_de_tiendas",
    "group_07_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie",
)


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestEveryMenuOpens(OperationsCase):
    """Every menu of every profile opens without access errors."""

    def test_every_profile_opens_all_its_menus(self):
        shop = self.warehouse("warehouse_huelva")
        config = self.config("pos_config_huelva")
        failures = {}
        for profile in PROFILES:
            restricted = profile in SHOP_PROFILES
            user = self.make_user(
                profile,
                warehouses=shop if restricted else None,
                configs=config if restricted else None,
            )
            errors = self.open_all_menus(user)
            if errors:
                failures[profile] = errors
        self.assertFalse(
            failures,
            "\n"
            + "\n".join(
                f"{profile}: {menu} -> {error}"
                for profile, errors in failures.items()
                for menu, error in errors.items()
            ),
        )

    def test_every_profile_opens_its_menus_without_restrictions(self):
        failures = {}
        for profile in PROFILES:
            user = self.make_user(profile, login=f"free_{profile}")
            errors = self.open_all_menus(user)
            if errors:
                failures[profile] = errors
        self.assertFalse(
            failures,
            "\n"
            + "\n".join(
                f"{profile}: {menu} -> {error}"
                for profile, errors in failures.items()
                for menu, error in errors.items()
            ),
        )
