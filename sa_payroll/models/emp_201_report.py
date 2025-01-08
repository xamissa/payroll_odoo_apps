# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

from odoo.osv import expression
from datetime import date, timedelta, datetime

class EMP201Report(models.Model):
    _name = 'emp.201.report'
    _description = 'EMP201 Report'

    paye_remuneration = fields.Float(string="PAYE Remuneration")
    paye_amt = fields.Float(string="PAYE AMT")
    sdl_leviable_amt = fields.Float(string="SDL LEVIABLE AMT")
    sdl_amt_rsn = fields.Float(string="SDL AMT RSN")
    uif_remuneration = fields.Float(string="UIF Remuneration")
    uif_amt_rsn = fields.Float(string="UIF AMT RSN")
    eti_amt = fields.Float(string="ETI AMT")
    employee = fields.Many2one('hr.employee', string="Employee")
    comp_reg_no = fields.Char(string="Company Reg No.")
    emp_code = fields.Char(string="EMP Code")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")