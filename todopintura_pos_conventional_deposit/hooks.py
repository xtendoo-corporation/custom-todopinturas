# -*- coding: utf-8 -*-


def post_init_hook(env):
    env.cr.execute(
        """
        UPDATE res_partner
           SET pos_conventional_sale_mode = CASE
               WHEN COALESCE(pos_credit_sale_enabled, FALSE) THEN 'credit'
               ELSE 'none'
           END
         WHERE pos_conventional_sale_mode IS NULL
            OR pos_conventional_sale_mode = ''
        """
    )

