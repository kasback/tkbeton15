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
    date_start = fields.Datetime('Date début de maintenance')
    date_end = fields.Datetime('Date fin de maintenance')
    equipment_unavailability_time = fields.Float('Compteur d\'indisponibilité', compute='compute_equipment_unavailability_time')
    nature = fields.Char('Nature')

    @api.depends('date_start', 'date_end')
    def compute_equipment_unavailability_time(self):
        for rec in self:
            rec.equipment_unavailability_time = 0
            if rec.date_end and rec.date_start:
                rec.equipment_unavailability_time = (rec.date_end - rec.date_start).days

    def _get_mrp_count(self):
        for rec in self:
            rec.count_reparations = len(rec.mrp_ids)


class MRP(models.Model):
    _inherit = 'mrp.production'

    def default_analytic_account_id(self):
        if 'default_maintenance_request_id' in self._context and self._context['default_maintenance_request_id']:
            maintenance_id = self.env['maintenance.request'].browse(self._context['default_maintenance_request_id'])
            domain = [('company_id', '=', self.env.company.id)]
            if maintenance_id.maintenance_type == 'preventive':
                return self.env['account.analytic.account'].\
                    search(domain + [('name', 'ilike', 'Maintenance Préventive')])
            elif maintenance_id.maintenance_type == 'corrective':
                return self.env['account.analytic.account'].\
                    search(domain + [('name', 'ilike', 'Maintenance Corrective')])

    maintenance_request_id = fields.Many2one('maintenance.request', 'Maintenance')
    equipment_id = fields.Many2one('maintenance.equipment', related='maintenance_request_id.equipment_id',
                                   string="Équipement", store=True)
    equipment_category_id = fields.Many2one('maintenance.equipment.category', related='equipment_id.category_id',
                                            string="Catégorie", store=True)

    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Analytic Account", default=lambda self: self.default_analytic_account_id()
    )
    description = fields.Html(related='maintenance_request_id.description', string='Cause')


class MRPWO(models.Model):
    _inherit = 'mrp.workorder'

    operator_id = fields.Many2one('hr.employee', 'Opérateur')


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    child_ids = fields.One2many('maintenance.equipment', 'parent_id', 'Équipements')
    parent_id = fields.Many2one('maintenance.equipment', 'Équipement Parent')
    odometer_ids = fields.One2many('maintenance.equipment.odometer', 'equipment_id', string='Odomètre')
    count_odometer = fields.Integer('Comptage de kilomètrage', compute='_get_odometre_count')
    is_vehicle = fields.Boolean('Est un véhicule', default=True)
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
    kanban_state = fields.Selection([('blocked', 'Indisponible'), ('done', 'Disponible')],
                                    string='Disponibilité', required=True, store=True, default='done', compute='compute_kanban_state')

    @api.depends('maintenance_ids.stage_id')
    def compute_kanban_state(self):
        for rec in self:
            ongoing_maintenance = rec.maintenance_ids.filtered(lambda m: m.stage_id == self.env.ref('maintenance.stage_1'))
            rec.kanban_state = 'blocked' if ongoing_maintenance else 'done'

    def compute_equipment_unavailability_time(self):
        for rec in self:
            rec.equipment_unavailability_time = sum(rec.maintenance_ids.mapped('equipment_unavailability_time'))

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
        res_service = []
        res_maintenance = []
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
            res_service.append((0, 0, line_vals))
        for maintenance_line in self.group_id.maintenance_line_ids:
            line_vals = {
                'type_ids': maintenance_line.type_ids.id,
                'nature': maintenance_line.nature,
                'frequency': maintenance_line.frequency,
                'day_of_week': maintenance_line.day_of_week,
                'last_maintenance_date': maintenance_line.last_maintenance_date,
                'equipment_id': self.id
            }
            res_maintenance.append((0, 0, line_vals))
        self.maintenance_service_ids = res_service
        self.maintenance_line_ids = res_maintenance

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

