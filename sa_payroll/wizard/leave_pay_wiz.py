from odoo import models, api, fields, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError

class LeavePayWiz(models.TransientModel):
    _name = 'leave.pay.wiz'
    _description = 'Leave Pay Wizard'


    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
    )

    # struct_id = fields.Many2one(
    #     'hr.payroll.structure',
    #     string='Structure',
    # )

    rules_to_exclude_ids = fields.Many2many(
        'hr.salary.rule',
        string='Exclude Salary Rules',
    )

    leave_ids = fields.Many2many(
        'hr.leave',
        string='Leaves',
    )

    no_of_weeks = fields.Integer(
        string='# of Weeks',
    )

    @api.onchange('no_of_weeks')
    def _onchange_no_of_weeks(self):
        weeks = self.no_of_weeks
        days = weeks*7
        date_to = self.payslip_id.date_to + relativedelta(day=days)
        leave_ids = self.env['hr.leave'].search([('employee_id','=',self.payslip_id.employee_id.id), 
                                         ('request_date_from','>=',self.payslip_id.date_from),
                                         ('request_date_to','<=', date_to)])
        self.leave_ids = [(6, 0, leave_ids.ids)]

    @api.model
    def default_get(self, fields):
        res = super(LeavePayWiz, self).default_get(fields)
        res_id = self._context.get('active_id')
        if res_id:
            payslip = self.env['hr.payslip'].browse(res_id)

            rule_ids = payslip.line_ids.mapped('salary_rule_id').filtered(lambda x: x.exclude_for_leave_pay)

            leave_ids = self.env['hr.leave'].search([('employee_id','=',payslip.employee_id.id), 
                                         ('request_date_from','>=',payslip.date_from),
                                         ('request_date_to','<=', payslip.date_to)])
            res.update({
                'employee_id': payslip.employee_id.id,
                'rules_to_exclude_ids': [(6, 0, rule_ids.ids)],
                'leave_ids': [(6, 0, leave_ids.ids)],
                'payslip_id': payslip.id,
                })
        return res

    def apply_leave_pay(self):
        # update pay_for_weeks, leave_pay_calculated_till
        # update field on employee
        weeks = self.no_of_weeks
        days = weeks*7
        exclude_ids = self.rules_to_exclude_ids.ids
        rest_lines = self.payslip_id.line_ids.filtered(lambda x: x.salary_rule_id.id not in exclude_ids)
        for line in rest_lines:
            line.amount = line.amount*weeks

        self.payslip_id.write({'leave_pay_for_weeks': weeks,
                               'leave_pay_calculated_till': self.payslip_id.date_to + relativedelta(day=days),
                               'is_leave_pay': True,
                               })

    # field on employee to hold the payslip till (on cancel reset the date)
    # on wizard we can see the leaves added by employee
    # on wizard we can add the weeks he is on leave
    # # of weeks * deductions
