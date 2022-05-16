# -*- encoding: utf-8 -*-

from odoo import models, fields, api


class DossierImport(models.Model):
    _name = 'dossier.import'

    state = fields.Selection([('new', 'Nouveau'), ('open', 'En cours'), ('closed', 'Soldé')],
                             string="État du dossier", default='new')
    name = fields.Char('No Engagement d\'importation')
    date = fields.Date('Date', default=fields.Date.today())
    date_from = fields.Date('Du')
    supplier_id = fields.Many2one('res.partner', string='Fournisseur')
    shipper_id = fields.Many2one('res.partner', string='Shipper')
    bl_lta_cmr = fields.Char('BL/LTA/CMR')
    date_start = fields.Date('Date départ')
    date_enter = fields.Date('Date d\'entrée')
    date_reception = fields.Date('Date réception à l\'Usine')
    date_projected_enter = fields.Date('Date d\'arrivée prévue')
    port_of_loading = fields.Char('Port of loading')
    port_of_discharge = fields.Char('Port of discharge')
    line_ids = fields.One2many('dossier.import.line', 'dossier_import_id', string="Lignes dossier import")
    amount_total = fields.Float(string="Montant Global")
    amount_residual = fields.Float(string="Solde à payer")
    advance = fields.Float(string="Avance %")
    payment_date = fields.Date(string="Date prévu")
    date_projected_payment = fields.Date(string="Date prévu")
    observations = fields.Text(string="Observations")

    def action_en_cours(self):
        self.write({'state': 'open'})

    def action_close(self):
        self.write({'state': 'closed'})


class DossierImportLine(models.Model):
    _name = 'dossier.import.line'

    dossier_import_id = fields.Many2one('dossier.import')
    name = fields.Char('No Pro-forma date')
    invoice_number_date = fields.Char('No invoice date')
    transportation_type = fields.Char('Moyen de transport')
    nature = fields.Char('Nature de M/se')
    net_weight = fields.Char('Poids Net')
    gross_weight = fields.Char('Poids Brut')
    domicilliation_bank = fields.Char('Domicilliation Bank')
    customs_charge = fields.Char('Imputation Douanière')
