# -*- encoding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_transporteur = fields.Boolean('Est un transporteur', default=False)
