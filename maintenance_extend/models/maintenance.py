# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api
import calendar

from odoo.exceptions import ValidationError


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    mrp_ids = fields.One2many('mrp.production', 'maintenance_request_id', 'Réparations')
    count_reparations = fields.Integer('Comptage de réparations', compute='_get_mrp_count')
    audit_id = fields.Many2one('maintenance.audit', string="Audit de maintenance")
    date_start_unavailability = fields.Datetime('Date début d\'indisponibilité')
    equipment_unavailability_time = fields.Float('Compteur d\'indisponibilité')
    equipment_unavailability_time_in_days = fields.Float('Compteur d\'indisponibilité en jours')
    nature = fields.Char('Nature')

    def _get_mrp_count(self):
        for rec in self:
            rec.count_reparations = len(rec.mrp_ids)

    def write(self, vals):
        if 'stage_id' in vals:
            en_cours_stage_id = self.env.ref('maintenance.stage_1')
            if vals['stage_id'] == en_cours_stage_id.id:
                vals['date_start_unavailability'] = fields.Datetime.now()
            if self.stage_id == en_cours_stage_id and vals['stage_id'] != en_cours_stage_id.id:
                if self.date_start_unavailability:
                    self.equipment_unavailability_time += (fields.Datetime.now() - self.date_start_unavailability).seconds / 3600
                    self.equipment_unavailability_time_in_days += (fields.Datetime.now() - self.date_start_unavailability).days
        return super(MaintenanceRequest, self).write(vals)


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
    license_plate = fields.Char(string='Immatriculation')
    maintenance_line_ids = fields.One2many('maintenance.line', 'equipment_id', 'Lignes de maintenance')
    maintenance_service_ids = fields.One2many('maintenance.service.line', 'equipment_id', 'Lignes des services')
    group_id = fields.Many2one('maintenance.equipment', 'Autocompletion des lignes de services')
    equipment_unavailability_time = fields.Float('Compteur d\'indisponibilité', compute='compute_equipment_unavailability_time')
    equipment_unavailability_time_in_days = fields.Float('Compteur d\'indisponibilité en jours', compute='compute_equipment_unavailability_time')

    def compute_equipment_unavailability_time(self):
        for rec in self:
            rec.equipment_unavailability_time = sum(rec.maintenance_ids.mapped('equipment_unavailability_time'))
            rec.equipment_unavailability_time_in_days = sum(rec.maintenance_ids.mapped('equipment_unavailability_time_in_days'))

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

