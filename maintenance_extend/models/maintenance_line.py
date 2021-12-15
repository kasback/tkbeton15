# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api
import calendar

from odoo.exceptions import ValidationError


class MaintenanceLine(models.Model):
    _name = 'maintenance.line'

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
    day_of_week = fields.Selection([
        ('0', 'Lundi'),
        ('1', 'Mardi'),
        ('2', 'Mercredi'),
        ('3', 'Jeudi'),
        ('4', 'Vendredi'),
        ('5', 'Samedi'),
        ('6', 'Dimanche'),
    ], default='0', string='Jour')
    last_maintenance_date = fields.Date('Date de la dernière maintenance', default=fields.Date.today(), required=True)
    next_maintenance_date = fields.Date('Date de la prochaine maintenance', readonly=False,
                                        compute='_compute_next_maintenance', store=True)
    state = fields.Selection([
        ('green', 'Éspacé'),
        ('yellow', 'S\'approche'),
        ('red', 'Aujourd\'hui'),
        ('grey', 'Dépassé'),
    ], string='État', compute="compute_state")

    @api.depends('last_maintenance_date', 'next_maintenance_date')
    def compute_state(self):
        for rec in self:
            diff = rec.next_maintenance_date - fields.date.today()
            print('diff', diff.days)
            diff_days = diff.days
            if diff_days < 0:
                rec.state = 'grey'
            if diff_days == 0:
                rec.state = 'red'
            elif 0 < diff_days <= 1:
                rec.state = 'yellow'
            elif diff_days > 1:
                rec.state = 'green'

    @api.depends('last_maintenance_date', 'day_of_week', 'frequency')
    def _compute_next_maintenance(self):
        """
            daily: next_maintenance_date = last_maintenance_date + 24 hours
            weekly: next_maintenance_date = last_maintenance_date + 7 days
            monthly: next_maintenance_date = Last 'day_of_week' of last_maintenance_date.month
        :return:
        """
        cal = calendar.Calendar(0)
        for rec in self:
            if rec.frequency == 'month':
                year = rec.last_maintenance_date.year
                month = rec.last_maintenance_date.month
                month_calendar = cal.monthdatescalendar(year, month)
                lastweek = month_calendar[-1]
                last_day_of_month = lastweek[int(rec.day_of_week)]
                rec.next_maintenance_date = datetime.date(year, month, last_day_of_month.day)
            elif rec.frequency == 'week':
                rec.next_maintenance_date = rec.last_maintenance_date + datetime.timedelta(weeks=1)
            elif rec.frequency == 'tri':
                rec.next_maintenance_date = rec.last_maintenance_date + datetime.timedelta(days=90)
            elif rec.frequency == 'year':
                rec.next_maintenance_date = rec.last_maintenance_date + datetime.timedelta(days=365)
            else:
                rec.next_maintenance_date = rec.last_maintenance_date + datetime.timedelta(days=1)

    def create_maintenance_from_equipment(self):
        for rec in self:
            equipment_id = rec.equipment_id
            if not equipment_id.maintenance_team_id:
                raise ValidationError('Veuillez renseigner l\'équipe de maintenance')
            if equipment_id.maintenance_count > 0 and equipment_id.maintenance_ids.filtered(
                    lambda m: m.request_date == rec.last_maintenance_date):
                raise ValidationError('Une demande de maintenance pour ce matériel est déja créee')
            self.env['maintenance.request'].create({
                'name': 'Maintenance - %s - %s - %s' % (
                    equipment_id.name, rec.next_maintenance_date, rec.type_ids.name),
                'request_date': rec.next_maintenance_date,
                'schedule_date': rec.next_maintenance_date,
                'equipment_id': rec.equipment_id.id,
                'maintenance_type': 'preventive',
                'owner_user_id': equipment_id.owner_user_id.id,
                'user_id': equipment_id.technician_user_id.id,
                'maintenance_team_id': equipment_id.maintenance_team_id.id,
                'company_id': equipment_id.company_id.id or self.env.company.id
            })
            rec.write({'last_maintenance_date': fields.Date.today()})

    def open_create_audit_wizard(self):
        wizard_maintenace_lines = []
        for rec in self:
            wizard_maintenace_lines.append((0, 0, {
                'maintenance_line_id': rec.id,
                'equipment_id': rec.equipment_id.id,
                'type_ids': rec.type_ids.id,
                'nature': rec.nature,
                'frequency': rec.frequency,
                'next_maintenance_date': rec.next_maintenance_date
            }))
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'create.audit.wizard',
            'view_mode': 'form',
            'context': {'default_maintenance_line_ids': wizard_maintenace_lines},
            'target': 'new'
        }
        return action
