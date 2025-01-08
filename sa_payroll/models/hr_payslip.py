# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from datetime import datetime

from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import calendar

from odoo.osv import expression

class HrSlip(models.Model):
    _inherit = 'hr.payslip'

    @api.onchange('contract_id')
    def _compute_other_advance_input_line_ids(self):
        for slip in self:
            if slip.contract_id:
                if slip.contract_id.advantages_ids:
                    input_line_vals = []
                    #slip.input_line_ids = [(5,0)]#[Command.unlink(advantage) for advantage in slip.input_line_ids]
                    for line in slip.contract_id.advantages_ids.filtered(lambda x: x.input_type_id):
                        if line.input_type_id.id not in slip.input_line_ids.mapped('input_type_id').ids:
                            input_line_vals.append(Command.create({
                                'name': line.input_type_id.name,
                                'amount': line.amount,
                                'input_type_id': line.input_type_id.id,
                            }))
                    slip.update({'input_line_ids': input_line_vals})

    @api.model
    def _default_late_pay(self):
        late_pay = self.env['ir.config_parameter'].sudo().get_param('sa_payroll.late_pay')
        return late_pay or False

    eti = fields.Float(
        string='ETI',
    )
    sdl = fields.Float(
        string='SDL',
    )
    early_late_pay = fields.Boolean(
        string='Late Pay/Early Pay',
        default=_default_late_pay
    )

    # Leave Pay
    allow_leave_pay = fields.Boolean(
        related='struct_id.can_leave_pay_apply',
        string='Allow Leave Pay',
    )

    is_leave_pay = fields.Boolean(
        string='Is Leave Pay?',
        default=False,
        copy=False
    )

    leave_pay_for_weeks = fields.Integer(
        string='Leave Pay for Weeks',
    )

    leave_pay_calculated_till = fields.Date(
        string='Leave Pay Calculated Till'
    )

    leave_pay_type_ids = fields.One2many(
        'payslip.leave.pay',
        'payslip_id',
        string='Leave Pay Types',
        copy=False
    )

    is_severance_pay = fields.Boolean(
        string='Severance pay',
    )
    total_years_worked = fields.Float(
        string='Total Years Worked',
        compute='_compute_total_years_worked',
        store=True
    )
    week_pay = fields.Float(
        string='Week Pay',
    )
    employee_commission_amount = fields.Monetary(compute="get_employee_commission_amount", store=True)

    @api.depends('employee_id', 'date_from', 'date_to')
    def get_employee_commission_amount(self):
        self = self.sudo()
        for payslip in self:
            employee_commission_amount = 0
            related_user = payslip.employee_id.user_id
            if related_user:
                sale_orders = self.env['sale.order'].search([
                    ('user_id', '=', related_user.id),
                    ('date_order', '>=', payslip.date_from),
                    ('date_order', '<=', payslip.date_to),
                    ('state', 'in', ['sale', 'done']),
                ])
                employee_commission_amount = sum(sale_orders.mapped('employee_commission_amount'))
            payslip.employee_commission_amount = employee_commission_amount

    # @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to')
    # def _compute_input_line_ids(self):
    #     res = super()._compute_input_line_ids()
    #     for slip in self:
    #         if not slip.employee_id or not slip.date_from or not slip.date_to:
    #             continue
    #         if slip.struct_id.name == 'Regular Monthly Pay':
    #             # pension_fund_contribution_by_employee
    #             # warrant_type = self.env.ref('l10n_be_hr_payroll.cp200_other_input_warrant')
    #             lines_to_remove = slip.input_line_ids.filtered(lambda x: x.input_type_id == warrant_type)
    #             to_remove_vals = [(3, line.id, False) for line in lines_to_remove]
    #             to_add_vals = [(0, 0, {
    #                 'amount': warrant_value,
    #                 'input_type_id': self.env.ref('l10n_be_hr_payroll.cp200_other_input_warrant').id
    #             })]
    #             input_line_vals = to_remove_vals + to_add_vals
    #             slip.update({'input_line_ids': input_line_vals})

    def _compute_expense_input_line_ids(self):
        expense_type = self.env.ref('hr_payroll_expense.expense_other_input', raise_if_not_found=False)
        travel_expense_type = self.env.ref('sa_payroll.travel_expense_other_input', raise_if_not_found=False)

        local_expense_type = self.env.ref('sa_payroll.local_expense_other_input', raise_if_not_found=False)
        foreign_expense_type = self.env.ref('sa_payroll.foreign_expense_other_input', raise_if_not_found=False)
        for payslip in self:

            # travel reimburse
            travel_total = sum(payslip.expense_sheet_ids.filtered(lambda x: x.is_travel).mapped('total_amount'))
            if travel_total and travel_expense_type:
                travel_lines_to_remove = payslip.input_line_ids.filtered(lambda x: x.input_type_id == travel_expense_type)
                travel_input_lines_vals = [Command.delete(line.id) for line in travel_lines_to_remove]
                travel_input_lines_vals.append(Command.create({
                    'amount': travel_total,
                    'input_type_id': travel_expense_type.id
                }))
                payslip.update({'input_line_ids': input_lines_vals})

            # parent code
            total = sum(payslip.expense_sheet_ids.filtered(lambda x: not x.is_travel).mapped('total_amount'))
            if not total or not expense_type:
                continue
            lines_to_remove = payslip.input_line_ids.filtered(lambda x: x.input_type_id == expense_type)
            input_lines_vals = [Command.delete(line.id) for line in lines_to_remove]
            input_lines_vals.append(Command.create({
                'amount': total,
                'input_type_id': expense_type.id
            }))
            payslip.update({'input_line_ids': input_lines_vals})

    def calculate_week_pay(self):
        for payslip in self:
            week_pay = 0
            if payslip.line_ids:
                gross_salary = payslip.line_ids.filtered(lambda x: x.category_id.code == 'GROSS').amount
                week_salary = gross_salary/4

                payslip._compute_total_years_worked()

                if week_salary > 0:
                    # if worked less than year
                    if payslip.total_years_worked == -1:
                        week_pay = week_salary* 1
                    else:
                        week_pay = week_salary #* payslip.total_years_worked
            payslip.week_pay = abs(week_pay)

    @api.depends('date_to')
    def _compute_total_years_worked(self):
        for payslip in self:
            payslip.total_years_worked

            contract_history= self.env['hr.contract.history'].search([('id','=', payslip.employee_id.id)], limit=1)

            if contract_history:
                if contract_history.date_hired:
                    hire_date = contract_history.date_hired
                    today = fields.date.today()

                    # Convert date strings to datetime objects
                    date1 = datetime.strptime(str(payslip.date_to), "%Y-%m-%d")
                    date2 = datetime.strptime(str(hire_date), "%Y-%m-%d")

                    # Calculate the difference between the dates
                    date_difference = today - hire_date

                    # Calculate the difference in years, considering leap years
                    def calculate_age_difference(date1, date2):
                        years = date1.year - date2.year
                        # if (date2.month, date2.day) < (date1.month, date1.day):
                        #     years -= 1
                        return years

                    # # Calculate and print the difference in years
                    years_difference = calculate_age_difference(date1, date2)
                    payslip.total_years_worked = years_difference

    def activate_leave_pay_advance(self):
        for rec in self:
            all_leave_type = self.env['hr.leave.type'].search([])
            for l_type in all_leave_type:
                remaining_leaves = l_type.with_context(employee_id=rec.employee_id.id).virtual_remaining_leaves
                values = {
                    'leave_type_id': l_type.id,
                    'remaining_days': remaining_leaves
                }
                rec['leave_pay_type_ids'] = [(0, 0, values)]

            # add new rule and 
            rec.is_leave_pay = True

    def add_into_payslip(self):
        for rec in self:
            if rec.leave_pay_type_ids:
                if any(line.remaining_days > 0 for line in rec.leave_pay_type_ids):
                    basic = rec.line_ids.filtered(lambda x: x.category_id.code == 'BASIC')
                    if basic:
                        if len(basic) > 1:
                            raise UserError(_('Wrong configuration, 2 basic found'))

                        if basic.amount == 0:
                            raise UserError(_('Basic Amount is 0.'))


                        weekly = basic.amount/4.333
                        daily = weekly/5

                        total_amount = sum(l_line.remaining_days * (daily*l_line.factor) for l_line in rec.leave_pay_type_ids)

                        flag= False
                        if rec.input_line_ids:
                            leave_paid_out = rec.input_line_ids.filtered(lambda x: x.input_type_id.code == 'LEAVEPAY')
                            if leave_paid_out:
                                leave_paid_out.amount = total_amount
                                flag= False
                            else:
                                flag = True
                        else:
                            flag= True

                        if flag:
                            other_input = self.env['hr.payslip.input.type'].search([('code','=', 'LEAVEPAY')], limit=1)
                            if other_input:
                                rec.input_line_ids = [(0, 0, {'input_type_id': other_input.id, 'amount': total_amount})]
                            else:
                                raise UserError(_("No other input type with code 'LEAVEPAY' found."))
                    else:
                        raise UserError(_('No Basic found under salary computation.'))
                else:
                    raise UserError(_('No positive leaves to add.'))
            else:
                raise UserError(_('Nothing to add.'))

    def activate_leave_pay(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sa_payroll.action_leave_pay_wizard")
        return action

    def compute_sheet(self):
        self._compute_other_advance_input_line_ids()
        res = super(HrSlip, self).compute_sheet()
        self._compute_eti()
        self._sdl_calc()
        self.get_employee_commission_amount()
        return res

    def update_contract(self):
        if self.contract_id:
            month = self.date_from.month
            month_data = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September',
                      10: 'October', 11: 'November', 12: 'December'}
            
            salary_id = self.contract_id.month_by_month_salary_ids.filtered(lambda x: x.month == month_data[month])
            if salary_id:
                salary = self.line_ids.filtered(lambda x: x.code == '3603')
                if salary:
                    salary_id.wage = salary.total

    def _compute_eti(self):
        for rec in self:
            contract_id = rec.contract_id
            eti_amount = 0
            if contract_id.qualify_for_eti:
                if rec.line_ids:
                    gross_salary = rec.line_ids.filtered(lambda x: x.salary_rule_id.consider_for_eti_sdl)
                    if gross_salary:
                        if gross_salary.amount > 0:
                            if gross_salary.amount > 0 and gross_salary.amount <= 1999:
                                if contract_id.first_year:
                                    eti_amount = gross_salary.amount * 0.75
                                if contract_id.second_year:
                                    eti_amount = gross_salary.amount * 37.5/100

                            if gross_salary.amount >= 2000 and gross_salary.amount <= 4499:
                                if contract_id.first_year:
                                    eti_amount = 1500
                                if contract_id.second_year:
                                    eti_amount = 750

                            if gross_salary.amount >= 4500 and gross_salary.amount <= 6499:
                                if contract_id.first_year:
                                    eti_amount = 1000 - (0.75* (gross_salary.amount-4500))
                                if contract_id.second_year:
                                    eti_amount = 500 - (0.25*(gross_salary.amount-4500))
            rec.eti = eti_amount

    def _sdl_calc(self):
        for rec in self:
            contract_id = rec.contract_id
            eti_amount = 0
            sdl_rate = self.env['ir.config_parameter'].sudo().get_param('sa_payroll.sdl_rate')
            print ('sdl_rate===>>',sdl_rate)
            if sdl_rate:
                if rec.line_ids:
                    gross_salary = rec.line_ids.filtered(lambda x: x.salary_rule_id.consider_for_eti_sdl)
                    if gross_salary:
                        if gross_salary.amount > 0:
                            rec.sdl = gross_salary.amount * (int(sdl_rate)/100)

    # 201 report
    previous_net_wage = fields.Float(string="Net wage previous Month", compute="_compute_previous_net")
    variance = fields.Float(string="Variance", compute="_compute_previous_net")

    def _compute_previous_net(self):
        for rec in self:
            employee_id = (rec._origin).employee_id
            date_from = (rec._origin).date_from
            first = date_from.replace(day=1)
            prev_last = first - timedelta(days=1)
            prev_first = prev_last.replace(day=1)
            last_payslip = self.sudo().search([('date_from','>=',prev_first), ('date_to','<=',prev_last), ('state','in',['done','paid']),('employee_id','=',employee_id.id)], limit=1)
            rec.previous_net_wage = last_payslip.net_wage
            rec.variance = rec.net_wage - rec.previous_net_wage

    def compute_paye_remuneration(self):
        amt = 0.0
        for rec in self:
            if rec.line_ids:
                paye_salary = rec.line_ids.filtered(lambda x: x.salary_rule_id.is_gross_em_in_tx)
                if paye_salary:
                    amt = abs(paye_salary.amount)
        return amt

    def compute_leviable_amt(self):
        amt = 0.0
        for rec in self:
            if rec.line_ids:
                paye_salary = rec.line_ids.filtered(lambda x: x.salary_rule_id.is_gross)
                if paye_salary:
                    amt = abs(paye_salary.amount)
        return amt

    def compute_uif_remuneration(self):
        amt = 0.0
        for rec in self:
            if rec.line_ids:
                uif_data = rec.line_ids.filtered(lambda x: x.salary_rule_id.is_gross)
                if uif_data:
                    amt = abs(uif_data.amount)
        return amt

    def compute_uif_amt(self):
        amt = 0.0
        for rec in self:
            if rec.line_ids:
                #uif_data = rec.line_ids.filtered(lambda x: x.salary_rule_id.is_uif)
                uif_data = rec.line_ids.filtered(lambda x: x.code in ['3801(8)','4142'])
                if uif_data:
                    amt = abs(sum(l.total for l in uif_data))
        return amt

    def compute_paye_amt(self):
        amt = 0.0
        for rec in self:
            if rec.line_ids:
                uif_data = rec.line_ids.filtered(lambda x: x.salary_rule_id.is_pay)
                if uif_data:
                    amt = abs(uif_data.total)
        return amt
