# -*- encoding: utf-8 -*-
import datetime

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    depart_usine = fields.Boolean('Départ Usine', default=False)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transporteur_id = fields.Many2one('res.partner', string='Transporteur')
    supplier_number = fields.Char('BL fournisseur')
    real_date = fields.Datetime('Date Effective', required=False)
    depart_usine = fields.Boolean('Départ Usine', default=False)
    city = fields.Many2one('product.product', 'Ville')

    def button_validate(self):
        if self.depart_usine:
            trsp_product_id = self.env.ref('stock_extend.product_product_service_transport')
            existing_po = self.env['purchase.order'].search([('depart_usine', '=', True),
                                                             ('partner_ref', '=', self.supplier_number)])
            if not existing_po:
                move_line = self.move_ids_without_package.filtered(lambda l: l.quantity_done > 0)
                if move_line:
                    po = self.env['purchase.order'].create({
                        'partner_id': self.transporteur_id.id,
                        'partner_ref': self.supplier_number,
                        'depart_usine': True,
                        'order_line': [
                            (0, 0, {
                                'name': self.city.name,
                                'product_id': self.city.id,
                                'product_qty': move_line[0].quantity_done,
                                # 'product_uom': trsp_product_id.uom_po_id.id,
                                'product_uom': 1,
                                'price_unit': self.city.standard_price,
                                'date_planned': datetime.datetime.today(),
                                'taxes_id': self.env['account.tax'].search([('code', '=', '141'), ('company_id', '=', self.env.company.id)]),
                            })
                        ]
                    })
                    po.button_confirm()
        for ml in self.move_ids_without_package:
            if ml.product_id.is_carburant and ml.purchase_line_id:
                self.env['fleet.recharge'].create({
                    'volume': ml.purchase_line_id.product_qty,
                    'price_unit': ml.purchase_line_id.price_unit,
                    'date': ml.picking_id.real_date,
                    'name': 'Alimentation citerne provenant de l\'achat %s' % ml.purchase_line_id.order_id.name
                })
        return super(StockPicking, self).button_validate()
