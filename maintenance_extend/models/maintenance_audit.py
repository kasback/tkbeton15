# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api
import calendar

from odoo.exceptions import ValidationError


class MaintenanceAudit(models.Model):
    _name = 'maintenance.audit'

    state = fields.Selection([('open', 'En cours'), ('closed', 'Fermé')], default='open')
    name = fields.Char('Numéro')
    date = fields.Date('Date d\'audit')
    audit_lines = fields.One2many('maintenance.audit.line', 'audit_id', string='Lignes d\'audit')
    responsible_id = fields.Many2one('res.partner', 'Responsable')
    maintenance_ids = fields.One2many('maintenance.request', 'audit_id', string='Maintenances')
    maintenance_count = fields.Integer(string='Comptage des maintenances', compute='compute_maintenance_count')

    def compute_maintenance_count(self):
        for rec in self:
            rec.maintenance_count = len(rec.maintenance_ids)

    def generate_audit_lines(self):
        maintenance_lines = self.env['maintenance.line'].search([('next_maintenance_date', '=', fields.Date.today()),
                                                                 ('audit_id', '=', False)])
        res = []
        if maintenance_lines:
            for line in maintenance_lines:
                res.append((0, 0, {
                    'maintenance_line_id': line.id,
                    'equipment_id': line.equipment_id.id,
                    'maintenance_equipment_id': line.equipment_id.id,
                    'type_ids': line.type_ids.id,
                    'nature': line.nature,
                    'next_maintenance_date': line.next_maintenance_date,
                }))
            audit_id = self.env['maintenance.audit'].create({
                'name': 'Audit ' + str(maintenance_lines[0].next_maintenance_date),
                'audit_lines': res
            })

    def open_audit_lines(self):
        action = self.env.ref('maintenance_extend.open_view_equipment_maintenance_line').read()[0]
        action['domain'] = [('audit_id', '=', self.id)]
        action['context'] = {'default_audit_id': self.id}
        return action

    def validate_audit(self):
        generated_maintenances = []
        for rec in self.audit_lines:
            if not rec.is_ok:
                Maintenance = self.env['maintenance.request']
                maintenance_id = Maintenance.create({
                    'name': 'Maintenance - %s - %s - %s' % (rec.equipment_id.name, self.name, rec.type_ids.name),
                    'request_date': fields.Date.today(),
                    'schedule_date': fields.Date.today(),
                    'equipment_id': rec.equipment_id.id,
                    'maintenance_type': 'corrective',
                    'owner_user_id': rec.equipment_id.owner_user_id.id,
                    'user_id': rec.equipment_id.technician_user_id.id,
                    'maintenance_team_id': self.env.ref('maintenance.equipment_team_maintenance').id,
                    'company_id': self.env.company.id,
                    'description': rec.observation
                })
                generated_maintenances.append((4, maintenance_id.id))
            rec.maintenance_line_id.write({
                'last_maintenance_date': fields.date.today()
            })
        self.write({
            'state': 'closed',
            'maintenance_ids': generated_maintenances
        })


class MaintenanceAuditLine(models.Model):
    _name = 'maintenance.audit.line'

    audit_id = fields.Many2one('maintenance.audit', 'Audit')
    state = fields.Selection(related='audit_id.state', string='État')
    maintenance_line_id = fields.Many2one('maintenance.line', string='Ligne de maintenance')
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipement')
    maintenance_equipment_id = fields.Many2one('maintenance.equipment', string='Equipement')
    type_ids = fields.Many2one('maintenance.equipment.type', string='Type de maintenance')
    nature = fields.Char(string='Nature')
    next_maintenance_date = fields.Date(string='Date de maintenance')
    is_ok = fields.Boolean(string='Ok', default=False)
    observation = fields.Char('Observation')
    frequency = fields.Selection([('day', 'Journalière'),
                                  ('week', 'Hebdomadaire'),
                                  ('month', 'Mensuelle'),
                                  ('tri', 'Trimestrielle'),
                                  ('year', 'Annuelle'),
                                  ], default='day',
                                 string="Fréquence")


