from odoo import models, fields, api, _

class ResSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    late_pay = fields.Boolean(
        string='Late Pay',
    )
    sdl_rate = fields.Integer(
        string='SDL Rate',
    )
    paye_ref_number = fields.Char(related="company_id.paye_ref_number",string='PAYE reference number', readonly=False)
    sdl_ref_number = fields.Char(related="company_id.sdl_ref_number",string='SDL reference number', readonly=False)
    uif_ref_number = fields.Char(related="company_id.uif_ref_number",string='UIF reference number', readonly=False)

    up_to_amount = fields.Float(string='Up To Amount')


    def set_values(self):
        res = super(ResSettings,self).set_values()
        set_value = self.env['ir.config_parameter'].sudo()
        set_value.set_param('sa_payroll.late_pay',self.late_pay)
        set_value.set_param('sa_payroll.sdl_rate',self.sdl_rate)

        set_value.set_param('sa_payroll.paye_ref_number',self.paye_ref_number)
        set_value.set_param('sa_payroll.sdl_ref_number',self.sdl_ref_number)
        set_value.set_param('sa_payroll.uif_ref_number',self.uif_ref_number)
        set_value.set_param('sa_payroll.up_to_amount',self.up_to_amount)
        return res

    @api.model
    def get_values(self):
        res = super(ResSettings,self).get_values()
        set_value = self.env['ir.config_parameter'].sudo()
        late_pay = set_value.get_param('sa_payroll.late_pay')
        res.update(
            late_pay = late_pay,
        )

        sdl_rate = set_value.get_param('sa_payroll.sdl_rate')
        res.update(
            sdl_rate = sdl_rate,
        )

        paye_ref_number = set_value.get_param('sa_payroll.paye_ref_number')
        sdl_ref_number = set_value.get_param('sa_payroll.sdl_ref_number')
        uif_ref_number = set_value.get_param('sa_payroll.uif_ref_number')
        res.update(paye_ref_number = paye_ref_number, sdl_ref_number = sdl_ref_number, uif_ref_number = uif_ref_number)

        up_to_amount = set_value.get_param('sa_payroll.up_to_amount')
        res.update(up_to_amount = up_to_amount)
        return res

