from . import models
from odoo import SUPERUSER_ID, api

def post_init_hook(env):
    env['stock.warehouse.orderpoint']._create_cron_job()
