# -*- encoding: utf-8 -*-

from odoo import models,fields, api
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tag_ids = fields.Many2many('product.tags', string='Étiquettes')
    is_carburant = fields.Boolean('Est un carburant', default=False)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    tag_ids = fields.Many2many('product.tags', string='Étiquettes')
    is_carburant = fields.Boolean('Est un carburant', default=False)


class ProductTags(models.Model):
    _name = 'product.tags'

    name = fields.Char('Nom')
    color = fields.Integer("Color Index", default=0)
