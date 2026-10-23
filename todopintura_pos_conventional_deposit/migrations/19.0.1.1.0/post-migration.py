# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Crédito y depósito pasan a ser independientes: el modo 'deposit' antiguo
    activa el nuevo flag de depósito y el modo 'credit' ya activaba el de crédito."""
    cr.execute(
        """
        UPDATE res_partner
           SET pos_deposit_sale_enabled = TRUE
         WHERE pos_conventional_sale_mode = 'deposit'
        """
    )
