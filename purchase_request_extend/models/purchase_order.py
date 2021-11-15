from odoo import fields, models, api
from odoo.exceptions import ValidationError


class PurchaseOder(models.Model):
    _inherit = "purchase.order"

    validation_daf = fields.Boolean('Validation de la DAF')
    validation_dg = fields.Boolean('Validation DG')
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', required=True, readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id.id)
    amount_in_mad = fields.Monetary('Montant en DH', currency_field='company_currency_id', compute='compute_amount_in_mad')

    def button_confirm(self):
        if self.requisition_id and self.amount_in_mad >= 5000 and not self.validation_dg:
            raise ValidationError('La validation du DG est requise')
        if self.requisition_id and not self.validation_daf and not self.validation_dg:
            raise ValidationError('La validation de la DAF est requise')
        return super(PurchaseOder, self).button_confirm()

    def compute_amount_in_mad(self):
        for rec in self:
            rec.amount_in_mad = rec.currency_id._convert(
                rec.amount_total, rec.company_currency_id, rec.company_id,
                rec.date_order or fields.Date.today())

