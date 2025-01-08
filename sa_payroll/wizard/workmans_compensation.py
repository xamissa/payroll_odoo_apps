from odoo import models, api, fields, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

class WorkmansCompensation(models.TransientModel):
    _name = 'workmans.compensation.wizard'
    _description = 'workmans compensation'

    start_date = fields.Date(string='Start Date', default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    end_date = fields.Date(string='End Date', default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))

    def generate_report(self):
        payslip_ids = self.env['hr.payslip'].search([('date_from','>=',self.start_date), ('date_to','<=',self.end_date), ('state','in',['done','paid'])])
        if not payslip_ids:
            raise UserError(_("There is no data for this period!"))
        data = {'payslip_ids': payslip_ids.ids,}
        return self.env.ref('sa_payroll.report_workmans_compensation').report_action(self,data=data)

class SaEMPReport(models.AbstractModel):
    _name = 'report.workmans_compensation.report_workmans_comp'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Workmans Compensation'

    def get_total_employees_up(self, payslip_ids):
        total_yearly_wage_up = 0.0
        total_yearly_wage_above = 0.0
        count_emp_up = []
        count_emp_above = []
        total_emp = 0.0
        up_to_amount = self.env['ir.config_parameter'].sudo().get_param('sa_payroll.up_to_amount')
        for rec in payslip_ids.filtered(lambda x: x.employee_id and x.employee_id.department_id.is_director == False):
            line_id = rec.line_ids.filtered(lambda x: x.salary_rule_id.is_net_salary == True)
            if line_id.amount <= float(up_to_amount):
                total_yearly_wage_up += line_id.amount
                if rec.employee_id.id not in count_emp_up:
                    count_emp_up.append(rec.employee_id.id)
            else:
                total_yearly_wage_above += line_id.amount
                if rec.employee_id.id not in count_emp_above:
                    count_emp_above.append(rec.employee_id.id)
            total_emp += line_id.amount
        return {'total_yearly_wage_up' : total_yearly_wage_up, 'count_emp_up' : len(count_emp_up), 'total_yearly_wage_above' : total_yearly_wage_above, 'count_emp_above' : len(count_emp_above), 'total_emp' : total_emp}

    def get_total_director_up(self, payslip_ids):
        total_yearly_wage_up = 0.0
        total_yearly_wage_above = 0.0
        count_director_up = []
        count_director_above = []
        total_director = 0.0
        up_to_amount = self.env['ir.config_parameter'].sudo().get_param('sa_payroll.up_to_amount')
        for rec in payslip_ids.filtered(lambda x: x.employee_id and x.employee_id.department_id.is_director):
            line_id = rec.line_ids.filtered(lambda x: x.salary_rule_id.is_net_salary == True)
            if line_id.amount <= float(up_to_amount):
                total_yearly_wage_up += line_id.amount
                if rec.employee_id.id not in count_director_up:
                    count_director_up.append(rec.employee_id.id)
            else:
                total_yearly_wage_above += line_id.amount
                if rec.employee_id.id not in count_director_above:
                    count_director_above.append(rec.employee_id.id)
            total_director += line_id.amount

        return {'total_yearly_wage_up' : total_yearly_wage_up, 'count_director_up' : len(count_director_up), 'total_yearly_wage_above' : total_yearly_wage_above, 'count_director_above' : len(count_director_above), 'total_director' : total_director}

    def get_total_employees(self, ):
        return 

    def generate_xlsx_report(self, workbook, data, partners):
        payslip_ids = self.env['hr.payslip'].browse(data.get('payslip_ids'))
        year_total_wage = sum(payslip_ids.mapped('contract_id').mapped('total_yearly_wage'))
        up_to_amount = self.env['ir.config_parameter'].sudo().get_param('sa_payroll.up_to_amount')
        frist_row = "{} {} {}".format('Up To', up_to_amount, 'p.a')
        second_row = "{} {} {}".format('Above To', up_to_amount, 'p.a')
        sheet = workbook.add_worksheet('Workmans Compensation')
        sheet.set_column(0, 0, 30)
        sheet.set_column(1, 1, 20)
        sheet.set_column(2, 2, 20)
        sheet.set_column(3, 3, 30)
        sheet.set_column(4, 4, 20)
        sheet.set_column(5, 5, 20)
        sheet.set_column(6, 6, 20)
        format_1 = workbook.add_format({'italic': True, 'bold' : True, 'bg_color' : '#e3e0e0', 'font_color':'green'})
        format_2 = workbook.add_format({'italic': True, 'bold' : True, 'bg_color' : '#e3e0e0', 'font_color':'green'})
        format_3 = workbook.add_format({'bg_color' : 'white', 'font_color':'black'})
        format_2.set_align('center')
        format_3.set_border(None)
        sheet.write(1, 0, frist_row, format_1)
        sheet.write(1, 1, 'Average Number', format_2)
        sheet.write(1, 2, 'Amount', format_2)
        sheet.write(1, 3, second_row, format_1)
        sheet.write(1, 4, 'Average Number', format_2)
        sheet.write(1, 5, 'Amount', format_2)
        sheet.write(1, 6, 'Total', format_2)

        total_director_data = self.get_total_director_up(payslip_ids)
        total_emp_data = self.get_total_employees_up(payslip_ids)

        total_emp_up = total_emp_data.get('count_emp_up')
        total_director_up = total_director_data.get('count_director_up')
        total_emp_up_count = total_emp_up + total_director_up

        total_emp_wage_up = total_emp_data.get('total_yearly_wage_up')
        total_director_wage_up = total_director_data.get('total_yearly_wage_up')
        total_emp_wage = total_emp_wage_up + total_director_wage_up

        count_total_emp_above = total_emp_data.get('count_emp_above')
        count_total_director_above = total_director_data.get('count_director_above')
        total_total_emp_above_count = count_total_emp_above + count_total_director_above

        total_emp_wage_above = total_emp_data.get('total_yearly_wage_above')
        total_director_wage_above = total_director_data.get('total_yearly_wage_above')
        total_emp_above = total_emp_wage_above + total_director_wage_above

        last_total = total_emp_data.get('total_emp') + total_director_data.get('total_director')

        # Total Directors
        sheet.write(2, 0, 'Directors',format_3)
        sheet.write(2, 1, total_director_data.get('count_director_up'), format_3)
        sheet.write(2, 2, total_director_data.get('total_yearly_wage_up'), format_3)
        sheet.write(2, 3, 'Directors', format_3)
        sheet.write(2, 4, total_director_data.get('count_director_above'), format_3)
        sheet.write(2, 5, total_director_data.get('total_yearly_wage_above'), format_3)
        sheet.write(2, 6, total_director_data.get('total_director'), format_3)
        # Normal Employees
        sheet.write(3, 0, 'Normal Employees',format_3)
        sheet.write(3, 1, total_emp_data.get('count_emp_up'), format_3)
        sheet.write(3, 2, total_emp_data.get('total_yearly_wage_up'), format_3)
        sheet.write(3, 3, 'Normal Employees', format_3)
        sheet.write(3, 4, total_emp_data.get('count_emp_above'), format_3)
        sheet.write(3, 5, total_emp_data.get('total_yearly_wage_above'), format_3)
        sheet.write(3, 6, total_emp_data.get('total_emp'), format_3)

        sheet.write(4, 0, 'Total Employees',format_3)
        sheet.write(4, 1, total_emp_up_count, format_3)
        sheet.write(4, 2, total_emp_wage, format_3)
        sheet.write(4, 3, 'Total Employees', format_3)
        sheet.write(4, 4, total_total_emp_above_count, format_3)
        sheet.write(4, 5, total_emp_above, format_3)
        sheet.write(4, 6, last_total, format_3)

        sheet.write(5, 0, 'W As 8 From Info', format_1)
        sheet.write(5, 1, '', format_1)
        sheet.write(5, 2, '', format_1)
        sheet.write(5, 3, '', format_1)
        sheet.write(5, 4, '', format_1)
        sheet.write(5, 5, '', format_1)
        sheet.write(5, 6, '', format_1)


