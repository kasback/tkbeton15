# -*- coding: utf-8 -*-

{
    "name": u"TKBETON: Demande d'achat",
    "version": "14.0",
    "depends": ['base', 'purchase_request', 'purchase_requisition',
                'supplier_evaluation', 'product', 'product_extend', 'hr', 'citerne'],
    "author": "Osisoftware",
    "summary": "",
    'website': '',
    "category": "",
    "description": "",
    "init_xml": [],
    'data': [
        'data/data.xml',
        'report/purchase_order_report_templates.xml',
        'report/report.xml',
        'security/groups.xml',
        'security/rules.xml',
        'security/ir.model.access.csv',
        'views/purchase_request_views.xml',
        'views/purchase_order_views.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
