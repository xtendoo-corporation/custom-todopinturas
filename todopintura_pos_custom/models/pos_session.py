from odoo import models, api
import logging
import time
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'

    def load_data(self, models_to_load, only_data=False):
        response = {}
        start = time.time()
        response['pos.session'] = self._load_pos_data(response)
        _logger.info("Tiempo carga pos.session: %.3f s", time.time() - start)
        self._load_pos_data_relations('pos.session', response)

        for model in self._load_pos_data_models(self.config_id.id):
            if models_to_load and model not in models_to_load:
                continue

            model_start = time.time()
            try:
                response[model] = self.env[model]._load_pos_data(response)
            except AccessError as e:
                response[model] = {
                    'data': [],
                    'fields': self.env[model]._load_pos_data_fields(response['pos.config']['data'][0]['id']),
                    'error': e.args[0]
                }
            elapsed = time.time() - model_start
            _logger.info("Tiempo carga modelo %s: %.3f s", model, elapsed)

            # Aquí registras los datos de product.product
            if model == 'product.product':
                fields = response[model].get('fields', [])
                _logger.info("Campos cargados de product.product: %s", fields)

            if not only_data:
                self._load_pos_data_relations(model, response)

        return response
