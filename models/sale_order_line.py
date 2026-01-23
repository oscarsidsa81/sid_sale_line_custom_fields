from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    contractual_qty = fields.Float(string="Cantidad contractual")

    sid_has_po_delay = fields.Boolean (
        string="Retraso en compra",
        store=True,
        index=True,
        readonly=False,
        # si quieres permitir override manual, si no: readonly=True
    )

    familia = fields.Char(
        string="Familia",
        related="product_id.categ_id.name",
        store=True,
        readonly=True,
    )

    # Madrid
    sid_qty_stock_mad = fields.Float(
        string="Stock pronosticado (Madrid)",
        compute="_compute_sid_qty_stock_mad",
        store=False,
        readonly=True,
        help="Cantidad pronosticada (virtual_available) en la ubicación de stock del almacén localizado por state_es_m.",
    )

    # Puertollano / Ciudad Real
    sid_qty_stock_ptllno = fields.Float(
        string="Stock pronosticado (Ptllno)",
        compute="_compute_sid_qty_stock_ptllno",
        store=False,
        readonly=True,
        help="Cantidad pronosticada (virtual_available) en la ubicación de stock del almacén localizado por state_es_cr.",
    )

    pending_invoice = fields.Selection(
        [
            ("to_invoice", "A facturar"),
            ("invoiced", "Facturado"),
            ("no", "N/A"),
        ],
        string="Pendiente Facturación",
        compute="_compute_pending_invoice",
        store=True,
        readonly=True,
    )

    pending_delivery = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("ok", "OK"),
        ],
        string="Pendiente Entrega",
        compute="_compute_pending_delivery",
        store=True,
        readonly=True,
    )

    # -------------------------
    # Helpers
    # -------------------------
    def _get_wh_stock_location_by_state_xmlid(self, state_xmlid):
        """Devuelve la lot_stock_id del primer warehouse cuya partner_id.state_id coincida con el state."""
        Warehouse = self.env["stock.warehouse"]
        state = self.env.ref(state_xmlid, raise_if_not_found=False)
        if not state:
            return False

        wh = Warehouse.search([("partner_id.state_id", "=", state.id)], limit=1)
        return wh.lot_stock_id if wh else False

    def _get_virtual_available_in_location(self, product, location):
        if not product or not location:
            return 0.0
        return product.with_context(location=location.id).virtual_available or 0.0

    # -------------------------
    # Computes stock
    # -------------------------
    @api.depends("product_id")
    def _compute_sid_qty_stock_mad(self):
        location = self._get_wh_stock_location_by_state_xmlid("base.state_es_m")
        for line in self:
            line.sid_qty_stock_mad = self._get_virtual_available_in_location(line.product_id, location)

    @api.depends("product_id")
    def _compute_sid_qty_stock_ptllno(self):
        location = self._get_wh_stock_location_by_state_xmlid("base.state_es_cr")
        for line in self:
            line.sid_qty_stock_ptllno = self._get_virtual_available_in_location(line.product_id, location)

    # -------------------------
    # Computes auxiliares
    # -------------------------
    @api.depends("qty_to_invoice", "qty_invoiced", "state")
    def _compute_pending_invoice(self):
        for line in self:
            if line.state == "cancel":
                line.pending_invoice = "no"
                continue
            if float_compare(line.qty_to_invoice or 0.0, 0.0, precision_digits=2) > 0:
                line.pending_invoice = "to_invoice"
            elif float_compare(line.qty_invoiced or 0.0, 0.0, precision_digits=2) > 0:
                line.pending_invoice = "invoiced"
            else:
                line.pending_invoice = "no"

    @api.depends("qty_delivered", "product_uom_qty", "state")
    def _compute_pending_delivery(self):
        for line in self:
            if line.state == "cancel":
                line.pending_delivery = "ok"
                continue
            remaining = (line.product_uom_qty or 0.0) - (line.qty_delivered or 0.0)
            line.pending_delivery = "pending" if float_compare(remaining, 0.0, precision_digits=2) > 0 else "ok"
