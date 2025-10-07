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

        # En Odoo 19, usar _load_pos_data_search_read que retorna una lista directamente
        response['pos.session'] = self._load_pos_data_search_read(response, self.config_id)
        _logger.info("Tiempo carga pos.session: %.3f s", time.time() - start)

        # Pasar el objeto config completo, no solo el ID
        for model in self._load_pos_data_models(self.config_id):
            if models_to_load and model not in models_to_load:
                continue

            model_start = time.time()
            try:
                # _load_pos_data_search_read retorna una lista directamente
                response[model] = self.env[model]._load_pos_data_search_read(response, self.config_id)
            except AccessError as e:
                response[model] = []
                _logger.info("Could not load model %s due to AccessError: %s", model, e)

            elapsed = time.time() - model_start
            _logger.info("Tiempo carga modelo %s: %.3f s", model, elapsed)

        return response
