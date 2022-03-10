# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import models, api, fields

from odoo.exceptions import ValidationError


class EquipmentUnavailabilityReport(models.AbstractModel):
    _name = 'report.maintenance_extend.equipment_unavailability_report'

    def calculate_unavailability_time(self, equipment_id, date_start, date_end):
        if date_end == date_start:
            raise ValidationError('Les deux dates doivent être différentes')
        maintenance_ids = self.env['maintenance.request'].search([
            ('equipment_id', '=', equipment_id),
            ('date_end', '>=', date_start),
            ('date_start', '<=', date_end),
        ])
        print('maintenance_ids', maintenance_ids)
        unavailability_counter = 0
        date_start = datetime.strptime(date_start, "%Y-%m-%d")
        date_end = datetime.strptime(date_end, "%Y-%m-%d")
        """
            date_start = 01/02/2022
            date_end = 20/02/2022
            maintenance_ids = [
                ('29/12/2021', 31/12/2021),
                ('08/02/2022', 15/02/2022),
                ('18/02/2022', 22/02/2022),
                ('01/03/2022', 05/03/2022)
            ]
        """
        for maintenance in maintenance_ids:
            if maintenance.date_start >= date_start and maintenance.date_end <= date_end:
                print('maintenance.date_start >= date_start and maintenance.date_end <= date_end')
                print('maintenance.date_end', maintenance.date_end)
                print('diff', (maintenance.date_end - maintenance.date_start).days)
                unavailability_counter += (maintenance.date_end - maintenance.date_start).days
            elif maintenance.date_start >= date_start and maintenance.date_end >= date_end:
                print('maintenance.date_start >= date_start and maintenance.date_end >= date_end')
                print('maintenance.date_end', maintenance.date_end)
                print('diff', (date_end - maintenance.date_start).days)
                unavailability_counter += (date_end - maintenance.date_start).days

        unavailability_ratio = round(((unavailability_counter / (date_end - date_start).days) * 100), 2)
        return unavailability_counter, unavailability_ratio

    @api.model
    def _get_report_values(self, docids, data=None):
        if 'data' not in data:
            raise ValidationError('Aucune donnée fournie')
        data = data['data']
        date_start = data['date_start']
        date_end = data['date_end']
        res = {
            'doc_ids': docids,
            'date_start': date_start,
            'date_end': date_end,
            'lines': []
        }
        if 'equipment_id' in data and data['equipment_id']:
            unavailability_counter, unavailability_ratio = self.calculate_unavailability_time(data['equipment_id'],
                                                                                              date_start, date_end)
            res['lines'].append({
                'equipment_id': self.env['maintenance.equipment'].browse(data['equipment_id']),
                'unavailable_time': unavailability_counter,
                'unavailable_ratio': unavailability_ratio
            })
        if 'equipment_category_id' in data and data['equipment_category_id']:
            res['equipment_ids'] = self.env['maintenance.equipment']. \
                search([('category_id', '=', data['equipment_category_id'])])
            res['category_id'] = self.env['maintenance.equipment.category'].browse(data['equipment_category_id'])
            for equipment in res['equipment_ids']:
                unavailability_counter, unavailability_ratio = self.calculate_unavailability_time(equipment.id,
                                                                                                  date_start, date_end)
                res['lines'].append({
                    'equipment_id': equipment,
                    'unavailable_time': unavailability_counter,
                    'unavailable_ratio': unavailability_ratio
                })
        return res
