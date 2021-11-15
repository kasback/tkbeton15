# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api
import calendar

from odoo.exceptions import ValidationError


class MaintenanceAudit(models.Model):
    _name = 'maintenance.audit'

    name = fields.Char('Numéro')
    date = fields.Date('Date d\'audit')
    audit_lines = fields.One2many('maintenance.audit.line', 'audit_id', string='Lignes d\'audit')

    def generate_audit(self):
        maintenance_lines = self.env['maintenance.line'].search([('next_maintenance_date', '=', fields.Date.today())])
        print('maintenance_lines', maintenance_lines)
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
                'name': 'Audit ' + maintenance_lines[0].date,
                'audit_lines': res
            })

    def open_audit_lines(self):
        action = self.env.ref('maintenance_extend.open_view_equipment_maintenance_line').read()[0]
        action['domain'] = [('audit_id', '=', self.id)]
        action['context'] = {'default_audit_id': self.id}
        return action


class MaintenanceAuditLine(models.Model):
    _name = 'maintenance.audit.line'

    audit_id = fields.Many2one('maintenance.audit', 'Audit')
    maintenance_line_id = fields.Many2one('maintenance.line', string='Ligne de maintenance')
    equipment_id = fields.Many2one('maintenance.equipment', string='Equipement')
    maintenance_equipment_id = fields.Many2one('maintenance.equipment', string='Equipement')
    type_ids = fields.Many2one('maintenance.equipment.type', string='Type de maintenance')
    nature = fields.Char(string='Type de maintenance')
    next_maintenance_date = fields.Date(string='Date de maintenance')
    is_ok = fields.Boolean(string='Ok', default=False)
