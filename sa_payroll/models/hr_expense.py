# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models, _

class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    is_travel = fields.Boolean(
        string='Is Travel',
        copy=False,
        default=False
    )

    is_local_expense = fields.Boolean(
        string='Is Local Expense',
        copy=False,
        default=False
    )

    is_foreign_expense = fields.Boolean(
        string='Is Foreign Expense',
        copy=False,
        default=False
    )
