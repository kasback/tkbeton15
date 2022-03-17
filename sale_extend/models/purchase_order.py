from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class SaleOder(models.Model):
    _inherit = "sale.order"

    @api.model
    def create(self, vals):
        res = super(SaleOder, self).create(vals)
        new_intercompany_sale_group_users = self.env.ref('sale_extend.groups_new_product_create_alert').users
        if 'auto_generated' in vals and vals['auto_generated'] and new_product_group_users:
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


