# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrContractAdvantage(models.Model):
    _name = "hr.contract.advantage"
    _description = "Employee's Advantages on Contract"

    contract_id = fields.Many2one("hr.contract")
    input_type_id = fields.Many2one(
        'hr.payslip.input.type',
        string='Input Type',
    )
    amount = fields.Float(string="Amount")
