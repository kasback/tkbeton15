# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    footer_text = fields.Html('Text d\'incoterm')
    purchase_request_id = fields.Many2one('purchase.request', string="Demande d'achat")
    picking_ids = fields.Char(string='Bl liés')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    footer_text = fields.Html('Text d\'incoterm')

    def _prepare_invoice(self):
        """Prepare the dict of values to create the new invoice for a purchase order.
        """
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')
        journal = self.env['account.move'].with_context(default_move_type=move_type)._get_default_journal()
        if not journal:
            raise UserError(_('Please define an accounting purchase journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

        partner_invoice_id = self.partner_id.address_get(['invoice'])['invoice']
        invoice_vals = {
            'ref': self.partner_ref or '',
            'move_type': move_type,
            'narration': self.notes,
            'currency_id': self.currency_id.id,
            'invoice_user_id': self.user_id and self.user_id.id or self.env.user.id,
            'partner_id': partner_invoice_id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(partner_invoice_id)).id,
            'payment_reference': self.partner_ref or '',
            'partner_bank_id': self.partner_id.bank_ids[:1].id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
        }
        if self.picking_ids and self.picking_ids.mapped('supplier_number'):
            sns = self.picking_ids.filtered(lambda p: p.supplier_number).mapped('supplier_number')
            invoice_vals['picking_ids'] = ','.join(sns)
        return invoice_vals