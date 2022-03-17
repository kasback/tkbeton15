# -*- encoding: utf-8 -*-

from odoo import models,fields, api
from odoo.exceptions import ValidationError
from odoo.osv import expression


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    product_id = fields.Many2one(
        'product.product', 'Product',
        domain="""[
                ('type', 'in', ['product', 'consu']),
                ('can_be_manufactured', '=', True),
                '|',
                    ('company_id', '=', False),
                    ('company_id', '=', company_id)
            ]
            """,
        readonly=True, required=True, check_company=True,
        states={'draft': [('readonly', False)]})


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tag_ids = fields.Many2many('product.tags', string='Étiquettes')
    is_carburant = fields.Boolean('Est un carburant', default=False)
    can_be_manufactured = fields.Boolean('Peut être produit', compute='compute_can_be_manufactured', store=True)
    fuel_product_cost = fields.Float('Dernier prix du carburant', compute='compute_fuel_product_cost')

    def compute_fuel_product_cost(self):
        fuel_product_id = self.env['product.product'].search([('is_carburant', '=', True)], limit=1)
        for rec in self:
            rec.fuel_product_cost = 0.0
            latest_purchase_line = self.env['purchase.order.line'].search([('product_id', '=', fuel_product_id.id),
                                                                           ('order_id.state', 'in', ('purchase', 'done')),
                                                                           ],
                                                                          order='id DESC', limit=1)
            if latest_purchase_line:
                rec.fuel_product_cost = latest_purchase_line.price_unit

    @api.depends('route_ids')
    def compute_can_be_manufactured(self):
        for rec in self:
            manufacture_route_id = self.env.ref('mrp.route_warehouse0_manufacture')
            rec.can_be_manufactured = any(rec.route_ids.filtered(lambda r: r == manufacture_route_id))

    @api.model
    def create(self, vals):
        res = super(ProductTemplate, self).create(vals)
        new_product_group_users = self.env.ref('product_extend.groups_new_product_create_alert').users
        if new_product_group_users:
            for user in new_product_group_users:
                if 'name' in vals and vals['name'] == 'new':
                    activity_id = self.sudo().env['mail.activity'].create({
                        'summary': 'Alerte de la création d\'un nouveau produit ' + vals['name'],
                        'activity_type_id': self.sudo().env.ref('mail.mail_activity_data_todo').id,
                        'res_model_id': self.sudo().env['ir.model'].search([('model', '=', 'product.template')], limit=1).id,
                        'note': "",
                        'res_id': res.id,
                        'user_id': user.id
                    })
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    tag_ids = fields.Many2many('product.tags', string='Étiquettes')

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
