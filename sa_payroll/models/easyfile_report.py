# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

from odoo.osv import expression

import csv
from odoo import api, fields, models, _
import base64
import csv
import io

class EasyfileReport(models.Model):
    _name = 'easyfile.report'
    _description='Easyfile Report'

    name = fields.Char(
        string='Name',
        required=True,
    )
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=datetime.now().strftime('%Y-%m-01')
    )
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=str(datetime.now() + relativedelta(months=+1, day=1, days=-1))[:10]
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help='Leave empty to consider all employees.'
    )

    payslip_ids = fields.Many2many(
        'hr.payslip',
        string='Payslips',
    )

    emp_201 = fields.Binary(
        string='EMP201',
        attachment=True,
    )
    emp_501 = fields.Binary(
        string='EMP501',
        attachment=True,
    )

    def get_payslips(self):
        for rec in self:
            if rec.payslip_ids:
                rec.payslip_ids = []
            employee_ids = []
            all_payslips = self.env['hr.payslip'].search([('date_from','>=',rec.start_date), ('date_to','<=',rec.end_date), ('state','in',['done','paid'])])
            if rec.employee_ids:
                employee_ids = rec.employee_ids.ids
                all_payslips = self.env['hr.payslip'].search([('date_from','>=',rec.start_date), ('date_to','<=',rec.end_date), ('state','in',['done','paid']),('employee_id','in',employee_ids)])
            if all_payslips:
                rec.payslip_ids = [(6, 0, all_payslips.ids)]
            else:
                rec.payslip_ids = []
                raise UserError(_('No Payslip Found in this period.'))

    def get_uif_data(self, line_ids):
        if line_ids:
            amount = 0.0
            line_id = line_ids.filtered(lambda x: x.salary_rule_id.is_uif == True)
            amount = sum([abs(line.amount) for line in line_id])
        amount = "%.2f" % amount
        return amount

    def chec_employee_pay(self, line_ids):
        line_id = line_ids.filtered(lambda x: x.salary_rule_id.is_pay == True)
        return 'IRP5' if line_id else 'IT3(a)'

    def get_bank_type(self, employee_id):
        bank_account_type = 0
        if employee_id.bank_account_id and employee_id.bank_account_id.bank_account_type:
            if employee_id.bank_account_id.bank_account_type == 'not_paid_electronic':
                bank_account_type = 0
            if employee_id.bank_account_id.bank_account_type == 'current':
                bank_account_type = 1
            if employee_id.bank_account_id.bank_account_type == 'savings_transmission':
                bank_account_type = 2
            if employee_id.bank_account_id.bank_account_type == 'creit_card':
                bank_account_type = 3
            if employee_id.bank_account_id.bank_account_type == 'home_loan':
                bank_account_type = 4
            if employee_id.bank_account_id.bank_account_type == 'subs_share':
                bank_account_type = 5
            if employee_id.bank_account_id.bank_account_type == 'foreign':
                bank_account_type = 6
        return bank_account_type if bank_account_type else ' '

    def get_account_ownership(self, employee_id):
        account_ownership = 0
        if employee_id.bank_account_id and employee_id.bank_account_id.account_ownership:
            if employee_id.bank_account_id.account_ownership == 'own':
                account_ownership = 1
            if employee_id.bank_account_id.account_ownership == 'joint':
                account_ownership = 2
            if employee_id.bank_account_id.account_ownership == 'third_party':
                account_ownership = 3
        return account_ownership if account_ownership else ' '

    def get_gross_salary(self, line_ids):
        if line_ids:
            line_id = line_ids.filtered(lambda x: x.salary_rule_id.is_gross == True)
            return round(sum([abs(line.amount) for line in line_id]), 2)
        return 0.0

    def get_bonus_amount(self, line_ids):
        if line_ids:
            line_id = line_ids.filtered(lambda x: x.salary_rule_id.is_bonus == True)
            return round(sum([abs(line.amount) for line in line_id]),2)
        return 0.0

    def get_gross_employment_income(self, line_ids):
        if line_ids:
            line_id = line_ids.filtered(lambda x: x.salary_rule_id.is_gross_em_in_tx == True)
            return round(sum([abs(line.amount) for line in line_id]))
        return 0.0

    def get_deductions(self, line_ids):
        if line_ids:
            line_id = line_ids.filtered(lambda x: x.salary_rule_id.is_deductions_pa == True)
            return round(sum([abs(line.amount) for line in line_id]),2)
        return 0.0

    def get_voluntary_deductions(self, line_ids):
        if line_ids:
            line_id = line_ids.filtered(lambda x: x.salary_rule_id.is_voluntary_deduction == True)
            return round(sum([abs(line.amount) for line in line_id]),2)
        return 0.0

    def get_pay_amount(self, line_ids):
        if line_ids:
            line_id = line_ids.filtered(lambda x: x.salary_rule_id.is_pay == True)
            return round(sum([abs(line.amount) for line in line_id]),2)
        return 0.0


    def get_total_sdl_uif(self, line_ids):
        payslip_id = line_ids.mapped('slip_id')
        amount = 0.0
        if line_ids:
            uif_amount = self.get_uif_data(line_ids)
            amount = payslip_id[0].sdl + float(uif_amount)
        amount = "%.2f" % amount
        return amount

    def check_valid_phone_number(self, phone):
        if phone:
            if '+27' in phone:
                phone = phone.split('+27')[1]
                phone = "{}{}".format('0', phone)
        return phone.replace(" ", "")

    def get_compnay_row(self):
        payslip_ids = self.payslip_ids
        hr_employee = self.payslip_ids.mapped("employee_id").filtered(lambda x: x.department_id.is_hr)
        company_id = payslip_ids.mapped('company_id')[0]
        emp_city = ''
        emp_zip = ''
        emp_contry_code = ''
        emp_street = ''
        emp_street2 = ''
        name_sf = ''
        street_no = ''
        if hr_employee.private_city:
            emp_city = hr_employee.private_city
        if hr_employee.private_zip:
            emp_zip = hr_employee.private_zip
        if hr_employee.private_country_id:
            emp_contry_code = hr_employee.private_country_id.code
        if hr_employee.private_street2:
            emp_street2 = hr_employee.private_street2
        if hr_employee.private_street:
            emp_street = hr_employee.private_street
        return [
            2010,company_id.name,
            2015,'Live',
            2020, company_id.paye_ref_number,
            2022, company_id.sdl_ref_number,
            2024, company_id.uif_ref_number,
            2025, hr_employee.name if hr_employee else ' ',

            2036,'STEWART',
            2026, self.check_valid_phone_number(hr_employee.work_phone) if hr_employee.work_phone else '',
            2027, hr_employee.work_email if hr_employee.work_email else '',
            2028, company_id.commercial_payroll if company_id and company_id.commercial_payroll else ' ',
            2029, company_id.software_package if company_id and company_id.software_package else ' ',
            2030, 2023,
            2031,'202302',
            2081, emp_contry_code,
            2037,'N',
            2063, '',
            2064, emp_street,
            2065, emp_street2,
            2066, emp_city,
            2080, emp_zip,
            2082,85490,
            9999,
        ]

    def get_total_deductions(self, line_ids):
        total_deduction = 0.0
        total_deduction = self.get_deductions(line_ids) + self.get_voluntary_deductions(line_ids)
        return total_deduction

    def get_compnay_last_row(self, total_line, total_line_6030):
        payslip_ids = self.payslip_ids
        company_id = payslip_ids.mapped('company_id')[0]
        get_6020 = 0.0
        if total_line > 0:
            get_6020 = (51 * (total_line - 1) + 16)
        return [
            6010, str(total_line),
            6020, str(get_6020),
            6030, str(total_line_6030),
            9999
        ]


    def get_employee_row(self, employee_id):
        payslip_ids = self.payslip_ids.filtered(lambda x: x.employee_id == employee_id)
        line_6030 = 0.0
        emp_city = ''
        emp_zip = ''
        emp_contry_code = ''
        emp_street = ''
        emp_street2 = ''
        name_sf = ''
        street_no = ''
        if employee_id.private_city:
            emp_city = employee_id.private_city
        if employee_id.private_zip:
            emp_zip = employee_id.private_zip
        if employee_id.private_country_id:
            emp_contry_code = employee_id.private_country_id.code
        if employee_id.private_street2:
            emp_street2 = employee_id.private_street2
        if employee_id.private_street:
            emp_street = employee_id.private_street
        if employee_id:
            s_name = ' '
            if employee_id.emp_surname:
                s_name = employee_id.emp_surname[0]
            name_sf = "{}{}".format(employee_id.name[0], s_name)

        acc_number = employee_id.bank_account_id.acc_number if employee_id.bank_account_id and employee_id.bank_account_id.acc_number else ' '
        branch_code = employee_id.bank_account_id.branch_code if employee_id.bank_account_id and employee_id.bank_account_id.branch_code else ' '
        bank_name = employee_id.bank_account_id.bank_id.name if employee_id.bank_account_id and employee_id.bank_account_id.bank_id.name else ' '
        branch_location = employee_id.bank_account_id.branch_location if employee_id.bank_account_id and employee_id.bank_account_id.branch_location else ' '
        name_of_account = employee_id.bank_account_id.name_of_account if employee_id.bank_account_id and employee_id.bank_account_id.name_of_account else ' '
        line_6030 += self.get_gross_salary(payslip_ids.mapped('line_ids'))
        line_6030 += self.get_bonus_amount(payslip_ids.mapped('line_ids'))
        line_6030 += payslip_ids[0].contract_id.gross_retirement if payslip_ids[0].contract_id.gross_retirement else 0.0
        line_6030 += self.get_gross_employment_income(payslip_ids.mapped('line_ids'))
        line_6030 += self.get_deductions(payslip_ids.mapped('line_ids'))
        line_6030 += self.get_voluntary_deductions(payslip_ids.mapped('line_ids'))
        line_6030 += self.get_total_deductions(payslip_ids.mapped('line_ids'))
        line_4102 = self.get_pay_amount(payslip_ids.mapped('line_ids')) if self.get_pay_amount(payslip_ids.mapped('line_ids')) else 0.0
        line_4141 = str(self.get_uif_data(payslip_ids.mapped('line_ids')))
        line_4142 = payslip_ids[0].sdl if payslip_ids[0].sdl else 0.0
        line_4149 = float(line_4102) + float(line_4141) + float(line_4142)

        line = [
            3010, payslip_ids[0].certificate_number if payslip_ids[0].certificate_number else '7210790897202308VIPL0002000001',
            3015,self.chec_employee_pay(payslip_ids.mapped('line_ids')),
            3020,employee_id.ident_id.name if employee_id.ident_id else 'A',
            3025,payslip_ids[0].date_from.year,
            3030,employee_id.name if employee_id.name else ' ',

            3040,employee_id.emp_surname if employee_id.emp_surname else ' ',
            3050,'K',
            3060,employee_id.id_number if employee_id.id_number else ' ',
            3080,str(employee_id.birthday).replace('-', '') if employee_id.birthday else '',
            3100,employee_id.tax_no if employee_id.tax_no else ' ',


            3263,payslip_ids[0].company_id.standard_classification if payslip_ids[0].company_id.standard_classification else '',
            # 3125,
            # employee_id.private_email if employee_id.private_email else ' ',
            3136, self.check_valid_phone_number(payslip_ids[0].company_id.phone) if payslip_ids[0].company_id.phone else '',
            3138,"0824947024", #Missing
            3146,"4", # Missing
            3147,payslip_ids[0].company_id.street if payslip_ids[0].company_id.street else '',


            3148,payslip_ids[0].company_id.street2 if payslip_ids[0].company_id.street2 else '',
            3149,payslip_ids[0].company_id.city if payslip_ids[0].company_id.city else ' ',
            3150,payslip_ids[0].company_id.zip if payslip_ids[0].company_id.zip else ' ',
            3151,payslip_ids[0].company_id.country_id.code if payslip_ids[0].company_id.country_id.code else ' ',
            3160,employee_id.emp_code if employee_id.emp_code else ' ',


            3170,str(payslip_ids[0].contract_id.date_start).replace('-', ''),
            3180,str(payslip_ids[0].contract_id.date_end).replace('-', '') if payslip_ids[0].contract_id.date_end else '',
            3190,20220501, # missing on text 
            3195,'N',
            3285,emp_contry_code,


            3200,'12.0000',
            3210,str('{}.0000'.format(len(payslip_ids))),
            3220,'N',
            3213,street_no,
            3214,emp_street,


            3215,emp_street2,
            3216,emp_city,
            3217,emp_zip,
            3279,'N',
            3240,self.get_bank_type(employee_id),
            3241,acc_number,
            3242,branch_code,
            3245,name_of_account,
            3246,self.get_account_ownership(employee_id),


            3288,'1',
            3026,'N',
            3601,self.get_bonus_amount(payslip_ids.mapped('line_ids')) if self.get_bonus_amount(payslip_ids.mapped('line_ids')) else '',
            3699,self.get_gross_employment_income(payslip_ids.mapped('line_ids')) if self.get_gross_employment_income(payslip_ids.mapped('line_ids')) else '',
            4102,"%.2f" % line_4102,
            4141,line_4141,
            4142,"%.2f" % line_4142,
            4149, "%.2f" % line_4149 if line_4149 else "%.2f" % 0.00,
            9999]
        return line, line_6030

    def generare_report(self):
        self.ensure_one()
        output = io.StringIO()
        writer = csv.writer(output)
        header = self.get_compnay_row()
        writer.writerow(header)
        total_line = 1
        total_line_6030 = 0.0
        for employee_id in self.payslip_ids.mapped("employee_id"):
            new_row, line_6030 = self.get_employee_row(employee_id)
            total_line_6030+=line_6030
            writer.writerow(new_row)
            total_line = total_line + 1
        last_row = self.get_compnay_last_row(total_line, total_line_6030)
        writer.writerow(last_row)
        self.emp_501 = base64.b64encode(output.getvalue().encode())

        us_format = "%m_%d_%Y"
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/web/content?model=easyfile.report&download=true&field=emp_501&filename=501 report {} - {}.csv&id={}".format(
                self.start_date.strftime(us_format), self.end_date.strftime(us_format), self.id
            ),
        }

    # ACB Report
    generated_csv_file = fields.Binary(
        "Generated file",
        help="Technical field used to temporarily hold the generated CSV file before it's downloaded."
    )

    def _generate_row(self, payslip):
        company_bank_ids = payslip.company_id.partner_id.bank_ids
        acc_number = ''
        if company_bank_ids:
            acc_number = company_bank_ids[0].acc_number

        emp_bank_id = payslip.employee_id.bank_account_id
        branch_code = ''
        emp_acc_number = ''
        acc_holder_name=''
        if emp_bank_id:
            emp_acc_number = emp_bank_id.acc_number
            branch_code = emp_bank_id.branch_code
            if emp_bank_id.acc_holder_name:
                acc_holder_name = emp_bank_id.acc_holder_name
            else:
                if emp_bank_id.partner_id:
                    acc_holder_name = emp_bank_id.partner_id.name

        # net pay
        net_pay = 0
        net_line = payslip.line_ids.filtered(lambda x: x.category_id.code == 'NET')
        net_pay = net_line.total

        row = [
            acc_number,
            'SALARY',
            payslip.company_id.name,
            emp_acc_number,
            branch_code,
            # payslip.employee_id.name,
            acc_holder_name,
            'SALARY',
            net_pay
        ]
        row = [val or "" for val in row]  # replace False m2o's
        return row

    def action_generate(self):
        """ Called from UI. Generates the CSV file in memory and writes it to the generated_csv_file
        field. Then returns an action for the client to download it. """
        self.ensure_one()
        header = [
            "Account Number",
            "Receiver Reference",
            "Payee Reference",
            "Account Number",
            "Branch Code",
            "Name",
            "Reference",
            "Amount",
        ]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)

        curr_vendor = None
        curr_total = 0
        lines = self.payslip_ids.filtered(lambda x: not x.early_late_pay)
        for line in lines:
            new_row = self._generate_row(line)
            writer.writerow(new_row)

        self.generated_csv_file = base64.b64encode(output.getvalue().encode())

        us_format = "%m_%d_%Y"
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/web/content?model=easyfile.report&download=true&field=generated_csv_file&filename=Bank File report {} - {}.csv&id={}".format(
                self.start_date.strftime(us_format), self.end_date.strftime(us_format), self.id
            ),
        }

    def _generate_row_csv(self, payslip):
        company_bank_ids = payslip.company_id.partner_id.bank_ids
        acc_number = ''
        if company_bank_ids:
            acc_number = company_bank_ids[0].acc_number

        emp_bank_id = payslip.employee_id.bank_account_id
        branch_code = ''
        emp_acc_number = ''
        acc_holder_name=''
        if emp_bank_id:
            emp_acc_number = emp_bank_id.acc_number
            branch_code = emp_bank_id.branch_code
            if emp_bank_id.acc_holder_name:
                acc_holder_name = emp_bank_id.acc_holder_name
            else:
                if emp_bank_id.partner_id:
                    acc_holder_name = emp_bank_id.partner_id.name

        # net pay
        net_pay = 0
        net_line = payslip.line_ids.filtered(lambda x: x.category_id.code == 'NET')
        net_pay = net_line.total

        row = [
            acc_number,
            'SALARY',
            acc_holder_name,
            emp_acc_number,
            '',
            branch_code,
            acc_holder_name,
            'SALARY',
            net_pay
        ]
        row = [val or "" for val in row]  # replace False m2o's
        return row

    def action_generate_csv(self):
        """ Called from UI. Generates the CSV file in memory and writes it to the generated_csv_file
        field. Then returns an action for the client to download it. """
        self.ensure_one()
        header = [
            "From Account Number",
            "From Account Description",
            "My statement desription",
            "Beneficiary Account Number",
            "Beneficiary Sub Account Number",
            "Beneficiary Account Branch Code",
            "Beneficiary Name",
            "Beneficiary Statement Description",
            "Amount",
        ]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(header)

        curr_vendor = None
        curr_total = 0
        lines = self.payslip_ids.filtered(lambda x: not x.early_late_pay)
        for line in lines:
            new_row = self._generate_row_csv(line)
            writer.writerow(new_row)

        self.generated_csv_file = base64.b64encode(output.getvalue().encode())

        us_format = "%m_%d_%Y"
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": "/web/content?model=easyfile.report&download=true&field=generated_csv_file&filename=Bank File report {} - {}.csv&id={}".format(
                self.start_date.strftime(us_format), self.end_date.strftime(us_format), self.id
            ),
        }

    # 201 report
    def emp_201_report(self):
        self.get_payslips()
        return {
            'name': "EMP 201",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sa.emp.wizard',
            'view_id': self.env.ref('sa_payroll.view_sa_emp_report_wizard_form').id,
            'context': {'payslip_ids': self.payslip_ids.ids, 'start_date': self.start_date, 'end_date': self.end_date},
            'target': 'new',
            }


class ReaCompnay(models.Model):
    _inherit = "res.company"

    standard_classification = fields.Char(string="Standard Industrial Classification")
    building_number = fields.Char(string="Billing Number")
    building_name = fields.Char(string="Billing Name")
    commercial_payroll = fields.Char(string="Commercial Payroll")
    software_package = fields.Char(string="Software Package")
    year_of_assessment = fields.Char(string="Year of assessment")

    # 201 report
    paye_ref_number = fields.Char(string="PAYE reference number")
    sdl_ref_number = fields.Char(string="SDL reference number")
    uif_ref_number = fields.Char(string="UIF reference number")

    # workman
    specification_type = fields.Selection([('industry', 'Industry'), ('percentage', 'Percentage'), ('capped_amount', 'Capped Amount')], string="Specification Type")

class Respartner(models.Model):
    _inherit = "res.partner"

    street_no = fields.Char(string="Street No")
