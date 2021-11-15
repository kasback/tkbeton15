# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api
import calendar

from odoo.exceptions import ValidationError


class ServiceConfiguration(models.Model):
    _name = 'maintenance.service.configuration'

    min_km = fields.Integer('Nombre minimum de km pour alertes', default=5000)
    min_hr = fields.Integer('Nombre minimum d\'heures pour alertes', default=24)


class ServiceLine(models.Model):
    _name = 'maintenance.service.line'
    _rec_name = 'product_id'

    state = fields.Selection([
        ('far', 'Éspacée'),
        ('close', 'S\'approche'),
        ('past', 'Dépassée')
    ], 'État', default='far', compute='compute_service_state', store=True)
    equipment_id = fields.Many2one('maintenance.equipment', 'Équipement')
    product_id = fields.Many2one('product.product', 'Article')
    name = fields.Char('Description')
    frequency = fields.Float('Fréquence')
    odometer_unit = fields.Selection(related='equipment_id.odometer_unit', string='Unité')
    compteur = fields.Integer('Compteur')

    @api.depends('equipment_id.odometer_ids', 'compteur')
    def compute_service_state(self):
        for rec in self:
            equipment_odometer = rec.equipment_id.odometer
            rec.state = 'far'
            line_odometer = rec.compteur
            config = self.env.ref('maintenance_extend.maintenance_service_configuration')
            threshold = config.min_km if rec.equipment_id.odometer_unit == 'kilometers' \
                else config.min_hr
            if (line_odometer - equipment_odometer) > threshold:
                rec.state = 'far'
            elif 0 < (line_odometer - equipment_odometer) <= threshold:
                rec.state = 'close'
            elif (line_odometer - equipment_odometer) <= 0:
                rec.state = 'past'

    def open_reinitialize_wizard(self):
        action = self.env.ref('maintenance_extend.action_reinitialize_service').read()[0]
        line_ids = []
        for rec in self:
            line_vals = {
                'service_line_id': rec.id,
                'product_id': rec.product_id.id,
                'compteur': rec.compteur,
                'frequency': rec.frequency,
                'odometer': rec.equipment_id.odometer
            }
            line_ids.append((0, 0, line_vals))
        context = {
            'default_line_ids': line_ids,
            'default_multiple_equipments': True
        }
        action['context'] = context
        return action

    def service_create_maintenance_request(self):
        for rec in self:
            product_id = rec.product_id
            rec = rec.equipment_id
            if not rec.maintenance_team_id:
                raise ValidationError('Veuillez renseigner l\'équipe de maintenance au niveau de l\'équipement %s', rec.name)
            self.env['maintenance.request'].create({
                'name': 'Maintenance - %s - %s - %s' % (rec.name, str(fields.Date.today()), product_id.name),
                'request_date': fields.Date.today(),
                'schedule_date': fields.Date.today(),
                'equipment_id': rec.id,
                'maintenance_type': 'preventive',
                'owner_user_id': rec.owner_user_id.id,
                'user_id': rec.technician_user_id.id,
                'maintenance_team_id': rec.maintenance_team_id.id,
                'company_id': rec.company_id.id or self.env.company.id
            })
