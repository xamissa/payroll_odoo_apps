from odoo import models, api, fields, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError

class SaEmp(models.TransientModel):
    _name = 'sa.emp.wizard'
    _description = 'SA Employee Report Wizard'

    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    start_date = fields.Date(string='Start Date', default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    end_date = fields.Date(string='End Date', default=lambda self: fields.Date.to_string((datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))

    def generate_report(self):
        payslip_ids = self.env.context.get('payslip_ids')
        data = {'payroll_ids': payslip_ids}
        return self.env.ref('sa_payroll.action_report_sa_emp').report_action([],data=data)

    def summary_report(self):
        payslip_ids = self.env.context.get('payslip_ids')
        start_date = self.env.context.get('start_date')
        end_date = self.env.context.get('end_date')
        data = {'payroll_ids': payslip_ids, 'start_date': start_date, 'end_date': end_date}
        return self.env.ref('sa_payroll.action_report_summary_emp').report_action([],data=data)

    def generate_report_odoo(self):
        #payslip_ids = self.env['hr.payslip'].search([('date_from','>=',self.start_date), ('date_to','<=',self.end_date), ('state','=','done')])
        if self.employee_id:
            payslip_id_start = self.env['hr.payslip'].search([('date_from','>=',self.start_date), ('employee_id', '=', self.employee_id.id), ('state','in',['done','paid'])])
            payslip_ids = payslip_id_start.filtered(lambda x: x.date_to <= self.end_date)
        else :
            payslip_id_start = self.env['hr.payslip'].search([('date_from','>=',self.start_date), ('state','in',['done','paid'])])
            payslip_ids = payslip_id_start.filtered(lambda x: x.date_to <= self.end_date)
        self._cr.execute('delete from emp_201_report')
        if payslip_ids:
            query = """
                        INSERT INTO emp_201_report (employee, emp_code, comp_reg_no, paye_remuneration, paye_amt, sdl_leviable_amt, sdl_amt_rsn, uif_remuneration, uif_amt_rsn, 
                            eti_amt, start_date, end_date)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ;

                        """ * len(payslip_ids)
            params = []
            for payroll in payslip_ids:
                params += [payroll.employee_id.id, payroll.employee_id.emp_code, payroll.company_id.company_registry, payroll.compute_paye_remuneration(), payroll.compute_paye_amt(),
                    payroll.compute_leviable_amt(), payroll.sdl, payroll.compute_uif_remuneration(), payroll.compute_uif_amt(), payroll.eti, payroll.date_from, payroll.date_to]
            self._cr.execute(query, params)
        return {
            'name': "EMP201 Report: "+ self.start_date.strftime("%m/%d/%Y") +"-"+ self.end_date.strftime("%m/%d/%Y"),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'res_model': 'emp.201.report',
            'view_id': self.env.ref('sa_payroll.emp_201_report_tree_view').id,
            'context': {'payslip_ids': payslip_ids, 'start_date': self.start_date, 'end_date': self.end_date},
            'target': 'current',
            }


class SaEMPReport(models.AbstractModel):
    _name = 'report.sa_payroll.report_sa_emp'
    _description = 'Employee Detailed Report'

    @api.model
    def get_payroll_details(self, payroll_ids=False):
        for payroll in payroll_ids:
            return {
                'company_name': payroll.company_id.name,
                'date_to': payroll.date_to,
                'comp_reg': payroll.company_id.company_registry,
                'sdl_amt': payroll.sdl,
                'eti_amt': payroll.eti,
                'paye_amt': payroll.net_wage,
                'paye_remuneration': 0.0,
                'leviable_amt': 0.0,
                'uif_remuneration': 0.0,
                'uif_amt': 0.0,

            }

    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        payroll = self.env['hr.payslip'].sudo().browse(data['payroll_ids'])
        #payroll = self.env['hr.payslip'].sudo().search([('employee_id', '=', data['employee_id']), ('date_from', '=', data['start_date'])])
        data.update(self.get_payroll_details(payroll))

        return {
            'doc_ids' : payroll.ids,
            'doc_model' : 'hr.payslip',
            'data' : data,
            'docs' : payroll,
        }


class SaEMPSummary(models.AbstractModel):
    _name = 'report.sa_payroll.report_emp_summary'
    _description = 'Employee Summary Report'

    @api.model
    def get_payroll_summary(self, payroll_ids=False):
        total_payee_amt=0.0
        total_sdl_amt= 0.0
        total_uif_amt= 0.0
        total_eti_amt = 0.0
        for payroll in payroll_ids:
            #total_sdl_amt += abs(payroll.sdl)
            sdl_data = payroll.line_ids.filtered(lambda x: x.code in ['4142(1)'])
            if sdl_data:
                total_sdl_amt += abs(sum(l.total for l in sdl_data))
            if payroll.line_ids:
                uif_data = payroll.line_ids.filtered(lambda x: x.code in ['3801(8)','4142'])
                if uif_data:
                    total_uif_amt += abs(sum(l.total for l in uif_data))
                paye_data = payroll.line_ids.filtered(lambda x: x.salary_rule_id.is_pay)
                if paye_data:
                    total_payee_amt += abs(paye_data.total)
                if payroll.eti:
                    total_eti_amt += abs(payroll.eti)

        return {
                'company_name': self.env.company.name,
                'date_to': False,
                'paye_ref_number': self.env.company.paye_ref_number,
                'sdl_ref_number': self.env.company.sdl_ref_number,
                'uif_ref_number': self.env.company.uif_ref_number,
                'paye_amt': total_payee_amt,
                'sdl_amt_rsn': total_sdl_amt,
                'uif_amt_rsn': total_uif_amt,
                'eti_amt_total': total_eti_amt,
                'total_payroll_liability': total_payee_amt+total_sdl_amt+total_uif_amt,
            }

    def number_eti_employee(self, payslip_ids):
        total_eti_emp = 0
        emp_list = []
        #payslip_ids = self.env['hr.payslip'].search([('state', '=', 'done')])
        for rec in payslip_ids:
            if rec.line_ids:
                eti_cnt = rec.line_ids.filtered(lambda x: x.salary_rule_id.consider_for_eti_sdl)
                if eti_cnt and rec.employee_id.id not in emp_list and rec.eti != 0 :
                    emp_list.append(rec.employee_id.id)
        total_eti_emp = len(emp_list)
        return total_eti_emp

    def get_total_intensive(self, payslip_ids):
        total_intesive_value = 0
        #payslip_ids = self.env['hr.payslip'].search([('state', '=', 'done')])
        for rec in payslip_ids:
            total_intesive_value += rec.eti
        return total_intesive_value

    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        payroll = self.env['hr.payslip'].search([('date_from','>=',data['start_date']), ('date_to','<=',data['end_date']), ('state','in',['done','paid'])])
        #payroll = self.env['hr.payslip'].sudo().search([('employee_id', '=', data['employee_id']), ('date_from', '=', data['start_date'])])
        data.update(self.get_payroll_summary(payroll))
        data['date_to'] = datetime.strptime(data['end_date'], "%Y-%m-%d") #data['end_date']
        data['number_eti_employee'] = self.number_eti_employee(payroll)
        data['total_intensive'] = self.get_total_intensive(payroll)
        return {
            'doc_ids' : payroll.ids,
            'doc_model' : 'hr.payslip',
            'data' : data,
            'docs' : payroll,
        }