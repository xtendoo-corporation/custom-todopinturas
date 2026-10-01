# -*- coding: utf-8 -*-
from odoo import models, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model_create_multi
    def create(self, vals_list):
        """Let a group_system admin create (and self-initialize) a new POS
        config even when their own "Cajas permitidas" record rule
        (pos_conventional_config_user_filter.pos_config_rule_system_all)
        would otherwise scope them to a fixed set of existing ids.

        point_of_sale's own create() writes back to the record it just
        inserted (_create_sequences() sets order_seq_id/invoice_seq_id via a
        plain write()), and that internal write is also governed by that
        ir.rule -- a brand new record can never already be a member of a
        pre-existing "allowed_pos_config_ids" list, so that bootstrap write
        would otherwise always be denied for an admin restricted to specific
        stores, even though security/pos_config_record_rules.xml in this
        module deliberately sets perm_create=0 on that rule so creation
        isn't blocked by it either. Same sudo-bypass pattern already used by
        pos.config._search()'s 'allow_all_pos' context flag.
        """
        if self.env.user.has_group('base.group_system'):
            records = super(PosConfig, self.sudo()).create(vals_list)
            user = self.env.user
            if user.allowed_pos_config_ids:
                # Otherwise the admin couldn't even READ back what they just
                # created (same "id in allowed_pos_config_ids" domain, same
                # chicken-and-egg problem as create/write above) -- and a
                # user restricted to specific POS who deliberately creates a
                # new one clearly means to have access to it.
                user.sudo().allowed_pos_config_ids = [(4, r.id) for r in records]
            return records.with_env(self.env)
        return super().create(vals_list)
