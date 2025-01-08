# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError, UserError

from odoo.osv import expression

class MedicalTaxStructureLine(models.Model):
    _name = 'medical.tax.structure.line'
    _description = 'Medical Tax Structure Line'

    level = fields.Integer(
        string='Level',
    )
    name = fields.Char(
        string='',
        size=64,
        required=False,
        readonly=False,
    )
    amount_monthly = fields.Float(
        string='Amount Monthly',
    )
    medical_tax_structure_id = fields.Many2one(
        'medical.tax.structure',
        string='Medical Structure',
    )

class MedicalTaxStructure(models.Model):
    _name = 'medical.tax.structure'
    _description = 'Medical Tax Structure'

    name = fields.Char(
        string='',
        size=64,
        required=False,
        readonly=False,
    )
    line_ids = fields.One2many(
        'medical.tax.structure.line',
        'medical_tax_structure_id',
        string='Lines',
    )


class TaxStructureLines(models.Model):
    _name='emp.tax.structure.lines'
    _description = "Tax Structure Lines"

    amount_from = fields.Float(
        string='Amount From',
    )
    amount_to = fields.Float(
        string='Amount To',
    )
    fix_amount = fields.Float(
        string='Fix Amount',
    )
    tax_amount = fields.Float(
        string='Tax(%)',
    )
    emp_tax_structure_id = fields.Many2one(
        'emp.tax.structure',
        string='Tax Structure',
    )

class TaxStructure(models.Model):
    _name='emp.tax.structure'
    _description = "Tax Structure"
    _rec_name= 'name'

    name = fields.Char(
        string='Name',
    )
    structure_line_ids = fields.One2many(
        'emp.tax.structure.lines',
        'emp_tax_structure_id',
        string='Lines',
    )
    rebate = fields.Float(
        string='Rebate(yearly)',
    )

class MonthbyMonth(models.Model):
    _name='month.by.month'
    _description = "Month by Month"
    _rec_name= 'id'

    month = fields.Char(
        string='Month',
    )
    wage = fields.Float(
        string='Monthly Wage',
    )
    to_update = fields.Boolean(
        string='To Update',
        default= False
    )
    to_update_amount = fields.Float(
        string='To Update amount',
        default=0
    )
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
    )
    bonus = fields.Float(
        string='Bonus',
    )
    total = fields.Float(
        string='Total',
        compute='_compute_total',
        store=True,
    )

    @api.depends('wage','bonus')
    def _compute_total(self):
        for rec in self:
            rec['total'] = rec.wage + rec.bonus

class SalaryIncrease(models.Model):
    _name = 'emp.salary.increase'
    _description = "Salary Increase"
    _rec_name= 'id'

    contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
    )
    increase_month = fields.Integer(
        string='Increase Month',
    )
    old_amount = fields.Float(
        string='Prevoius FCC',
    )
    increase_amount = fields.Float(
        string='Increase Amount',
        compute='_compute_increase_amount',
        store=True,
    )
    is_triggered = fields.Boolean(
        string='Is Triggered',
    )
    to_hide = fields.Boolean(
        string='Hide',
        default=False
    )
    year = fields.Integer(
        string='Year',
    )
    new_monthly_fixed_ctc = fields.Float(
        string='New Monthly Fixed CTC',
    )

    @api.depends('new_monthly_fixed_ctc','old_amount')
    def _compute_increase_amount(self):
        for rec in self:
            rec.increase_amount = 0
            if rec.new_monthly_fixed_ctc > 0:
                rec.increase_amount = rec.new_monthly_fixed_ctc - rec.old_amount


    def action_apply_increase(self):
        # now = fields.Datetime.now()
        # if self.increase_month != now.month:
        #     raise UserError('Current Month is not match. You can apply only in increase month.')
        month_data = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September',
                      10: 'October', 11: 'November', 12: 'December'}
        if self.contract_id:
            self.old_amount = self.contract_id.monthly_cost_to_company
            to_update = self.contract_id.month_by_month_salary_ids.filtered(lambda x: x.month == month_data[self.increase_month])
            months_to_update = []
            i = self.increase_month

            if self.increase_month not in [1,2]:
                for i in range(self.increase_month, 13):
                    months_to_update.append(month_data[i])
                i = 1
                for i in range(i, 3):
                    months_to_update.append(month_data[i])
            else:
                if self.increase_month == 1:
                    for i in range(self.increase_month, 3):
                        months_to_update.append(month_data[i])
                else:
                    months_to_update.append(month_data[self.increase_month])

            total_salary = self.old_amount + self.increase_amount
            to_update = self.contract_id.month_by_month_salary_ids.filtered(lambda x: x.month in months_to_update)
            to_update.wage = total_salary

            self.contract_id.monthly_cost_to_company = total_salary#self.contract_id.monthly_cost_to_company + self.increase_amount
            #self.contract_id._comput_cost_to_company()
            self.is_triggered= True

