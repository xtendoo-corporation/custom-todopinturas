# -*- coding: utf-8 -*-
from odoo.addons.pos_conventional_core.tests.common import PosConventionalTestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosConfigCreateFix(PosConventionalTestCommon):

    def _create_system_admin(self, name, login):
        # A real-world "global admin" able to configure POS also holds the
        # Point of Sale/Administrator ACL group (group_pos_manager) -- the
        # ir.rule bug this reproduces is about the *record rule* layer, not
        # the ACL layer, so the test user needs both to match production.
        return self.env["res.users"].create({
            "name": name,
            "login": login,
            "company_id": self.env.company.id,
            "company_ids": [(6, 0, self.env.company.ids)],
            "group_ids": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("base.group_system").id,
                self.env.ref("point_of_sale.group_pos_manager").id,
            ])],
        })

    def _create_second_config(self, name="Config Secundaria"):
        pm = self._make_fresh_cash_pm(name=f"Efectivo {name}")
        return self.env["pos.config"].create({
            "name": name,
            "payment_method_ids": [(6, 0, [pm.id])],
        })

    def test_system_admin_without_restriction_can_create_config(self):
        """Un admin global sin restricción explícita puede crear una caja."""
        admin = self._create_system_admin(
            "System Admin Unrestricted", "system_admin_unrestricted_fix@example.com"
        )
        pm = self._make_fresh_cash_pm(name="Efectivo Admin Sin Restriccion")
        new_config = self.env["pos.config"].with_user(admin).create({
            "name": "Caja Creada Admin Sin Restriccion",
            "payment_method_ids": [(6, 0, [pm.id])],
        })
        self.assertTrue(new_config.exists())

    def test_system_admin_with_restriction_can_still_create_config(self):
        """Regresión: un admin global CON cajas restringidas debe poder seguir
        creando cajas nuevas, y además leerlas justo después de crearlas.

        Antes del fix, la regla 'POS: Admin Global ve todos los POS (o
        restringidos)' (en pos_conventional_config_user_filter) aplicaba su
        dominio 'id in allowed_pos_config_ids' también a la creación -- y una
        caja recién creada nunca puede tener un id que ya estuviera en esa
        lista de antemano, así que la creación se denegaba siempre que el
        admin tuviera cualquier caja asignada en "Cajas permitidas". El mismo
        problema reaparecía al releer el campo (p.ej. el propio cliente web
        hace esto justo tras guardar), porque la caja recién creada tampoco
        estaba aún en esa lista para lectura.
        """
        admin = self._create_system_admin(
            "System Admin Restricted", "system_admin_restricted_fix@example.com"
        )
        admin.allowed_pos_config_ids = [(4, self.pos_config.id)]

        pm = self._make_fresh_cash_pm(name="Efectivo Admin Restringido")
        new_config = self.env["pos.config"].with_user(admin).create({
            "name": "Caja Creada Admin Restringido",
            "payment_method_ids": [(6, 0, [pm.id])],
        })
        self.assertTrue(new_config.exists())
        # Debe poder releer el nombre justo después de crear, sin AccessError.
        self.assertEqual(new_config.name, "Caja Creada Admin Restringido")
        # Y debe haberse auto-concedido acceso a la caja que acaba de crear.
        self.assertIn(new_config, admin.allowed_pos_config_ids)

    def test_system_admin_create_permission_does_not_leak_read_access(self):
        """El permiso de creación sin restricción no amplía lo que el admin
        restringido puede LEER: sigue sin ver cajas fuera de su lista."""
        admin = self._create_system_admin(
            "System Admin Restricted Read", "system_admin_restricted_read_fix@example.com"
        )
        admin.allowed_pos_config_ids = [(4, self.pos_config.id)]
        other_config = self._create_second_config("Config Fuera De Alcance Admin Fix")

        visible_configs = self.env["pos.config"].with_user(admin).search(
            [("id", "in", [self.pos_config.id, other_config.id])]
        )

        self.assertEqual(visible_configs.ids, self.pos_config.ids)
