# -*- encoding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = 'account.move'

    footer_text = fields.Html('Text d\'incoterm')
    purchase_request_id = fields.Many2one('purchase.request', string="Demande d'achat")


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    footer_text = fields.Html('Text d\'incoterm')
