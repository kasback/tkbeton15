# -*- encoding: utf-8 -*-

from odoo import models,fields, api
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tag_ids = fields.Many2many('product.tags', string='Étiquettes')
    is_carburant = fields.Boolean('Est un carburant', default=False)
    can_be_manufactured = fields.Boolean('Peut être produit', compute='compute_can_be_manufactured', store=True)

    @api.depends('route_ids')
    def compute_can_be_manufactured(self):
        for rec in self:
            manufacture_route_id = self.env.ref('mrp.route_warehouse0_manufacture')
            rec.can_be_manufactured = any(rec.route_ids.filtered(lambda r: r == manufacture_route_id))


class ProductProduct(models.Model):
    _inherit = 'product.product'

    tag_ids = fields.Many2many('product.tags', string='Étiquettes')
    is_carburant = fields.Boolean('Est un carburant', default=False)

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if args is None:
            args = []
        domain = ['|', '|', ('name', operator, name),
                  ('product_template_variant_value_ids', operator, name),
                  ('default_code', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


class ProductTags(models.Model):
    _name = 'product.tags'

    name = fields.Char('Nom')
    color = fields.Integer("Color Index", default=0)
