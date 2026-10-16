# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, models, tools

MODULE = "todopintura_user_groups"

# Modelos "de infraestructura" que cualquier flujo de Odoo necesita escribir
# (mensajes, adjuntos, preferencias...). No forman parte de los permisos de negocio.
INFRA_PREFIXES = ("mail.", "ir.", "bus.", "base.", "res.users", "res.device", "web.", "digest.")


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    @api.model
    def _todopintura_group_ids(self):
        """Ids de los grupos de este modulo."""
        data = self.env["ir.model.data"].sudo().search(
            [("module", "=", MODULE), ("model", "=", "res.groups")]
        )
        return set(data.mapped("res_id"))

    @api.model
    @tools.ormcache(cache="stable")
    def _todopintura_controlled_read(self):
        """Modelos cuya lectura solo se concede a quien tenga un permiso Todopintura."""
        self.flush_model()
        self.env.cr.execute(
            """
            SELECT DISTINCT m.model
              FROM ir_model_access a JOIN ir_model m ON m.id = a.model_id
             WHERE a.perm_read AND a.active AND a.group_id IN %s
            """,
            [tuple(self._todopintura_group_ids()) or (None,)],
        )
        return frozenset(r[0] for r in self.env.cr.fetchall())

    @tools.ormcache("self.env.uid", "mode", cache="stable")
    def _get_allowed_models(self, mode="read"):
        allowed = super()._get_allowed_models(mode)
        user = self.env.user
        if user.has_group("base.group_system") or not user.has_group(
            f"{MODULE}.group_todopintura_restricted"
        ):
            return allowed
        own = tuple(set(user._get_group_ids()) & self._todopintura_group_ids()) or (None,)
        self.env.cr.execute(
            f"""
            SELECT DISTINCT m.model
              FROM ir_model_access a JOIN ir_model m ON m.id = a.model_id
             WHERE a.perm_{mode} AND a.active AND a.group_id IN %s
            """,  # noqa: S608 (mode validado por el metodo base)
            [own],
        )
        granted = {r[0] for r in self.env.cr.fetchall()}
        if mode == "read":
            return frozenset(
                m for m in allowed if m in granted or m not in self._todopintura_controlled_read()
            )
        return frozenset(
            m
            for m in allowed
            if m in granted
            or m.startswith(INFRA_PREFIXES)
            or (m in self.env and self.env[m]._transient)
        )
