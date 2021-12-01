# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api
import calendar

from odoo.exceptions import ValidationError


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    mrp_ids = fields.One2many('mrp.production', 'maintenance_request_id', 'Réparations')
    count_reparations = fields.Integer('Comptage de réparations', compute='_get_mrp_count')

    def _get_mrp_count(self):
        for rec in self:
            rec.count_reparations = len(rec.mrp_ids)


class MRP(models.Model):
    _inherit = 'mrp.production'

    maintenance_request_id = fields.Many2one('maintenance.request', 'Maintenance')


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    child_ids = fields.One2many('maintenance.equipment', 'parent_id', 'Équipements')
    parent_id = fields.Many2one('maintenance.equipment', 'Équipement Parent')
    odometer_ids = fields.One2many('maintenance.equipment.odometer', 'equipment_id', string='Odomètre')
    count_odometer = fields.Integer('Comptage de kilomètrage', compute='_get_odometre_count')
    is_vehicle = fields.Boolean('Est un véhicule', default=False)
    odometer_unit = fields.Selection([
        ('kilometers', 'km'),
        ('hours', 'H')
        ], 'Unité', default='kilometers', help='Unit of the odometer ', required=True)
    odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Last Odometer',
        help='Odometer measure of the vehicle at the moment of this log')
    consomation_ids = fields.One2many('maintenance.consomation', 'equipment_id', string="Consommations", readonly=True)
    count_vehicle_cons = fields.Integer(compute='_cons_count', string=u'Nbre de consommations')
    license_plate = fields.Char(string='Immatriculation')
    maintenance_line_ids = fields.One2many('maintenance.line', 'equipment_id', 'Lignes de maintenance')
    maintenance_service_ids = fields.One2many('maintenance.service.line', 'equipment_id', 'Lignes des services')
    group_id = fields.Many2one('maintenance.equipment', 'Autocompletion des lignes de services')

    def _cons_count(self):
        for rec in self:
            rec.count_vehicle_cons = len(rec.consomation_ids)

    def _get_odometer(self):
        FleetVehicalOdometer = self.env['maintenance.equipment.odometer']
        for record in self:
            vehicle_odometer = FleetVehicalOdometer.search([('equipment_id', '=', record.id)], limit=1, order='value desc')
            if vehicle_odometer:
                record.odometer = vehicle_odometer.value
            else:
                record.odometer = 0

    @api.onchange('group_id')
    def _on_change_group_id(self):
        res = []
        for service_line in self.group_id.maintenance_service_ids:
            line_vals = {
                'type_id': service_line.type_id.id,
                'product_id': service_line.product_id.id,
                'name': service_line.name,
                'compteur': service_line.compteur,
                'frequency': service_line.frequency,
                'odometer_unit': service_line.odometer_unit,
                'equipment_id': self.id
            }
            res.append((0, 0, line_vals))
        self.maintenance_service_ids = res

    def _set_odometer(self):
        for record in self:
            if record.odometer:
                date = fields.Date.context_today(record)
                data = {'value': record.odometer, 'date': date, 'equipment_id': record.id}
                self.env['maintenance.equipment.odometer'].create(data)

    def _get_odometre_count(self):
        for rec in self:
            rec.count_odometer = len(rec.odometer_ids)

    def open_reinitialize_wizard(self):
        action = self.env.ref('maintenance_extend.action_reinitialize_service').read()[0]
        line_ids = []
        for service_line in self.maintenance_service_ids:
            line_vals = {
                'service_line_id': service_line.id,
                'product_id': service_line.product_id.id,
                'compteur': service_line.compteur,
                'frequency': service_line.frequency,
                'odometer': service_line.equipment_id.odometer
            }
            line_ids.append((0, 0, line_vals))
        context = {
            'default_equipment_id': self.id,
            'default_line_ids': line_ids,
            'default_multiple_equipments': False
        }
        action['context'] = context
        return action


class MaintenanceEquipmentType(models.Model):
    _name = 'maintenance.equipment.type'

    name = fields.Char('Nom')


class FleetEquipmentOdometer(models.Model):
    _name = 'maintenance.equipment.odometer'

    equipment_id = fields.Many2one('maintenance.equipment', 'Équipement')
    date = fields.Date(default=fields.Date.context_today)
    value = fields.Float('Valeur', group_operator="max")
    unit = fields.Selection(related='equipment_id.odometer_unit', string="Unité", readonly=True)
    driver_id = fields.Many2one(related="equipment_id.employee_id", string="Conducteur", readonly=False)


class MaintenanceConsomation(models.Model):
    _name = 'maintenance.consomation'

    equipment_id = fields.Many2one('maintenance.equipment', string='Véhicule', required=True)
    date = fields.Date('Date', default=fields.Date.today())
    immatriculation = fields.Char(related='equipment_id.license_plate', string='Immatriculation')
    motif = fields.Char(string='Motif')
    name = fields.Char(string='Numéro de reçu')
    conducteur = fields.Many2one(related='equipment_id.employee_id', string='Employé', readonly=False)
    qty_litres = fields.Float(string="Quantité en litres", required=True)
    amount = fields.Float(string="Prix en DH", compute='compute_amounts')
    total = fields.Float(string="Total en DH", compute='compute_amounts')
    kilometrage = fields.Float(string="Odomètre", required=True)

    @api.model
    def create(self, vals):
        self.env['maintenance.equipment.odometer'].create({
            'date': vals['date'],
            'equipment_id': vals['equipment_id'],
            'driver_id': vals['conducteur'],
            'value': vals['kilometrage'],
        })
        return super(MaintenanceConsomation, self).create(vals)

    @api.depends('qty_litres', 'date')
    def compute_amounts(self):
        for rec in self:
            rec.amount = 0.0
            rec.total = 0.0
            last_recharge_id = self.env['fleet.recharge'].search([('date', '<=', rec.date)], order='date DESC')
            if last_recharge_id:
                rec.amount = last_recharge_id[0].price_unit
                rec.total = rec.amount * rec.qty_litres
