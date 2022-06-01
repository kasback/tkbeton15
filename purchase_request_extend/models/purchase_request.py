from odoo import fields, models, api

_STATES = [
    ("draft", "Draft"),
    ('superieur_approval', 'Validation supérieur'),
    ("to_approve", "Validation Responsable Achat"),
    ('daf_approval', 'Validation DAF'),
    ('dg_approval', 'Validation DG'),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("done", "Done"),
]


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    supplier_id = fields.Many2one('res.partner', string="Fournisseur", readonly=False)
    default_code = fields.Char(related='product_id.default_code', string="Reférence interne")
    purchase_type = fields.Selection(related='request_id.purchase_type')

    @api.onchange('purchase_type')
    def onchange_purchase_type(self):
        tag_ids = self.env['product.tags'].search([('name', 'ilike', self.purchase_type)])
        domain = [('tag_ids', 'in', tag_ids.ids)]
        product_ids = self.env['product.template'].search(domain).mapped('product_variant_id')
        products_domain = [('id', 'in', product_ids.ids)]
        return {'domain': {'product_id': products_domain}}


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    def _get_dg(self):
        group_dg = self.env.ref('purchase_request_extend.group_dg')
        if group_dg.users:
            return group_dg.users[0]

    def _get_daf(self):
        group_daf = self.env.ref('purchase_request_extend.group_daf')
        if group_daf.users:
            return group_daf.users[0]

    @api.model
    def get_purchase_product_type_selection(self):
        if self.env.user.has_group('purchase_request.group_purchase_request_manager'):
            return [
                ('existing', 'Alimentation de stock'),
                ('achat_mp', 'Achat MP'),
                ('new', 'Nouveau Produit'),
                ('price_change', 'Changement de prix'),
                ('negociation', 'Renégociation annuelle des prix'),
            ]
        else:
            return [
                ('existing', 'Alimentation de stock'),
                ('new', 'Nouveau Produit')
            ]

    state = fields.Selection(
        selection=_STATES,
        string="Status",
        index=True,
        tracking=True,
        required=True,
        copy=False,
        default="draft",
    )
    responsible_id = fields.Many2one('res.users', related='requested_by.employee_id.parent_id.user_id',
                                     string='Supérieur hiérarchique', store=True)
    dg_id = fields.Many2one('res.users', string='DG', domain=lambda self: self._get_dg_task_domain(), default=_get_dg)
    daf_id = fields.Many2one('res.users', string='DAF', domain=lambda self: self._get_daf_task_domain(),
                             default=_get_daf)
    can_approve = fields.Boolean('Peut approuver', compute='_can_approve')
    can_approve_resp = fields.Boolean('Responsable Peut approuver', compute='_can_approve_resp')
    can_approve_daf = fields.Boolean('DAF Peut approuver', compute='_can_approve_daf')
    can_approve_dg = fields.Boolean('DG Peut approuver', compute='_can_approve_dg')
    purchase_type = fields.Selection([('local', 'Local'), ('import', 'Import')], default='local',
                                     string='Type d\'Achat')
    purchase_reason = fields.Selection([('stock', 'Stock'), ('urgent', 'Urgent')], default='stock',
                                       string='Raison d\'Achat')
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Responsable d'Achat",
        compute='_compute_resp_achat',
        readonly=True,
        store=True,
        tracking=True,
        index=True,
    )

    purchase_product_type = fields.Selection(selection=get_purchase_product_type_selection,
                                             default='existing',
                                             string='Type de produit')
    show_tender_btn = fields.Boolean('Montrer le button CA', compute='_compute_show_tender_btn')
    tender_id = fields.Many2one('purchase.requisition', string='Convention d\'achat')
    active = fields.Boolean(
        help="The active field allows you to hide the date range without "
             "removing it.",
        default=True,
    )
    purchase_order_ids = fields.Many2many('purchase.order', compute='compute_purchase_order_ids',
                                          string='Bons de commandes', store=True)
    validation_date = fields.Date('Date de validation', readonly=True)
    equipment_id = fields.Many2one('maintenance.equipment', string='Équipement')

    @api.depends('line_ids', 'line_ids.purchase_lines')
    def compute_purchase_order_ids(self):
        for rec in self:
            rec.purchase_order_ids = [(4, o.id) for o in rec.mapped("line_ids.purchase_lines.order_id")]

    @api.model
    def create(self, vals):
        res = super(PurchaseRequest, self).create(vals)
        new_product_group_users = self.env.ref('purchase_request_extend.groups_new_product_purchase_alert').users
        if new_product_group_users:
            for user in new_product_group_users:
                if 'purchase_product_type' in vals and vals['purchase_product_type'] == 'new':
                    activity_id = self.sudo().env['mail.activity'].create({
                        'summary': 'Alerte demande d\'achat d\'un nouveau produit ' + vals['name'],
                        'activity_type_id': self.sudo().env.ref('mail.mail_activity_data_todo').id,
                        'res_model_id': self.sudo().env['ir.model'].search([('model', '=', 'purchase.request')], limit=1).id,
                        'note': "",
                        'res_id': res.id,
                        'user_id': user.id
                    })
        return res

    @api.depends('purchase_product_type')
    def _compute_show_tender_btn(self):
        for rec in self:
            if rec.purchase_product_type in ('new', 'price_change', 'negociation') and self.env.user.has_group(
                    'purchase_request.group_purchase_request_manager'):
                rec.show_tender_btn = True
            else:
                rec.show_tender_btn = False

    def create_tender(self):

        tender_line_ids = [(0, 0, {'product_id': x.product_id.id if x.product_id else self.env.ref(
            'purchase_request_extend.product_product_new').id,
                                   'product_qty': x.product_qty,
                                   'product_uom_id': x.product_id.uom_id.id,
                                   'price_unit': x.estimated_cost,
                                   }) for x in self.line_ids]
        context = {
            'default_line_ids': tender_line_ids,
            'default_user_id': self.assigned_to.id
        }

        tender_vals = {
            'line_ids': tender_line_ids,
            'user_id': self.assigned_to.id
        }
        if self.line_ids:
            tender_vals['currency_id'] = self.line_ids[0].currency_id.id or self.env.user.company_id.currency_id.id
        tender_id = self.env['purchase.requisition'].create(tender_vals)

        self.tender_id = tender_id
        return {'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': tender_id.id,
                'res_model': 'purchase.requisition',
                'target': 'new',
                'context': context,
                }

    def button_approved_resp(self):
        return self.write({"state": "to_approve", "validation_date": fields.Date.today()})

    def button_to_approve(self):
        user_id = self.sudo().env['res.users'].browse(self.responsible_id.id)
        activity_id = self.sudo().env['mail.activity'].create({
            'summary': 'Demande d\'achat numéro ' + self.name + ' à approuver',
            'activity_type_id': self.sudo().env.ref('mail.mail_activity_data_todo').id,
            'res_model_id': self.sudo().env['ir.model'].search([('model', '=', 'purchase.request')], limit=1).id,
            'note': "",
            'res_id': self.id,
            'user_id': self.responsible_id.id
        })
        return self.write({"state": "superieur_approval"})

    def button_approved(self):
        state = 'approved'
        if self.purchase_product_type == 'new':
            state = 'daf_approval'
        self.write({
            'state': state
        })

    def button_approved_daf(self):
        self.write({
            'state': 'dg_approval'
        })

    def button_approved_dg(self):
        self.write({
            'state': 'approved'
        })

    def _get_dg_task_domain(self):
        group_dg = self.env.ref('purchase_request_extend.group_dg')
        return [('id', 'in', group_dg.users.mapped('id'))]

    def _get_daf_task_domain(self):
        group_daf = self.env.ref('purchase_request_extend.group_daf')
        return [('id', 'in', group_daf.users.mapped('id'))]

    @api.depends('purchase_type')
    def _compute_resp_achat(self):
        for rec in self:
            group_resp_achat_local = self.env.ref('purchase_request_extend.group_al')
            group_resp_achat_import = self.env.ref('purchase_request_extend.group_ai')
            if self.purchase_type == 'local':
                if group_resp_achat_local.users:
                    rec.assigned_to = group_resp_achat_local.users[0]
            else:
                if group_resp_achat_import.users:
                    rec.assigned_to = group_resp_achat_import.users[0]

    @api.depends('assigned_to', 'state')
    def _can_approve(self):
        for rec in self:
            rec.can_approve = rec.assigned_to == self.env.user and self.env.user.has_group(
                'purchase_request.group_purchase_request_manager') \
                              and rec.state == 'to_approve'

    @api.depends('responsible_id', 'state')
    def _can_approve_resp(self):
        for rec in self:
            rec.can_approve_resp = rec.responsible_id == self.env.user and self.env.user.has_group(
                'purchase_request.group_purchase_request_manager') \
                                   and rec.state == 'superieur_approval'

    @api.depends('daf_id', 'state')
    def _can_approve_daf(self):
        for rec in self:
            rec.can_approve_daf = rec.daf_id == self.env.user and self.env.user.has_group(
                'purchase_request.group_purchase_request_manager') \
                                  and rec.state == 'daf_approval' \
                                  and rec.purchase_product_type == 'new'

    @api.depends('dg_id', 'state')
    def _can_approve_dg(self):
        for rec in self:
            rec.can_approve_dg = rec.dg_id == self.env.user and self.env.user.has_group(
                'purchase_request.group_purchase_request_manager') \
                                 and rec.state == 'dg_approval' \
                                 and rec.purchase_product_type == 'new'
