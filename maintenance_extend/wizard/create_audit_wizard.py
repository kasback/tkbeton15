# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CreateAuditWizard(models.TransientModel):
    _name = 'create.audit.wizard'

    responsible_id = fields.Many2one('res.partner', 'Responsable', required=True)
    date = fields.Date('Date d\'audit', default=fields.Date.today(), required=True)
    maintenance_line_ids = fields.One2many('create.audit.wizard.line', 'create_audit_wizard_id', 'Lignes de maintenance')

    def action_create_audit(self):
        audit_lines = []
        for rec in self.maintenance_line_ids:
            print('wizard maintenance_line_id', rec.maintenance_line_id.id)
            audit_lines.append((0, 0, {
                'maintenance_line_id': rec.maintenance_line_id.id,
                'equipment_id': rec.equipment_id.id,
                'maintenance_equipment_id': rec.equipment_id.id,
                'type_ids': rec.type_ids.id,
                'nature': rec.nature,
                'frequency': rec.frequency,
                'next_maintenance_date': rec.next_maintenance_date
            }))
        audit_id = self.env['maintenance.audit'].create({
            'name': 'Audit ' + str(self.date),
            'date': self.date,
            'responsible_id': self.responsible_id.id,
            'audit_lines': audit_lines
        })
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.audit',
            'view_mode': 'form',
            'res_id': audit_id.id,
            'target': 'current',
        }
        return action


class CreateAuditWizardLine(models.TransientModel):
    _name = 'create.audit.wizard.line'

    create_audit_wizard_id = fields.Many2one('create.audit.wizard', 'Wizard de création d\'audit')
    maintenance_line_id = fields.Many2one('maintenance.line', 'Ligne de maintenance')
    equipment_id = fields.Many2one('maintenance.equipment', 'Équipement')
    product_id = fields.Many2one('product.product', 'Fourniture')
    type_ids = fields.Many2one('maintenance.equipment.type', string='Types de maintenance')
    nature = fields.Char('Nature')
    frequency = fields.Selection([('day', 'Journalière'),
                                  ('week', 'Hebdomadaire'),
                                  ('month', 'Mensuelle'),
                                  ('tri', 'Trimestrielle'),
                                  ('year', 'Annuelle'),
                                  ], default='day',
                                 string="Fréquence")
    next_maintenance_date = fields.Date('Date de la prochaine maintenance')
