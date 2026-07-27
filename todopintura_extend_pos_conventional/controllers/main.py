from odoo import http


class TodopinturaExtendPosConventionalController(http.Controller):
    @http.route('/todopintura_extend_pos_conventional/user_permissions', type='json', auth='user', methods=['POST'])
    def user_permissions(self):
        user = http.request.env.user
        return {
            'pos_can_edit_price': bool(getattr(user, 'pos_can_edit_price', False)),
        }

