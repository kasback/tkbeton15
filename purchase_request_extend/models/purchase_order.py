from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


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
        if not self.validation_daf and not self.user_id.has_group('purchase_request_extend.groups_purchase_super_user'):
            raise ValidationError('La validation de la DAF est requise')
        return super(PurchaseOder, self).button_confirm()

    @api.model
    def create(self, vals):
        res = super(PurchaseOder, self).create(vals)
        if 'validation_daf' in vals and 'user_id' in vals:
            if not vals['validation_daf'] and \
                    (
                            not vals['user_id'].has_group('purchase_request_extend.groups_purchase_super_user')
                            or not vals['is_fuel_po']
                    ):
                daf_group_users = self.env.ref(
                    'purchase_request_extend.group_daf').users
                if daf_group_users:
                    for user in daf_group_users:
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

    def _log_decrease_ordered_quantity(self, purchase_order_lines_quantities):
        return
        # def _keys_in_sorted(move):
        #     """ sort by picking and the responsible for the product the
        #     move.
        #     """
        #     return (move.picking_id.id, move.product_id.responsible_id.id)
        #
        # def _keys_in_groupby(move):
        #     """ group by picking and the responsible for the product the
        #     move.
        #     """
        #     return (move.picking_id, move.product_id.responsible_id)
        #
        # def _render_note_exception_quantity_po(order_exceptions):
        #     order_line_ids = self.env['purchase.order.line'].browse([order_line.id for order in order_exceptions.values() for order_line in order[0]])
        #     purchase_order_ids = order_line_ids.mapped('order_id')
        #     move_ids = self.env['stock.move'].concat(*rendering_context.keys())
        #     impacted_pickings = move_ids.mapped('picking_id')._get_impacted_pickings(move_ids) - move_ids.mapped('picking_id')
        #     values = {
        #         'purchase_order_ids': purchase_order_ids,
        #         'order_exceptions': order_exceptions.values(),
        #         'impacted_pickings': impacted_pickings,
        #     }
        #     return self.env.ref('purchase_stock.exception_on_po')._render(values=values)
        #
        # documents = self.env['stock.picking']._log_activity_get_documents(purchase_order_lines_quantities, 'move_ids', 'DOWN', _keys_in_sorted, _keys_in_groupby)
        # filtered_documents = {}
        # for (parent, responsible), rendering_context in documents.items():
        #     if parent._name == 'stock.picking':
        #         if parent.state == 'cancel':
        #             continue
        #     filtered_documents[(parent, responsible)] = rendering_context
        # self.env['stock.picking']._log_activity(_render_note_exception_quantity_po, filtered_documents)


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
