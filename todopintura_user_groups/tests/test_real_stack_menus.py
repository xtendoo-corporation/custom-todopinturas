# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests import tagged

from .common import PROFILES, OperationsCase


@tagged("post_install", "-at_install", "todopintura_user_groups")
class TestEveryMenuOpens(OperationsCase):
    """Every menu of every profile opens without access errors."""

    def test_every_profile_opens_all_its_menus(self):
        shop = self.warehouse("warehouse_huelva")
        config = self.config("pos_config_huelva")
        failures = {}
        for profile in PROFILES:
            user = self.make_user(profile, warehouses=shop, configs=config)
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
