# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Helpers to exercise the profiles the way the web client does.

The scenarios built on them need the customer's full stack (conventional POS,
credit policy...). They skip themselves on a database without it, so they run
on a copy of the customer's database.
"""

import datetime
from unittest import SkipTest

from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

MODULE = "todopintura_user_groups"
STACK_MODULES = ("todopintura_extend_pos_conventional",)
PROFILES = (
    "group_01_gestion_de_pedidos",
    "group_02_pedidos_de_y_para_tiendas",
    "group_03_gestion_de_entradas_de_proveedor",
    "group_04_ventas_de_almacen_central",
    "group_05_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie",
    "group_06_ventas_de_tiendas",
    "group_07_gestion_de_pedidos_traspasos_y_ventas_de_otras_tie",
    "group_08_menu_de_comerciales",
    "group_09_informes_estadisticos_menu_of002",
    "group_10_direccion",
)
X2MANY = ("one2many", "many2many")


class OperationsCase(TransactionCase):
    """Base class: profile users plus a web-client-like menu opener."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        installed = cls.env["ir.module.module"].search(
            [("name", "in", STACK_MODULES), ("state", "=", "installed")]
        )
        if len(installed) != len(STACK_MODULES):
            raise SkipTest("Needs the customer's full POS stack")

    # ---- users ----------------------------------------------------------
    @classmethod
    def make_user(cls, profile, login=None, warehouses=None, configs=None):
        group = cls.env.ref(f"{MODULE}.{profile}")
        values = {
            "name": login or f"e2e_{profile[:8]}",
            "login": login or f"e2e_{profile}",
            "group_ids": [Command.set(group.ids)],
            "allowed_warehouse_ids": [
                Command.set((warehouses or cls.env["stock.warehouse"]).ids)
            ],
        }
        if (
            configs is not None
            and "allowed_pos_config_ids" in cls.env["res.users"]._fields
        ):
            values["allowed_pos_config_ids"] = [Command.set(configs.ids)]
        return cls.env["res.users"].with_context(no_reset_password=True).create(values)

    @classmethod
    def warehouse(cls, xmlid):
        return cls.env.ref(f"{MODULE}.{xmlid}")

    @classmethod
    def config(cls, xmlid):
        return cls.env.ref(f"{MODULE}.{xmlid}")

    # ---- web client emulation ----------------------------------------------
    def visible_leaf_menus(self, user):
        menu = self.env["ir.ui.menu"]
        visible = menu.browse(menu.with_user(user)._visible_menu_ids())
        return visible.filtered("action").sorted("complete_name")

    def _spec(self, model, arch_node):
        """Fields spec like the web client sends to web_read/web_search_read."""
        spec = {}
        for field_node in arch_node.iterchildren():
            if field_node.tag == "field":
                name = field_node.get("name")
                spec[name] = self._field_spec(model, name, field_node)
            elif field_node.tag in (
                "group",
                "page",
                "notebook",
                "sheet",
                "div",
                "header",
                "button_box",
            ) or len(field_node):
                spec.update(self._spec(model, field_node))
        return spec

    def _field_spec(self, model, name, field_node):
        field = self.env[model]._fields.get(name)
        if field is None or not field.relational:
            return {}
        sub = {}
        for sub_view in field_node.iterchildren():
            if sub_view.tag in ("list", "form", "kanban"):
                sub.update(self._spec(field.comodel_name, sub_view))
        if field.type in X2MANY and sub:
            return {"fields": sub}
        return {"fields": {"display_name": {}}}

    def _action_domain(self, action, user):
        if not action.domain:
            return []
        return safe_eval(
            action.domain,
            {
                "uid": user.id,
                "user": user,
                "time": safe_time,
                "datetime": safe_datetime,
                "context_today": datetime.date.today,
            },
        )

    def open_menu(self, user, menu, limit=5):
        """Open the menu action as the client does; return the opened model."""
        action = menu.action
        if action._name == "ir.actions.server":
            action = action.with_user(user).with_context(active_model=action.model_name)
            result = action.run() or {}
            if result.get("type") != "ir.actions.act_window":
                return action.model_name
            action = self.env["ir.actions.act_window"].new(result)
        model = action.res_model
        Model = self.env[model].with_user(user)
        modes = [mode.strip() for mode in (action.view_mode or "list,form").split(",")]
        views = Model.get_views([(False, mode) for mode in modes])
        domain = self._action_domain(action, user)
        records = Model
        for mode in modes:
            info = views["views"].get(mode)
            if not info:
                continue
            arch = etree.fromstring(info["arch"])
            if mode in ("list", "kanban", "form") and mode != "form":
                spec = self._spec(model, arch)
                found = Model.web_search_read(domain, spec, limit=limit)
                if mode == "list" and found["records"]:
                    records = Model.browse(r["id"] for r in found["records"])
            elif mode == "form" and records:
                Model.browse(records[0].id).web_read(self._spec(model, arch))
            elif mode in ("pivot", "graph"):
                Model.formatted_read_group(domain, [], ["__count"])
        return model

    def open_all_menus(self, user):
        """Open every leaf menu; return {menu name: error} for the failures."""
        failures = {}
        for menu in self.visible_leaf_menus(user):
            try:
                with self.env.cr.savepoint():
                    self.open_menu(user, menu)
            except (AccessError, UserError, KeyError, ValueError, TypeError) as error:
                failures[menu.complete_name] = f"{type(error).__name__}: {error}"[:300]
        return failures
