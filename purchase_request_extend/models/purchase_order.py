from itertools import groupby

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import AccessError, UserError, ValidationError


class PurchaseTags(models.Model):
    _name = "purchase.tag"

    name = fields.Char('Nom')


class PurchaseOder(models.Model):
    _inherit = "purchase.order"

    validation_daf = fields.Boolean('Validation de la DAF')
    validation_dg = fields.Boolean('Validation DG')
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', required=True, readonly=True,
                                          default=lambda self: self.env.user.company_id.currency_id.id)
    amount_in_mad = fields.Monetary('Montant en DH', currency_field='company_currency_id',
                                    compute='compute_amount_in_mad')
    tag_ids = fields.Many2many('purchase.tag', string='Étiquettes')

    purchase_request_id = fields.Many2one('purchase.request', compute='compute_purchase_request_id',
                                          string='Demande d\'achat', store=True)

    request_validation_date = fields.Date(related='purchase_request_id.validation_date', string='Date de validation DA',
                                          store=True)
    is_fuel_po = fields.Boolean('Est un BC de carburant', compute='compute_is_fuel_po')

    @api.depends('order_line')
    def compute_is_fuel_po(self):
        for rec in self:
            rec.is_fuel_po = len(rec.order_line) == 1 and \
                             rec.order_line[0].product_id.is_carburant

    @api.depends('order_line', 'order_line.purchase_request_lines')
    def compute_purchase_request_id(self):
        for rec in self:
            rec.purchase_request_id = rec.mapped("order_line.purchase_request_lines.request_id")

    def button_confirm(self):
        if self.requisition_id and self.amount_in_mad >= 5000 and not self.validation_dg:
            raise ValidationError('La validation du DG est requise')
        if not self.validation_daf \
                and not self.user_id.has_group('purchase_request_extend.groups_purchase_super_user') \
                and not self.is_fuel_po:
            raise ValidationError('La validation de la DAF est requise')
        return super(PurchaseOder, self).button_confirm()

    @api.model
    def create(self, vals):
        res = super(PurchaseOder, self).create(vals)
        if 'validation_daf' in vals and 'user_id' in vals and 'order_line' in vals:
            is_fuel_po = len(vals['order_line']) == 1 and \
                              self.env['product.product'].browse(vals['order_line'][0][2]['product_id']).is_carburant
            if not vals['validation_daf'] and \
                    not self.env['res.users'].browse(vals['user_id']).has_group(
                        'purchase_request_extend.groups_purchase_super_user') \
                    and not is_fuel_po:
                daf_group_users = self.env.ref(
                    'purchase_request_extend.group_daf').users
                if daf_group_users:
                    for user in daf_group_users: \
                            activity_id = self.sudo().env['mail.activity'].create({
                                'summary': 'Validation DAF requise pour le bon de commande achat ' + vals['name'],
                                'activity_type_id': self.sudo().env.ref('mail.mail_activity_data_todo').id,
                                'res_model_id': self.sudo().env['ir.model'].search([('model', '=', 'purchase.order')],
                                                                                   limit=1).id,
                                'note': "",
                                'res_id': res.id,
                                'user_id': user.id
                            })
        return res

    def compute_amount_in_mad(self):
        self = self.sudo()
        for rec in self:
            rec.amount_in_mad = rec.currency_id._convert(
                rec.amount_total, rec.company_currency_id, rec.company_id,
                rec.date_order or fields.Date.today())


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_qty', 'product_uom')
    def _onchange_quantity(self):
        if not self.product_id:
            return
        params = {'order_id': self.order_id}
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order.date(),
            uom_id=self.product_uom,
            params=params)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # If not seller, use the standard price. It needs a proper currency conversion.
        if not seller or (seller and 'Transport' in self.product_id.name):
            po_line_uom = self.product_uom or self.product_id.uom_po_id
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
                self.product_id.uom_id._compute_price(self.product_id.standard_price, po_line_uom),
                self.product_id.supplier_taxes_id,
                self.taxes_id,
                self.company_id,
            )
            if price_unit and self.order_id.currency_id and self.order_id.company_id.currency_id != self.order_id.currency_id:
                price_unit = self.order_id.company_id.currency_id._convert(
                    price_unit,
                    self.order_id.currency_id,
                    self.order_id.company_id,
                    self.date_order or fields.Date.today(),
                )

            self.price_unit = price_unit
            return

        price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                             self.product_id.supplier_taxes_id,
                                                                             self.taxes_id,
                                                                             self.company_id) if seller else 0.0
        if price_unit and seller and self.order_id.currency_id and seller.currency_id != self.order_id.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, self.order_id.currency_id, self.order_id.company_id, self.date_order or fields.Date.today())

        if seller and self.product_uom and seller.product_uom != self.product_uom:
            price_unit = seller.product_uom._compute_price(price_unit, self.product_uom)

        self.price_unit = price_unit
