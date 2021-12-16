{
    'name': 'Tk-Beton - Maintenance',
    'version': '1.0',
    'category': 'MAintenance, MRP',
    'description': """""",
    'author': 'Osisoftware',
    'website': 'http://www.osisoftware.com',
    'depends': ['maintenance', 'hr', 'mrp'],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/maintenance_request_views.xml',
        'views/maintenance_equipement_type_views.xml',
        'views/maintenance_equipment_views.xml',
        'views/maintenance_configuration_views.xml',
        'views/maintenance_service_views.xml',
        'views/maintenance_line_views.xml',
        'views/maintenance_audit_views.xml',
        'views/maintenance_audit_lines_views.xml',
        'wizard/reinitialize_service_wizard_views.xml',
        'wizard/create_audit_wizard_views.xml',
    ],

}
