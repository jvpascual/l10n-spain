# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp
from odoo.tools import float_compare


class PosOrder(models.Model):
    _inherit = 'pos.order'

    is_l10n_es_simplified_invoice = fields.Boolean(
        'Simplified invoice',
        copy=False,
        default=False,
    )

    @api.model
    def _simplified_limit_check(self, amount_total, limit=3000):
        precision_digits = dp.get_precision('Account')(self.env.cr)[1]
        # -1 or 0: amount_total <= limit, simplified
        #       1: amount_total > limit, can not be simplified
        return float_compare(
            amount_total, limit, precision_digits=precision_digits) < 0

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder, self)._order_fields(ui_order)
        if ui_order.get('simplified_invoice', False):
            res.update({
                'pos_reference': ui_order['simplified_invoice'],
                'is_l10n_es_simplified_invoice': True,
            })
        return res

    @api.model
    def _process_order(self, pos_order):
        simplified_invoice_number = pos_order.get('simplified_invoice', False)
        if not simplified_invoice_number:
            return super(PosOrder, self)._process_order(pos_order)
        pos_order_obj = self.env['pos.order']
        pos = self.env['pos.session'].browse(
            pos_order.get('pos_session_id')).config_id
        if pos_order_obj._simplified_limit_check(
                pos_order.get('amount_total'),
                pos.l10n_es_simplified_invoice_limit):
            pos_order.update({
                'pos_reference': simplified_invoice_number,
                'is_l10n_es_simplified_invoice': True,
            })
            pos.l10n_es_simplified_invoice_sequence_id.next_by_id()
        return super(PosOrder, self)._process_order(pos_order)

    @api.model
    def create_from_ui(self, orders):
        """Provide a context with the current session id"""
        if not orders:
            return super().create_from_ui(orders)
        # We take the session from the first order in queue
        pos_session_id = orders and orders[0]['data']['pos_session_id']
        self_ctx = self.with_context(l10n_es_pos_session_id=pos_session_id)
        return super(PosOrder, self_ctx).create_from_ui(orders)

    @api.model
    def search(self, args, offset=0, limit=0, order=None, count=False):
        """If the context provided from create_from_ui() is given, we add
           the session to the domain filter. This way, we prevent missing
           orders if a sequence is reset. If they belong to another session
           we grant them for valid despite the duped sequence number"""
        pos_session_id = self.env.context.get('l10n_es_pos_session_id')
        if pos_session_id:
            args += [('session_id', '=', pos_session_id)]
        return super().search(args, offset=offset, limit=limit,
                              order=order, count=count)