class HrPayslipInputType(models.Model):
    _inherit = "hr.payslip.input.type"

    is_default_advantage = fields.Boolean(
        string='Is Default Advantage?',
        default=False
    )

class Contract(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def default_get(self, field_list=None):
        res = super().default_get(field_list)
        
        input_line_vals = []
        all_input_lines= self.env['hr.payslip.input.type'].search([('is_default_advantage','=', True)])
        for line in all_input_lines:
            input_line_vals.append(Command.create({
                            'amount': 0,
                            'input_type_id': line.id,
                        }))

        res.update({'advantages_ids': input_line_vals})
        return res

    advantages_ids = fields.One2many(
        "hr.contract.advantage", "contract_id", string="Contract Advantages"
    )

    emp_tax_structure_id = fields.Many2one(
        'emp.tax.structure',
        string='Tax Structure',
    )
    month_by_month_salary_ids = fields.One2many(
        'month.by.month',
        'contract_id',
        string='Month By Month',
        #compute='_compute_by_month'
    )
    financial_year_month_start = fields.Integer(
        string='Financial Year Month Start',
        default=3
    )
    total_yearly_wage = fields.Float(
        string='Yearly Wage',
        compute='_compute_yearly_wage',
        store=True
    )
    current_month = fields.Integer(
        string='Current Month Test',
        default=3
    )

    show_in_detail = fields.Boolean(
        string='Show Detail',
        default=False
    )

    # medical allowances
    eligible_for_tax_rebate = fields.Boolean(
        string='Eligible for Tax rebate?',
    )
    medical_structure_id = fields.Many2one(
        'medical.tax.structure',
        string='Medical Structure',
    )
    spouse = fields.Boolean(
        string='Spouse',
    )
    no_of_children = fields.Integer(
        string='# of Children',
    )
    other_dependents = fields.Integer(
        string='Other Dependents',
    )
    medical_amount= fields.Float('Medical Amount')

    company_vehicle = fields.Float(
        string='Company Vehicle Amount',
    )
    company_vehicle_id = fields.Many2one(
        'account.asset',
        string='Company Vehicle',
    )

    overtime_1_5 = fields.Float(
        string='Overtime 1.5(Rate)',
    )

    overtime_2_0 = fields.Float(
        string='Overtime 2.0 (Rate)',
    )
    overtime_zar = fields.Float(
        string='Overtime ZAR',
    )

    standby_ah_all = fields.Float(
        string='Standby A/H',
    )

    shift_allowance = fields.Float(
        string='Shift Allowance',
    )

    var_reg_bonus = fields.Float(
        string='VAR Reg Bonus',
    )
    commission = fields.Float(
        string='Commission',
    )
    staff_transport = fields.Float(
        string='Staff Transport',
    )

    #ETI calculation
    # eti_structure_id = fields.Many2one(
    #     'eti.structure',
    #     string='ETI Structure',
    # )
    qualify_for_eti = fields.Boolean(
        string='Qualify for ETI?',
    )
    first_year = fields.Boolean(
        string='First Year',
    )
    second_year = fields.Boolean(
        string='Second Year',
    )

    #SDL
    sdl_rate = fields.Integer(
        string='SDL Rate',
        compute='_compute_require_signature',
        store=True,
    )
    @api.depends('wage','company_id')
    def _compute_require_signature(self):
        for contract in self:
            contract.sdl_rate = self.env['ir.config_parameter'].sudo().get_param(
            'sa_payroll.sdl_rate'
        )

    gross_retirement= fields.Float(string="Gross Retirement")

    id_number_on_palyslip = fields.Boolean(string="ID Display on payslip", help="This field are used to diplay on playslip")

    # Provident Fund
    employer_provident_fund = fields.Float(
        string='Employer Provident Fund',
    )
    provident_fund_percent = fields.Float(
        string='Provident Fund (%)',
    )
    # employee_provident_fund = fields.Float(
    #     string='Employee Provident Fund',
    # )
    # provident_fund_max = fields.Float(
    #     string='Provident Fund Max.',
    # )

    # additional fields
    annual_fix_cost_to_company = fields.Float(
        string='Annual Fixed Cost to Company',
        compute='_comput_cost_to_company',
        compute_sudo=True
    )
    annual_bonus = fields.Float(
        string='Annual Bonus',
    )
    bonus_month = fields.Float(
        string='Bonus Month',
    )
    total_cost_to_company = fields.Float(
        string='Total Cost to Company',
        compute='_comput_cost_to_company',
        compute_sudo=True
    )
    monthly_cost_to_company = fields.Float(
        string='Monthly Fixed Cost to Company',
        #compute='_comput_cost_to_company'
    )

    # commission
    target_commision_amount = fields.Float(
        string='Target Commission Amount',
    )
    # commision_plan = fields.
    commission_type = fields.Selection([
        ('fix', 'Fixed Amount'),
        ('perc', 'Percentage'),
    ])
    commission_amount = fields.Float()

    # Pension
    pension_fund_contribution_by_employee = fields.Float(
        string='Pension Contribution (by Employee)',
    )
    pension_fund_contribution_by_employer = fields.Float(
        string='Pension Contribution (by Employer)',
        help="This is a company contribution - percentages will differ for each employee and are based on what the employee decided on at start date. The contribution to the fund is compulsory with a minimum contribution of 5% and a maximum of 27.5%",
        default=5.00,
        required=True,
    )

    # other allowances
    executive_allowance = fields.Float(
        string='Executive Allowance',
        help='Executive allowance is a type of benefit given to executives.', 
    )
    graveyard_shift_allowance = fields.Float(
        string='Graveyard Shift Allowance',
    )
    cell_phone_allowance = fields.Float(
        string='Cell Phone Allowance',
    )

    # company contribution
    disability_cover = fields.Float(
        string='Disability Cover',
    )
    my_health = fields.Float(
        string='My Health',
    )
    vitality = fields.Float(
        string='Vitality',
    )
    # death_benefit = fields.Float(
    #     string='Death Benefit',
    # )
    # admin_fee = fields.Float(
    #     string='Admin Fee',
    # )

    total_company_contribution = fields.Float(
        string='Total Company Contribution',
        compute="_compute_total_company_contribution"
    )
    
    # backpay_disability_cover = fields.Float(
    #     string='Backpay Disability Cover',
    # )
    # backpay_life_insurance = fields.Float(
    #     string='Backpay Life Insurance',
    # )
    # backpay_provident_fund = fields.Float(
    #     string='Backpay Provident Fund',
    # )

    # backpay_vitality = fields.Float(
    #     string='Backpay Vitality',
    # )

    # backpay_medical_aid = fields.Float(
    #     string='Backpay Medical Aid',
    # )

    medical_aid_contribution = fields.Float(
        string='Medical Aid',
    )

    life_insurance = fields.Float(
        string='Life Insurance',
    )

    # skill_development_levy = fields.Float(
    #     string='Skills Development Levy',
    # )

    # smart_funder_basic_education_tax = fields.Float(
    #     string='Smart Funder Basic Education Tax',
    # )

    # smart_funder_further_education_tax = fields.Float(
    #     string='Smart Funder Further Education Tax',
    # )

    # unemployment_insurance_fund = fields.Float(
    #     string='Unemployment Insurance Fund',
    # )
    salary_increase_ids = fields.One2many(
        'emp.salary.increase',
        'contract_id',
        string='Salary Increase',
        domain="[('to_hide','=',False)]"
    )

    def clear_data_new_year(self):
        now = fields.Datetime.now()
        current_month = now.month
        if current_month != 3:
            raise UserError(_('You cannot reset. You can reset only in March.'))
        for rec in self:
            if rec.salary_increase_ids:
                rec.salary_increase_ids.to_hide = True
            rec.annual_bonus =0
            rec.bonus_month=False
            rec.copy_month_wise_data()

    @api.onchange('annual_bonus','bonus_month')
    def onchange_bonus(self):
        month_data = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September',
                      10: 'October', 11: 'November', 12: 'December'}
        for rec in self:
            if rec.month_by_month_salary_ids:
                if rec.bonus_month:
                    reset_previous = rec.month_by_month_salary_ids.filtered(lambda x: x.bonus > 0)
                    reset_previous.bonus = 0
                    to_update = rec.month_by_month_salary_ids.filtered(lambda x: x.month == month_data[rec.bonus_month])
                    to_update.bonus = rec.annual_bonus  

    @api.depends('life_insurance','medical_aid_contribution','employer_provident_fund','disability_cover','vitality','my_health')
    def _compute_total_company_contribution(self):
        for rec in self:
            total_contribution = rec.life_insurance + rec.medical_aid_contribution + rec.employer_provident_fund + rec.disability_cover + rec.vitality + rec.my_health

            # my_health = rec.advantages_ids.filtered(lambda x: x.input_type_id.code == 'MY_HEALTH')
            # total_contribution += my_health.amount
            rec.total_company_contribution = total_contribution
    
    def _set_overtime_rate(self):
        for contract in self:
            if contract.structure_type_id.default_resource_calendar_id:
                resource_calendar_id = contract.structure_type_id.default_resource_calendar_id
            else:
                resource_calendar_id = contract.resource_calendar_id

            days_per_week = resource_calendar_id._get_days_per_week()
            hours_per_day = resource_calendar_id.hours_per_week
            #hourly_rate = ((contract.monthly_cost_to_company/4.333)/days_per_week)/hours_per_day
            hourly_rate = (contract.monthly_cost_to_company/21.67)/8

            contract.overtime_1_5 = hourly_rate*1.5
            contract.overtime_2_0 = hourly_rate*2

        #Salary / 4.333 to get weekly rate then divide by 5 
        # if working 5 day week to get daily rate then divide by 8 hours to get hourly rate then multiply by 1.5 or 2


    @api.depends('monthly_cost_to_company','annual_bonus','total_company_contribution')
    def _comput_cost_to_company(self):
        for rec in self:
            company_contribution = rec.total_company_contribution
            basic = rec.wage
            # calculate Overtime
            rec._set_overtime_rate()
            allowances = rec.company_vehicle
            total_yearly_wage = sum(l.wage for l in rec.month_by_month_salary_ids)
            rec.annual_fix_cost_to_company = total_yearly_wage#rec.monthly_cost_to_company * 12#(basic + company_contribution + allowances) * 12

            total_yearly_income = sum(l.total for l in rec.month_by_month_salary_ids)
            rec.total_cost_to_company = total_yearly_income#rec.annual_fix_cost_to_company + rec.annual_bonus
            rec.wage = rec.monthly_cost_to_company - company_contribution - allowances

    @api.depends('month_by_month_salary_ids', 'month_by_month_salary_ids.total')
    def _compute_yearly_wage(self):
        for rec in self:
            total = 0
            for line in rec.month_by_month_salary_ids:
                total += line.total
            rec['total_yearly_wage'] = total

    @api.depends('wage')
    @api.onchange('wage')
    def _onchange_wage(self):
        if self.financial_year_month_start == 0 or self.financial_year_month_start > 12:
            raise UserError(_('Please set correct Start Month.'))
        current_month = self.current_month
        month_data = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September',
                      10: 'October', 11: 'November', 12: 'December'}

        f_month = self.financial_year_month_start
        if current_month > f_month:
            for i in range(current_month, 13):
                line = self.month_by_month_salary_ids.filtered(lambda x: x.month == month_data[i])
                if line:
                    line.wage = self.monthly_cost_to_company

            for i in range(1,f_month):
                line = self.month_by_month_salary_ids.filtered(lambda x: x.month == month_data[i])
                if line:
                    line.wage = self.monthly_cost_to_company

            for i in range(f_month, current_month):
                line = self.month_by_month_salary_ids.filtered(lambda x: x.month == month_data[i])
                if line:
                    line.to_update = True
                    line.to_update_amount = self.monthly_cost_to_company
        else:
            for i in range(current_month,f_month):
                line = self.month_by_month_salary_ids.filtered(lambda x: x.month == month_data[i])
                if line:
                    line.wage = self.monthly_cost_to_company


    def copy_month_wise_data(self):
        now = fields.Datetime.now()
        current_month = now.month

        if self.month_by_month_salary_ids:
            if current_month != 3:
                raise UserError(_('You cannot reset. You can reset only in March.'))

        month_data = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September',
                      10: 'October', 11: 'November', 12: 'December'}
        for rec in self:
            rec.month_by_month_salary_ids = [(5, 0)]
            i = rec.financial_year_month_start
            vals=[]
            for i in range(i, 13):
                vals.append({
                         'month': month_data[i],
                         'wage': rec.monthly_cost_to_company,
                })

            i = rec.financial_year_month_start
            for i in range(1,i):
                vals.append({
                         'month': month_data[i],
                         'wage': rec.monthly_cost_to_company,
                })

            if rec.bonus_month and rec.annual_bonus:
                vals[int(rec.bonus_month)-rec.financial_year_month_start]['bonus'] = rec.annual_bonus

            rec.month_by_month_salary_ids = [(0,0, val) for val in vals]

    def get_financial_period(self, date):
        year = date.year

        print ('date====>>>',date)
        start_date = date.replace(day=1,month=3,year=year)
        end_date = date.replace(day=28,month=2,year=year+1)

        if date.month in [1,2]:
            start_date = date.replace(day=1,month=3,year=year-1)
            end_date = date.replace(day=28,month=2,year=year)

        return start_date, end_date

    def sage_avg_emp_monthly_tax(self, salary, paid_amount, payslip):
        date = payslip.date_from
        current_month = date.month
        total_taxable = final_tax_amount= 0
        start_date, end_date = self.get_financial_period(date)
        all_payslips = self.env['hr.payslip'].search([('date_from','>=',start_date), ('date_to', '<=',end_date),('state', 'in', ['done','paid']),('employee_id','=',payslip.employee_id.id)])
        result = False

        date_to_compare = self.date_start
        if self.original_start_date:
            date_to_compare = self.original_start_date
        if date_to_compare > start_date:
            result= True

        if all_payslips or result:
            all_lines = all_payslips.mapped('line_ids')
            taxable_income = all_lines.filtered(lambda x: x.salary_rule_id.code == '3601(3)')
            
            # from contract year to date
            if self.taxable_earnings_amount > 0:
                if taxable_income:
                    taxable_income += self.taxable_earnings_amount

            till_now_taxable_income = sum(line.amount for line in taxable_income)

            total_taxable = till_now_taxable_income + salary # include current month taxable

            remaining_months = 0
            month_to_consider = 0
            if result:
                current_contract_month = date_to_compare.month#self.date_start.month
                if current_contract_month in [3,4,5,6,7,8,9,10,11,12]:
                    month_to_consider = 12 - current_contract_month +3
                if current_contract_month in [1]:
                    month_to_consider = 2
                if current_contract_month in [2]:
                    month_to_consider = 1
                if not all_payslips:
                    remaining_months = 1
                    if remaining_months > 0:
                        total_taxable = till_now_taxable_income + self.wage
                        total_taxable = total_taxable/remaining_months*month_to_consider
                else:
                    remaining_months = len(all_payslips.ids)+1
                    if remaining_months > 0:
                        total_taxable = (total_taxable/remaining_months)*month_to_consider
            else:
                if current_month in [3,4,5,6,7,8,9,10,11,12]:
                    remaining_months = current_month -2
                if current_month in [1]:
                    remaining_months = 12- current_month

                if current_month in [2]:
                    remaining_months = 12

                if remaining_months > 0:
                    total_taxable = total_taxable/remaining_months*12

            line = self.emp_tax_structure_id.structure_line_ids.sorted(lambda x: x.tax_amount).filtered(lambda x: x.amount_to >= total_taxable)
            if line[0]:
                total_tax = ((total_taxable - line[0].amount_from)*line[0].tax_amount/100) + line[0].fix_amount

                total_tax -= self.emp_tax_structure_id.rebate
                if result:
                    if not all_payslips and salary != self.wage:
                        total_tax = salary*total_tax/self.wage

                if total_tax > 0:
                    # medical tax credit
                    total_tax -= self.medical_amount*12
                    # find out already tax paid
                    total_tax_lines = all_lines.filtered(lambda x: x.salary_rule_id.code == '4102')
                    total_tax_paid = sum(line.amount for line in total_tax_lines)
                    # from year to date
                    if self.tax_paid_amount > 0:
                        total_tax_paid += self.tax_paid_amount
                    tax_due_for_year = total_tax/12*remaining_months - abs(total_tax_paid)
                    if result:
                        if month_to_consider > 0:
                            tax_due_for_year = total_tax/month_to_consider*remaining_months - abs(total_tax_paid)

                    final_tax_amount = tax_due_for_year
        else:
            total_taxable = salary
            current_month_taxable_income = salary
            if date.month == self.bonus_month:
                current_month_taxable_income = salary - self.annual_bonus

            remaining_months = 0
            if current_month in [3,4,5,6,7,8,9,10,11,12]:
                remaining_months = 14 - current_month
            if current_month in [1, 2]:
                remaining_months = 2- current_month

            if remaining_months > 0:
                total_taxable += (current_month_taxable_income * remaining_months)

            line = self.emp_tax_structure_id.structure_line_ids.sorted(lambda x: x.tax_amount).filtered(lambda x: x.amount_to >= total_taxable)
            if line[0]:
                total_tax = ((total_taxable - line[0].amount_from)*line[0].tax_amount/100) + line[0].fix_amount
                total_tax -= self.emp_tax_structure_id.rebate

                # medical tax credit
                total_tax -= self.medical_amount*12

                total_tax_paid = 0
                if self.tax_paid_amount > 0:
                    total_tax_paid += self.tax_paid_amount

                tax_due_for_year = total_tax - total_tax_paid
                final_tax_amount = tax_due_for_year/(remaining_months+1)

        return final_tax_amount

    def sage_emp_monthly_tax(self, salary, paid_amount, payslip):
        date = payslip.date_from
        current_month = date.month
        total_taxable = final_tax_amount= 0
        start_date, end_date = self.get_financial_period(date)
        all_payslips = self.env['hr.payslip'].search([('date_from','>=',start_date), ('date_to', '<=',end_date),('state', 'in', ['done','paid']),('employee_id','=',payslip.employee_id.id)])
        if all_payslips:
            all_lines = all_payslips.mapped('line_ids')
            taxable_income = all_lines.filtered(lambda x: x.salary_rule_id.code == '3601(3)')
            # from contract year to date
            if self.taxable_earnings_amount > 0:
                taxable_income += self.taxable_earnings_amount

            till_now_taxable_income = sum(line.amount for line in taxable_income)

            total_taxable = till_now_taxable_income + salary # include current month taxable

            # find out current month taxable income excluding bonus
            current_month_taxable_income = salary
            if date.month == self.bonus_month:
                current_month_taxable_income = salary - self.annual_bonus

            remaining_months = 0
            if current_month in [3,4,5,6,7,8,9,10,11,12]:
                remaining_months = 14 - current_month
            if current_month in [1, 2]:
                remaining_months = 2- current_month

            if remaining_months > 0:
                total_taxable += (current_month_taxable_income * remaining_months)

            line = self.emp_tax_structure_id.structure_line_ids.sorted(lambda x: x.tax_amount).filtered(lambda x: x.amount_to >= total_taxable)
            if line[0]:
                total_tax = ((total_taxable - line[0].amount_from)*line[0].tax_amount/100) + line[0].fix_amount
                total_tax -= self.emp_tax_structure_id.rebate

                # medical tax credit
                total_tax -= self.medical_amount*12

                # find out already tax paid
                total_tax_lines = all_lines.filtered(lambda x: x.salary_rule_id.code == '4102')
                total_tax_paid = sum(line.amount for line in total_tax_lines)
                # from year to date
                if self.tax_paid_amount > 0:
                    total_tax_paid += self.tax_paid_amount

                remaining_months = 0
                if current_month in [3,4,5,6,7,8,9,10,11,12]:
                    remaining_months = current_month-2
                if current_month in [1]:
                    remaining_months = 12- current_month

                if current_month in [2]:
                    remaining_months = 12

                tax_due_for_year = 0
                if remaining_months > 0:
                    tax_due_for_year = total_tax/12*remaining_months - abs(total_tax_paid)

                #tax_due_for_year = total_tax - total_tax_paid
                final_tax_amount = tax_due_for_year#/(remaining_months+1)
        else:
            total_taxable = salary
            current_month_taxable_income = salary
            if date.month == self.bonus_month:
                current_month_taxable_income = salary - self.annual_bonus

            remaining_months = 0
            if current_month in [3,4,5,6,7,8,9,10,11,12]:
                remaining_months = 14 - current_month
            if current_month in [1, 2]:
                remaining_months = 2- current_month

            if remaining_months > 0:
                total_taxable += (current_month_taxable_income * remaining_months)

            line = self.emp_tax_structure_id.structure_line_ids.sorted(lambda x: x.tax_amount).filtered(lambda x: x.amount_to >= total_taxable)
            if line[0]:
                total_tax = ((total_taxable - line[0].amount_from)*line[0].tax_amount/100) + line[0].fix_amount
                total_tax -= self.emp_tax_structure_id.rebate

                # medical tax credit
                total_tax -= self.medical_amount*12

                # find out already tax paid
                #total_tax_lines = all_lines.filtered(lambda x: x.salary_rule_id.code == '4102')
                #total_tax_paid = sum(line.amount for line in total_tax_lines)
                # from year to date
                total_tax_paid = 0
                if self.tax_paid_amount > 0:
                    total_tax_paid += self.tax_paid_amount

                remaining_months = 0
                if current_month in [3,4,5,6,7,8,9,10,11,12]:
                    remaining_months = current_month-2
                if current_month in [1]:
                    remaining_months = 12- current_month

                if current_month in [2]:
                    remaining_months = 12

                if remaining_months > 0:
                    tax_due_for_year = total_tax/12*remaining_months - abs(total_tax_paid)

                #tax_due_for_year = total_tax - total_tax_paid
                final_tax_amount = tax_due_for_year#/(remaining_months+1)

        return final_tax_amount

    def emp_monthly_tax(self, salary, paid_amount):
        yearly = (self.total_yearly_wage - paid_amount) + salary
        total_tax = 0
        if self.emp_tax_structure_id:
            line = self.emp_tax_structure_id.structure_line_ids.sorted(lambda x: x.tax_amount).filtered(lambda x: x.amount_to >= yearly)
            if line[0]:
                total_tax = (((yearly - line[0].amount_from)*line[0].tax_amount/100)/12)+(line[0].fix_amount/12)

                if abs(total_tax) > 0:
                    monthly_rebate = self.emp_tax_structure_id.rebate/12
                    total_tax -= monthly_rebate

                    if total_tax < 0:
                        total_tax = 0
        return total_tax

    def emp_monthly_tax_current(self, salary, paid_amount):
        yearly = salary*12#(self.total_yearly_wage - paid_amount) + salary
        total_tax = 0
        if self.emp_tax_structure_id:
            line = self.emp_tax_structure_id.structure_line_ids.sorted(lambda x: x.tax_amount).filtered(lambda x: x.amount_to >= yearly)
            if line[0]:
                total_tax = (((salary - line[0].amount_from/12)*line[0].tax_amount/100))+(line[0].fix_amount/12)

                if abs(total_tax) > 0:
                    monthly_rebate = self.emp_tax_structure_id.rebate/12

                    print ('monthly_rebate===>>',monthly_rebate)
                    total_tax -= monthly_rebate

                    if total_tax < 0:
                        total_tax = 0
        return total_tax

    def emp_monthly_medical_extra(self):
        if not self.eligible_for_tax_rebate:
            self.medical_amount = 0
        else:
            line = self.medical_structure_id.line_ids.filtered(lambda x: x.level == 1)
            amount = line.amount_monthly
            if self.spouse:
                line2 = self.medical_structure_id.line_ids.filtered(lambda x: x.level == 2)
                amount = line2.amount_monthly

                if self.no_of_children or self.other_dependents:
                    line3 = self.medical_structure_id.line_ids.filtered(lambda x: x.level == 3)
                    if line3:
                        amount += self.no_of_children * line3.amount_monthly
                        amount += self.other_dependents * line3.amount_monthly
            else:
                if self.no_of_children > 0:
                    children = self.no_of_children
                    amount += amount
                    children -= 1
                    if children > 0:
                        line3 = self.medical_structure_id.line_ids.filtered(lambda x: x.level == 3)
                        if line3:
                            amount += line3.amount_monthly * children
                else:
                    if self.other_dependents:
                        other_dependents = self.other_dependents
                        amount += amount
                        other_dependents -= 1
                        if other_dependents > 0:
                            line3 = self.medical_structure_id.line_ids.filtered(lambda x: x.level == 3)
                            if line3:
                                amount += line3.amount_monthly * other_dependents
            self.medical_amount = amount

    def emp_monthly_medical(self):
        if self.medical_structure_id:
            total_amount = 0
            if self.spouse:
                line = self.medical_structure_id.line_ids.filtered(lambda x: x.level == 1)
                total_amount += (line.amount_monthly*2)

            if self.no_of_children > 0:
                line = self.medical_structure_id.line_ids.filtered(lambda x: x.level == 2)
                total_amount += (line.amount_monthly * self.no_of_children)

                if self.other_dependents:
                    total_amount += (line.amount_monthly * self.other_dependents)

            else:
                if self.other_dependents > 0 and not self.spouse:
                    line = self.medical_structure_id.line_ids.filtered(lambda x: x.level == 3)
                    total_amount += (line.amount_monthly * 1)
                else:
                    if self.other_dependents:
                        line = self.medical_structure_id.line_ids.filtered(lambda x: x.level == 4)
                        total_amount += line.amount_monthly
                        if self.other_dependents > 2:
                            total_amount += (line.amount_monthly * 2)
                        else:
                            total_amount += (line.amount_monthly * self.other_dependents)

            if total_amount == 0:
                line = self.medical_structure_id.line_ids.filtered(lambda x: x.level == 1)
                total_amount += line.amount_monthly
            self.medical_amount = total_amount
