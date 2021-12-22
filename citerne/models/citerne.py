# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    consomation_ids = fields.One2many('equipment.consomation', 'equipment_id', string="Consommations", readonly=True)
    count_vehicle_cons = fields.Integer(compute='_cons_count', string=u'Nbre de consommations')

    def _cons_count(self):
        for rec in self:
            rec.count_vehicle_cons = len(rec.consomation_ids)


class MaintenanceConsomation(models.Model):
    _name = 'equipment.consomation'

    state = fields.Selection([('draft', "Brouillon"),
                              ('done', "Términé")
                              ],
                             string="État", default="draft", track_visibility='onchange')
    equipment_id = fields.Many2one('maintenance.equipment', string='Équipement')
    date = fields.Date('Date', default=fields.Date.today())
    name = fields.Char(string='Numéro de reçu', required=False)
    qty_litres = fields.Float(string="Quantité en litres")
    kilometrage = fields.Float(string="Kilométrage", required=True)
    picking_id = fields.Many2one('stock.picking', string="Mouvement de la citerne", copy=False)
    conducteur = fields.Many2one(related='equipment_id.employee_id', string='Employé', readonly=False)

    @api.constrains('kilometrage')
    def check_kilometrage(self):
        for rec in self:
            if rec.kilometrage <= 0.0:
                raise ValidationError('Veuillez rentrer une valeur de kilomètrage valide')

    def action_to_done(self):
        self.process_lines()
        self.write({
            'state': 'done'
        })

    def action_to_draft(self):
        self.write({
            'state': 'draft'
        })

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('equipment.consomation')
        self.env['maintenance.equipment.odometer'].create({
            'date': vals['date'],
            'equipment_id': vals['equipment_id'],
            'driver_id': vals['conducteur'],
            'value': vals['kilometrage'],
        })
        return super(MaintenanceConsomation, self).create(vals)

    def process_lines(self):
        fuel_product_id = self.env['product.product'].search([('is_carburant', '=', True)], limit=1)
        if not fuel_product_id:
            raise ValidationError('Veuillez avoir au moin un produit de type carburant')
        citerne_location_id = self.env.ref('citerne.stock_location_citerne')
        dest_location_id = self.env.ref('stock.stock_location_customers')
        citerne_operation_type_id = self.env.ref('citerne.stock_picking_type_citerne')
        if self.qty_litres <= 0:
            raise ValidationError('Veuillez rentrer une quantité en litres valide')
        if self.qty_litres > 0:
            qty_available = self.env['stock.quant'].search([('location_id', '=', citerne_location_id.id),
                                                                ('product_id', '=', fuel_product_id.id)]).quantity
            product_available = qty_available >= self.qty_litres
            if not product_available:
                raise ValidationError(
                    'La quantité du produit %s n\'est pas disponible dans l\'emplacement %s, La quantité disponible est : %d'
                    % (fuel_product_id.name, citerne_location_id.name, qty_available))
        picking_id = self.env['stock.picking'].create({
            'location_id': citerne_location_id.id,
            'location_dest_id': dest_location_id.id,
            'name': 'Citerne / ' + 'BON DE SORTIE' + '/' + self.name,
            'picking_type_id': citerne_operation_type_id.id,
            'move_line_ids_without_package': [(0, 0, {
                'product_id': fuel_product_id.id,
                'qty_done': self.qty_litres,
                'product_uom_id': fuel_product_id.uom_id.id,
                'location_id': citerne_location_id.id,
                'location_dest_id': dest_location_id.id,
            })],
            'immediate_transfer': True,
            'fleet_consomation_id': self.id
        })
        picking_id.button_validate()
        self.write({
            'picking_id': picking_id.id
        })


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    fleet_consomation_id = fields.Many2one('equipment.consomation', string='Consommation de carburant')

