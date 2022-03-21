from odoo import fields, models, api


class SaleOder(models.Model):
    _inherit = "sale.order"

    @api.model
    def create(self, vals):
        res = super(SaleOder, self).create(vals)
        new_intercompany_sale_group_users = self.env.ref('sale_extend.new_intercompany_sale_group_users').users
        if 'auto_generated' in vals and vals['auto_generated'] and new_intercompany_sale_group_users:
            for user in new_intercompany_sale_group_users:
                if 'name' in vals:
                    activity_id = self.sudo().env['mail.activity'].create({
                        'summary': 'Alerte de la création d\'une vente Intercompany ' + vals['name'],
                        'activity_type_id': self.sudo().env.ref('mail.mail_activity_data_todo').id,
                        'res_model_id': self.sudo().env['ir.model'].search([('model', '=', 'sale.order')], limit=1).id,
                        'note': "",
                        'res_id': res.id,
                        'user_id': user.id
                    })
        return res


