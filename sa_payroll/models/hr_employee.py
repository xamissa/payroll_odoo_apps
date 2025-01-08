# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import calendar

class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # These are required for manual attendance
    emp_code = fields.Char(related='employee_id.emp_code', readonly=True,string="Employee Code")
    kanow_as = fields.Char(related='employee_id.kanow_as',string="Known As")
    tax_no = fields.Char(related='employee_id.tax_no',string="Employee Tax No")
    emp_surname = fields.Char(related='employee_id.emp_surname',string="Surname")
    emp_date_completion = fields.Boolean(related='employee_id.emp_date_completion',string="Employment Date Completion")
    id_number = fields.Char(related='employee_id.id_number',string="ID Number")
    ident_id = fields.Many2one(related='employee_id.ident_id',string="Identification indicators")


class Employee(models.Model):
    _inherit = "hr.employee"

    last_payslip_generated_date = fields.Date(
        string='Last Generated Date',
        default=False,
        copy=False
    )

    emp_code = fields.Char(string="Employee Code")
    kanow_as = fields.Char(string="Known As")
    tax_no = fields.Char(string="Employee Tax No")
    emp_surname = fields.Char(string="Surname")
    emp_date_completion = fields.Boolean(string="Employment Date Completion")
    id_number = fields.Char(string="ID Number")
    ident_id = fields.Many2one('id.indicator', string="Identification indicators")

class PlayslipRule(models.Model):
    _inherit = "hr.salary.rule"

    is_pay = fields.Boolean(string="Is PAYE")
    is_uif = fields.Boolean(string="Is UIF")
    is_gross = fields.Boolean(string="IS Gross Salary")
    is_bonus = fields.Boolean(string="IS Bonus")
    is_gross_em_in_tx = fields.Boolean(string="IS Gross Emp Income(Tax)")
    is_deductions = fields.Boolean(string="Is Deductions / Contributions")
    is_earnings = fields.Boolean(string="Is Earnings")
    is_deductions_pa = fields.Boolean(string="Is Pension Fund")
    is_net_salary = fields.Boolean(string="Is Net Salary")
    is_net_salary = fields.Boolean(string="Is Net Salary")
    is_voluntary_deduction = fields.Boolean(string="Is Voluntary Deduction")
    is_com_contributions = fields.Boolean(string="Is Company Contributions")
    is_taxebal_income = fields.Boolean(string="Is Taxable Income")
    is_diduction = fields.Boolean(string="Is Deduction")

class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    branch_name = fields.Char(string="Branch Name")
    name_of_account = fields.Char(string="Name on Account")
    branch_code = fields.Char(string="Branch Code")
    branch_location = fields.Char(string="Branch Location")
    account_ownership = fields.Selection([('own', 'Own'), ('joint', 'Joint'), ('third_party', 'Third Party')], string="Account ownership")
    bank_account_type = fields.Selection([
            ('not_paid_electronic', 'Not Paid Electronic'), 
            ('current', 'Current'), 
            ('savings_transmission', 'Savings/Transmission'), 
            ('creit_card', 'Creit card'),
            ('home_loan', 'Home Loan'),
            ('subs_share', 'Subs share'),
            ('foreign', 'Foreign')], string="Bank Account Type")

class HRContract(models.Model):
    _inherit = 'hr.contract'

    tax_paid_amount = fields.Float(string="Tax Paid Amount")

    taxable_earnings_amount = fields.Float(string="Taxable Earnings Amount")

    taxable_company_contributions_amount = fields.Float(string="Taxable Company Contributions Amount")


    fringe_benefits_amount = fields.Float(string="Fringe Benefits Amount")

    tax_deductible_ductions_amount = fields.Float(string="Tax Deductible Deductions Amount")

    private_contributions_amount = fields.Float(string="Private Contributions Amount")

    original_start_date = fields.Date(
        string='Joined Group'
    )

    def _get_hourly_rate(self):
        for contract in self:
            if contract.structure_type_id.default_resource_calendar_id:
                resource_calendar_id = contract.structure_type_id.default_resource_calendar_id
            else:
                resource_calendar_id = contract.resource_calendar_id
            days_per_week = resource_calendar_id._get_days_per_week()
            hours_per_day = resource_calendar_id.hours_per_week
            hourly_rate = ((contract.wage/4.3333)/days_per_week)/hours_per_day
            return {'hours_per_day' : hours_per_day, 'hourly_rate' : hourly_rate, 'days_per_week' : days_per_week}

