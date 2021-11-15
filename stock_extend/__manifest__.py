# -*- coding: utf-8 -*-

{
    "name": u"TKBETON: Stock",
    "version": "14.0",
    "depends": ['base', 'product', 'stock', 'maintenance_extend', 'hr', 'product_extend', 'purchase'],
    "author": "Osisoftware",
    "summary": "",
    'website': '',
    "category": "",
    "description": "Ajouter des infos sup",
    "init_xml": [],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/res_partner_views.xml',
        # 'views/citerne_views.xml',
        'report/report_picking_template.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
