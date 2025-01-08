# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _

class LeavePayCalc(models.Model):
    _name = 'payslip.leave.pay'
    _description = 'Payslip Leave Pay'

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
    )
    leave_type_id = fields.Many2one(
        'hr.leave.type',
        string='Leave Type',
    )
    remaining_days = fields.Float(
        string='Remaining Days',
    )

    factor = fields.Float(
        string='Factor',
        default=1
    )
