# -*- encoding: utf-8 -*-
import datetime

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    depart_usine = fields.Boolean('Départ Usine', default=False)
    date_planned = fields.Datetime(
        string='Receipt Date', index=True, copy=False, compute='_compute_date_planned', store=True, readonly=True,
        help="Delivery date promised by vendor. This date is used to determine expected arrival of products.")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transporteur_id = fields.Many2one('res.partner', string='Transporteur', copy=False)
    supplier_number = fields.Char('BL fournisseur', copy=False)
    real_date = fields.Datetime('Date Effective', required=False)
    depart_usine = fields.Boolean('Départ Usine', default=False)
    city = fields.Many2one('product.product', 'Ville')
    intercompany_transfer = fields.Boolean('Transfert Inter-Société', default=False)
    company_dest_id = fields.Many2one('res.company', 'Société destinataire')
    percent = fields.Float('Pourcentage')
    purchase_request_id = fields.Many2one('purchase.request', related='purchase_id.purchase_request_id',
                                          string='Demande d\'Achat')

    def prepare_sale_order_lines(self, move_ids):
        lines = []
        for move in move_ids:
            price_unit = move.purchase_line_id.price_unit
            print('move.quantity_done', move.quantity_done)
            lines.append((0, 0, {
                'name': move.product_id.name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.quantity_done,
                'product_uom': move.product_id.uom_id.id,
                'price_unit': price_unit + (price_unit * (self.percent / 100)),
            }))
        return lines

    def prepare_purchase_order_lines(self, move_ids):
        lines = []
        for move in move_ids:
            price_unit = move.purchase_line_id.price_unit
            lines.append((0, 0, {
                    'name': move.product_id.name,
                    'product_id': move.product_id.id,
                    'product_qty': move.quantity_done,
                    'product_uom': move.product_id.uom_id.id,
                    'price_unit': price_unit + (price_unit * (self.percent / 100)),
                    'date_planned': self.real_date or fields.Date.today(),
                    'taxes_id': move.purchase_line_id.taxes_id
                }))
        return lines

    def button_validate(self):
        self = self.sudo()
        for rec in self:
            move_lines = rec.move_ids_without_package.filtered(lambda l: l.quantity_done > 0)
            if rec.purchase_id:
                rec.purchase_id.write({
                    'date_planned': fields.Date.today()
                })
            if rec.intercompany_transfer:
                for move in move_lines:
                    SaleOrder = self.env['sale.order']
                    PurchaseOrder = self.env['purchase.order']
                    existing_so = SaleOrder.search([('origin', '=', rec.name + '/' + rec.supplier_number)])
                    existing_po = PurchaseOrder.search([('origin', '=', rec.name + '/' + rec.supplier_number),
                                                        ('company_id', '=', rec.company_dest_id.id)])
                    if not existing_po and not existing_so:
                        so_intercompany = SaleOrder.create({
                            'partner_id': rec.company_dest_id.partner_id.id,
                            'date_order': rec.real_date or fields.datetime.now(),
                            'origin': rec.name + '/' + rec.supplier_number,
                            'order_line': rec.prepare_sale_order_lines(move)
                        })
                        so_intercompany.action_confirm()
                        for picking in so_intercompany.picking_ids:
                            picking.supplier_number = rec.supplier_number
                            picking.action_assign()
                            picking.action_set_quantities_to_reservation()
                            # print('picking.move_line_ids_without_package', picking.move_line_ids_without_package)
                            for ml in picking.move_ids_without_package:
                                ml.quantity_done = move.quantity_done
                            for ml in picking.move_line_ids_without_package:
                                ml.qty_done = move.quantity_done
                            picking.button_validate()
                        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'incoming'),
                                                                                 ('sequence_code', '=', 'IN'),
                                                                                 ('company_id', '=',
                                                                                  rec.company_dest_id.id),
                                                                                 ('return_picking_type_id', '!=', False)
                                                                                 ])
                        po_intercompany = PurchaseOrder.create({
                            'partner_id': rec.company_id.partner_id.id,
                            'partner_ref': so_intercompany.name,
                            'date_approve': rec.real_date,
                            'picking_type_id': picking_type_id.id,
                            'origin': rec.name + '/' + rec.supplier_number,
                            'order_line': rec.prepare_purchase_order_lines(move),
                            'company_id': rec.company_dest_id.id,
                            'validation_daf': True
                        })
                        so_intercompany.write({
                            'client_order_ref': po_intercompany.name
                        })
                        po_intercompany.button_confirm()
                        for picking in po_intercompany.picking_ids:
                            picking.supplier_number = rec.supplier_number
                            picking.action_set_quantities_to_reservation()
                            picking.button_validate()
            if rec.depart_usine and rec.transporteur_id:
                existing_po = self.env['purchase.order'].search([('depart_usine', '=', True),
                                                                 ('partner_ref', '=', rec.supplier_number)])
                if not existing_po:
                    if move_lines:
                        po = self.env['purchase.order'].create({
                            'partner_id': rec.transporteur_id.id,
                            'partner_ref': rec.supplier_number,
                            'validation_daf': True,
                            'depart_usine': True,
                            'order_line': [
                                (0, 0, {
                                    'name': rec.city.name,
                                    'product_id': rec.city.id,
                                    'product_qty': move_lines[0].quantity_done,
                                    'product_uom': rec.city.uom_id.id,
                                    'price_unit': rec.city.standard_price,
                                    'date_planned': datetime.datetime.today(),
                                    'taxes_id': rec.env['account.tax'].search(
                                        [('code', '=', '141'), ('company_id', '=', self.env.company.id)]),
                                })
                            ]
                        })
                        po.button_confirm()
                        for picking in po.picking_ids:
                            picking.supplier_number = rec.supplier_number
                            picking.action_set_quantities_to_reservation()
                            picking.button_validate()
        return super(StockPicking, self).button_validate()