class HrSlip(models.Model):
    _inherit = 'hr.payslip'

    certificate_number = fields.Char(string="Certificate Number")
    no_of_payslip = fields.Integer(string="Number of Payslip", compute="_compute_no_payslip")

    def _compute_no_payslip(self):
        cnt = self.sudo().search_count([('employee_id', '=', self.employee_id.id), ('state', 'not in', ['draft', 'cancel'])])
        self.no_of_payslip = cnt

    def get_start_date_end_date(self):
        today = date.today()
        contract_id = self.contract_id
        if today.month in [1,2]:
            start_date = today.replace(year=today.year - 1, month=int(contract_id.financial_year_month_start), day=1)
        else:
            start_date = today.replace(year=today.year, month=int(contract_id.financial_year_month_start), day=1)
        end_date = self.date_to
        return start_date,end_date

    def get_taxable_rarnings(self):
        for rec in self:
            amount = 0.0
            start_date, end_date = rec.get_start_date_end_date()
            total_dict = {}
            taxable_company_contributions_amount = 0.0
            paid_amount = 0.0
            taxable_earning_amount = 0.0
            fringe_benefits_amount = 0.0
            all_payslips = self.env['hr.payslip'].search([('date_from','>=',start_date), ('date_to','<=',end_date), ('state','in',['done','paid']), ('employee_id', '=', self.employee_id.id)])
            #all_payslips += self
            if all_payslips:
                taxeble_paid_lines = all_payslips.mapped('line_ids').filtered(lambda x: x.name and x.name == 'PAYE')
                paid_amount = sum([abs(line.amount) for line in taxeble_paid_lines])
                # Taxable Earning
                payslip_line_ids = self.env['hr.payslip.line']

                taxeble_basic_lines = all_payslips.mapped('line_ids').filtered(lambda x: x.salary_rule_id and x.salary_rule_id.code in ['3601(3)'])
                #taxeble_allownce_lines = all_payslips.mapped('line_ids').filtered(lambda x: x.category_id and x.category_id.code == 'ALW')
                #payslip_line_ids = taxeble_basic_lines + taxeble_allownce_lines
                taxable_earning_amount = sum([abs(line.amount) for line in taxeble_basic_lines])
                # Taxable Company Contributions Amount
                taxable_company_contributions = all_payslips.mapped('line_ids').filtered(lambda x: x.salary_rule_id 
                    and x.salary_rule_id.code == '4142' 
                    or x.salary_rule_id.code == '4142(1)' 
                    or x.salary_rule_id.code == '4003' 
                    or x.salary_rule_id.code == '4477' 
                    or x.salary_rule_id.code == 'SK05' 
                    or x.salary_rule_id.code == '3801(3)'
                    or x.salary_rule_id.code == '3808'
                    or x.salary_rule_id.code == '4142'
                    )
                taxable_company_contributions_amount = sum([abs(line.amount) for line in taxable_company_contributions])

                # frindge benefits
                fringe_benefits_lines = all_payslips.mapped('line_ids').filtered(lambda x: x.salary_rule_id and x.salary_rule_id.code in ['4003'])
                fringe_benefits_amount = sum([abs(line.amount) for line in fringe_benefits_lines])

            total_dict.update({"taxable_paid" : paid_amount + self.contract_id.tax_paid_amount})
            total_dict.update({"taxable_earning" : taxable_earning_amount + self.contract_id.taxable_earnings_amount})
            total_dict.update({"taxable_company_contributions_amount" : taxable_company_contributions_amount + self.contract_id.taxable_company_contributions_amount})
            total_dict.update({"fringe_benefits" : fringe_benefits_amount + self.contract_id.fringe_benefits_amount})
            total_dict.update({"tax_deductible_deductions" : 0.0 + self.contract_id.tax_deductible_ductions_amount})
            total_dict.update({"private_contributions" : 0.0 + self.contract_id.private_contributions_amount})
               
            return total_dict

    def get_leave_balances(self):
        # leave_type_ids = self.env['hr.leave.type'].search([])
        # for leave_id in leave_type_ids:
        prepare_leave_dict = []
        data = self.env['hr.leave.type'].with_company(self.company_id).with_context(employee_id=self.employee_id.id).get_allocation_data_request()
        print("DATAAAAAAAAAAAAAAA", data)
        for record in data:
            if record[0] in ['Statutory leave','Additional Leave','Statutory CF','Additional CF']:
                prepare_leave_dict.append({
                    'leave_type' : record[0],
                    'remaining_leaves' : record[1].get('remaining_leaves')
                    })
        return prepare_leave_dict

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    no_of_allocation = fields.Float(string="Number Remaining Leaves")

class HrWorkEntryType(models.Model):
    _inherit = "hr.work.entry.type"

    is_show_payslip = fields.Boolean(string="Show on payslip")

class Hrpayslipinputtype(models.Model):
    _inherit = "hr.payslip.input.type"

    is_print = fields.Boolean(string="Is Print")

class Department(models.Model):
    _inherit = "hr.department"

    is_director = fields.Boolean(string="Is Director")
    is_hr = fields.Boolean(string="Is HR")

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string="Analytic Account",
        copy=False, check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

class ProductTrophy(models.Model):
    _name = "id.indicator"
    _description = "ID Indicator"

    name = fields.Char(
        string='Nature of Person', 
    )
    note = fields.Text(string="Description")