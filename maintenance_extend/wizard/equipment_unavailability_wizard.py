# -*- coding: utf-8 -*-

from odoo import models, fields, api


class EquipmentUnavailabilityWizard(models.TransientModel):
    _name = 'maintenance.equipment.unavailability.wizard'

    equipment_id = fields.Many2one('maintenance.equipment', 'Équipement')
    equipment_category_id = fields.Many2one('maintenance.equipment.category', 'Catégorie d\'équipement')
    date_start = fields.Date('Date début', default=fields.Date.today(), required=True)
    date_end = fields.Date('Date fin', default=fields.Date.today(), required=True)
    by_category = fields.Boolean('Par catégorie', default=False)

    @api.onchange('by_category')
    def onchange_by_category(self):
        if not self.by_category:
            self.equipment_category_id = False

    def generate_data(self):
        self = self.sudo()
        datas = {
            'data': {
                'equipment_id': self.equipment_id.id,
                'equipment_category_id': self.equipment_category_id.id,
                'date_start': self.date_start,
                'date_end': self.date_end,
            }
        }
        return self.env.ref('maintenance_extend.equipment_unavailability_report_id').report_action([], data=datas)
