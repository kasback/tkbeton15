# -*- encoding: utf-8 -*-
import datetime

from odoo import models, fields, api


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
    intercompany_transfer = fields.Boolean('Transfert Inter-Société', default=False)
    company_dest_id = fields.Many2one('res.company', 'Société destinataire')
    percent = fields.Float('Pourcentage')

    def prepare_sale_order_lines(self, move_ids):
        for move in move_ids:
            price_unit = move.purchase_line_id.price_unit
            return [(0, 0, {
                'name': move.product_id.name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.quantity_done,
                'product_uom': move.product_id.uom_id.id,
                'price_unit': price_unit + (price_unit * (self.percent / 100)),
            })]

    def prepare_purchase_order_lines(self, move_ids):
        for move in move_ids:
            price_unit = move.purchase_line_id.price_unit
            return [
                (0, 0, {
                    'name': move.product_id.name,
                    'product_id': move.product_id.id,
                    'product_qty': move.quantity_done,
                    'product_uom': move.product_id.uom_id.id,
                    'price_unit': price_unit + (price_unit * (self.percent / 100)),
                    'date_planned': self.real_date or fields.Date.today(),
                    'taxes_id': move.purchase_line_id.taxes_id
                })
            ]

    def button_validate(self):
        move_lines = self.move_ids_without_package.filtered(lambda l: l.quantity_done > 0)
        if self.intercompany_transfer:
            for move in move_lines:
                SaleOrder = self.env['sale.order']
                PurchaseOrder = self.env['purchase.order']
                existing_so = SaleOrder.search([('origin', '=', self.name + '/' + self.supplier_number)])
                existing_po = PurchaseOrder.search([('origin', '=', self.name + '/' + self.supplier_number),
                                                    ('company_id', '=', self.company_dest_id.id)])
                if not existing_po and not existing_so:
                    so_intercompany = SaleOrder.create({
                        'partner_id': self.company_dest_id.partner_id.id,
                        'date_order': self.real_date or fields.datetime.now(),
                        'origin': self.name + '/' + self.supplier_number,
                        'order_line': self.prepare_sale_order_lines(move)
                    })
                    so_intercompany.action_confirm()
                    for picking in so_intercompany.picking_ids:
                        picking.supplier_number = self.supplier_number
                        picking.action_set_quantities_to_reservation()
                        for ml in picking.move_ids_without_package:
                            ml.quantity_done = ml.product_uom_qty
                        picking.button_validate()
                    picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming'),
                                                                             ('sequence_code', '=', 'IN'),
                                                                             ('company_id', '=',
                                                                              self.company_dest_id.id),
                                                                             ('return_picking_type_id', '!=', False)
                                                                             ])
                    po_intercompany = PurchaseOrder.create({
                        'partner_id': self.company_id.partner_id.id,
                        'partner_ref': so_intercompany.name,
                        'date_approve': self.real_date,
                        'picking_type_id': picking_type_id.id,
                        'origin': self.name + '/' + self.supplier_number,
                        'order_line': self.prepare_purchase_order_lines(move),
                        'company_id': self.company_dest_id.id
                    })
                    so_intercompany.write({
                        'client_order_ref': po_intercompany.name
                    })
                    po_intercompany.button_confirm()
                    for picking in po_intercompany.picking_ids:
                        picking.supplier_number = self.supplier_number
                        picking.action_set_quantities_to_reservation()
                        picking.button_validate()
        if self.depart_usine:
            existing_po = self.env['purchase.order'].search([('depart_usine', '=', True),
                                                             ('partner_ref', '=', self.supplier_number)])
            if not existing_po:
                if move_lines:
                    po = self.env['purchase.order'].create({
                        'partner_id': self.transporteur_id.id,
                        'partner_ref': self.supplier_number,
                        'depart_usine': True,
                        'order_line': [
                            (0, 0, {
                                'name': self.city.name,
                                'product_id': self.city.id,
                                'product_qty': move_lines[0].quantity_done,
                                'product_uom': self.city.uom_id.id,
                                'price_unit': self.city.standard_price,
                                'date_planned': datetime.datetime.today(),
                                'taxes_id': self.env['account.tax'].search(
                                    [('code', '=', '141'), ('company_id', '=', self.env.company.id)]),
                            })
                        ]
                    })
                    po.button_confirm()
        return super(StockPicking, self).button_validate()
