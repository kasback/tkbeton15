# -*- encoding: utf-8 -*-

from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    report_code_ids = fields.One2many('report.code.line', 'company_id', string="Codes des rapports")


class ReportCodeLine(models.Model):
    _name = 'report.code.line'

    company_id = fields.Many2one('res.company', string='Société')
    report_id = fields.Many2one('ir.actions.report', string='Rapport')
    code = fields.Char('Code')
