# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Se retira la relación usuario-empleados del TPV (el PIN vale en cualquier caja).

    Las vistas que la mostraban se borran antes de cargar el módulo: si no, siguen
    apuntando a campos que ya no existen y rompen la validación de otras vistas.
    """
    cr.execute(
        """
        DELETE FROM ir_ui_view WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'todopintura_extend_pos_conventional'
              AND model = 'ir.ui.view'
              AND name IN ('view_users_form_remove_pos_pin',
                           'view_employee_form_pos_users')
        )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'todopintura_extend_pos_conventional'
          AND model = 'ir.ui.view'
          AND name IN ('view_users_form_remove_pos_pin',
                       'view_employee_form_pos_users')
        """
    )
    cr.execute("DROP TABLE IF EXISTS res_users_pos_employee_rel")
