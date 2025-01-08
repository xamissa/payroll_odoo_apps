# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

from odoo.osv import expression

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    consider_for_eti_sdl = fields.Boolean(
        string='Consider for ETI and SDL',
    )

    exclude_for_leave_pay = fields.Boolean(
        string='Exclude for Leave Pay',
        default=False
    )