# -*- coding: utf-8 -*-

from odoo.tools import config

from . import models
from . import wizard
from .hooks import post_init_hook

if config["test_enable"]:
	from . import tests


