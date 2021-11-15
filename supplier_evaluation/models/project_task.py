from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ProjectProject(models.Model):
    _inherit = 'project.project'

    type = fields.Selection([
        ('default', 'Default'),
        ('eval', 'Évaluation'),
        ('selection', 'Sélection'),
    ], string="Type de projet")


class ProjectTask(models.Model):
    _inherit = "project.task"

    project_type = fields.Selection(related='project_id.type', string='Type du projet')
    selected_supplier_id = fields.Many2one('res.partner', 'Fournisseur Séléctionné')
    evaluated_supplier_id = fields.Many2one('res.partner', 'Fournisseur Évalué')
    product_ids = fields.Many2many('product.product', 'product_product_project_task_rel', string='Articles')
    rating_line_ids = fields.One2many('supplier.rating.line', 'task_id', string="Lignes d'évaluation")
    note = fields.Float('Evaluation', compute='compute_mark')
    rating_date_start = fields.Date('De')
    rating_date_end = fields.Date('À')
    all_read_only = fields.Boolean('Remettre le tout RO', compute='compute_all_read_only')

    @api.depends('stage_id')
    def compute_all_read_only(self):
        for rec in self:
            rec.all_read_only = rec.stage_id in (self.env.ref('supplier_evaluation.sf_stage_done'), self.env.ref('supplier_evaluation.ef_stage_done'))

    @api.depends('rating_line_ids')
    def compute_mark(self):
        for rec in self:
            rec.note = 0
            # if self.rating_line_ids:
            total_notes = rec.rating_line_ids.mapped('mark')
            if len(total_notes):
                rec.note = sum(total_notes) / len(total_notes)

    def write(self, vals):
        if vals.get('stage_id'):
            stage_id = self.env['project.task.type'].browse(vals['stage_id'])
            project_ef_id = self.env.ref('supplier_evaluation.project_eval_fournisseur')
            project_sf_id = self.env.ref('supplier_evaluation.project_selection_fournisseur')
            done_sf_stage_id = self.env.ref('supplier_evaluation.sf_stage_done')
            done_ef_stage_id = self.env.ref('supplier_evaluation.ef_stage_done')
            if self.stage_id in (done_sf_stage_id, done_ef_stage_id) and stage_id:
                raise ValidationError('Vous ne pouvez pas changer l\'état d\'une évaluation qui est terminée')

            if self.project_id == project_sf_id and stage_id == done_sf_stage_id:
                supplier_rank = 0
                score = 'c'
                if self.note >= 80:
                    supplier_rank = 1
                    score = 'a'
                partner_id = self.env['res.partner'].create({
                    'name': self.name,
                    'type': 'contact',
                    'supplier_rank': supplier_rank,
                    'score': score,
                })
                self.selected_supplier_id = partner_id

            if self.project_id == project_ef_id and stage_id == done_ef_stage_id:
                if not self.evaluated_supplier_id:
                    raise ValidationError('Veuillez renseigner le fournisseur à évaluer')
                supplier_rank = 1
                score = 'c'
                # A > 80, 50 < B < 70 et C < 50
                if self.note >= 80:
                    score = 'a'
                elif 50 <= self.note < 80:
                    score = 'b'
                elif self.note < 50:
                    score = 'c'
                    supplier_rank = 0
                self.evaluated_supplier_id.write({
                    'supplier_rank': supplier_rank,
                    'score': score,
                })
        return super(ProjectTask, self).write(vals)


class LigneEvaluation(models.Model):
    _name = 'supplier.rating.line'

    @api.model
    def _get_rating_domain(self):
        if self._context.get('active_id', False):
            rec = self.env['project.project'].browse(self._context['active_id'])
            if rec:
                if rec.type == 'selection':
                    return [("type", "=", 'selection')]
                elif rec.type == 'eval':
                    return [("type", "=", 'eval')]

    rating_id = fields.Many2one('supplier.rating', string='Evaluation', domain=_get_rating_domain)
    rating_mark_id = fields.Many2one('rating.mark', string='Note')
    mark = fields.Float(related='rating_mark_id.mark', string='Note')
    task_id = fields.Many2one('project.task', 'Procédure')


class SupplierRating(models.Model):
    _name = 'supplier.rating'

    name = fields.Char('Nom')
    type = fields.Selection([('selection', 'Critère de Sélection'),
                             ('eval', 'Critère d\'évaluation')], default='selection', string='Type de critère')


class RatingMark(models.Model):
    _name = 'rating.mark'

    name = fields.Char('Nom')
    mark = fields.Float('Note', default=0)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    score = fields.Selection([
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C')
    ], string="Score fournisseur", default='c')
    periodicity = fields.Float('Périodicité en mois', default=3)
    selection_ids = fields.One2many('project.task', 'selected_supplier_id', string="Selection fournisseur", domain="[('project_type', '=', 'selection')]")
    selection_count = fields.Integer('Comptage de selection fournisseur', compute='get_count')
    evaluation_ids = fields.One2many('project.task', 'evaluated_supplier_id', string="Évaluation fournisseur", domain="[('project_type', '=', 'eval')]")
    evaluation_count = fields.Integer('Comptage de selection fournisseur', compute='get_count')

    def get_count(self):
        for rec in self:
            rec.selection_count = len(rec.selection_ids)
            rec.evaluation_count = len(rec.evaluation_ids)

    def write(self, vals):
        if 'score' in vals and self.child_ids:
            for child in self.child_ids:
                child.write({
                    'score': vals['score']
                })
        return super(ResPartner, self).write(vals)


