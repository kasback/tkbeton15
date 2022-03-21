# -*- coding: utf-8 -*-
import datetime

from odoo import models, fields, api
import calendar

from odoo.exceptions import ValidationError


class ReinitializeServiceWizard(models.TransientModel):
    _name = 'reinitialize.service.wizard'

    equipment_id = fields.Many2one('maintenance.equipment', 'Équipement')
    odometer = fields.Float(related='equipment_id.odometer', string='Kilomètrage de l\'equipement')
    line_ids = fields.One2many('reinitialize.service.wizard.line', 'service_wizard_id', string='Lignes à réinitialiser')
    multiple_equipments = fields.Boolean('Équipements Multiples', default=True)

    def reinitialize(self):
        self = self.sudo()
        for line in self.line_ids:
            if line.reinitialize:
                line_obj = self.env['maintenance.service.line'].browse(line.service_line_id)
                line_obj.write({
                    'compteur': line.odometer + line.frequency
                })


class ReinitializeServiceWizardLine(models.TransientModel):
    _name = 'reinitialize.service.wizard.line'

    service_wizard_id = fields.Many2one('reinitialize.service.wizard', 'Wizard de réinitialisation')
    service_line_id = fields.Integer('Id de la ligne')
    product_id = fields.Many2one('product.product', 'Article')
    compteur = fields.Integer('Compteur')
    frequency = fields.Float('Fréquence')
    odometer = fields.Float(string='Kilomètrage de l\'equipement')
    reinitialize = fields.Boolean('Réinitialiser?', default=False)

