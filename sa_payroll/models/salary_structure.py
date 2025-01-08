# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    @api.model
    def _get_default_rule_ids(self):
        return []

    rule_ids = fields.One2many(
        'hr.salary.rule', 'struct_id', copy=True,
        string='Salary Rules', default=_get_default_rule_ids)

    can_leave_pay_apply = fields.Boolean(
        string='Can Leave Pay Apply ?',
    )

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'is_credit_time', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):
        for worked_days in self:
            if worked_days.payslip_id.edited or worked_days.payslip_id.state not in ['draft', 'verify']:
                continue
            if not worked_days.contract_id or worked_days.code == 'OUT' or worked_days.is_credit_time:
                worked_days.amount = 0
                continue
            if worked_days.payslip_id.wage_type == "hourly":
                worked_days.amount = worked_days.payslip_id.contract_id.hourly_wage * worked_days.number_of_hours if worked_days.is_paid else 0
            else:
                days = worked_days.number_of_days#worked_days['LEAVE90']['number_of_days']
                daily_rate = (worked_days.payslip_id.contract_id.monthly_cost_to_company/21.67)
                worked_days.amount = days * daily_rate if worked_days.is_paid else 0
