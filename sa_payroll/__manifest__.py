# -*- coding: utf-8 -*-
{
    'name'        : 'SA Payroll',
    'version'     : '17.0.0.1',
    "author"      : "ERPWEB",
    "support"     : "pinakin@erpweb.co.za",
    'category'    : 'Human Resources/Payroll',
    'summary'     : '''South Africa Payroll Extended''',
    'description' : """ South Africa Payroll Extended.
    """,
    'depends'     : [
                        "account",
                        "hr_contract", 
                        'hr_payroll',
                        'account_asset',
                        'hr_holidays',
                        'sale_management',
                        'hr_payroll_expense',
                        'report_xlsx'
                    ],
    'data'        : [
                        'report/report_action.xml',
                        'data/salary_data.xml',
                        "security/ir.model.access.csv",
                        'views/settings.xml',
                        "views/contract_view.xml",
                        'views/salary_rule.xml',
                        'views/salary_structure.xml',
                        'views/hr_payslip.xml',
                        'views/easyfile_view.xml',
                        'wizard/leave_pay_wiz_view.xml',
                        'views/sale_view.xml',
                        'views/hr_expense_view.xml',

                        'views/emp_201_report_view.xml',
                        'views/emp_summary_report.xml',
                        'views/hr_payslip_report.xml',
                        'views/id_indicater_view.xml',
                        'views/report_action.xml',
                        'views/sa_emp_report.xml',


                        'report/payslip_report_extended.xml',
                        
                        'report/report_extend.xml',

                        'wizard/sa_emp_wizard.xml',
                        'wizard/workmans_compensation.xml',
                    ],
    'installable' : True,
    'auto_install': False,
    "price"       : 1000,
    "currency"    : "EUR",
    "images"      : ["static/description/banner.png",],
    'license'     : 'OEEL-1',
}

