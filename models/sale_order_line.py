# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # ====== Campos detectados en tus vistas exportadas ======

    # Cantidad contractual (en tu export aparecía como x_contractual_qty)
    x_contractual_qty = fields.Float(string="Cantidad contractual")

    # Familia (en conversaciones anteriores la usabas como related a categoría)
    x_familia = fields.Char(
        string="Familia",
        related="product_id.categ_id.name",
        store=True,
        readonly=True,
    )

    # Tags/Actividades (export: x_stock.move.tags + rel table)
    x_sale_line_tags = fields.Many2many(
        comodel_name="x_stock.move.tags",
        relation="x_sale_order_line_x_stock_move_tags_rel",
        column1="sale_order_line_id",
        column2="x_stock_move_tags_id",
        string="Actividades",
        copy=False,
    )

    # Campos Studio vistos en el tree
    x_studio_qty_stock_ptllno = fields.Float(
        string="Qty stock Ptllno",
        # normalmente related a un forecast en product/product.template; si ya existe en tu BD,
        # NO lo redefinas. Si no existe, deja este related como no-store para que no rompa.
        # Puedes ajustarlo cuando confirmes el campo real.
        help="Campo legado Studio. Ajustar related real si aplica.",
    )

    # Estados auxiliares que aparecen en searchpanel
    x_invoice = fields.Selection(
        [
            ("to_invoice", "A facturar"),
            ("invoiced", "Facturado"),
            ("no", "N/A"),
        ],
        string="Pendiente Facturación",
        compute="_compute_x_invoice",
        store=True,
        readonly=True,
    )

    x_pendiente = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("ok", "OK"),
        ],
        string="Pendiente Entrega",
        compute="_compute_x_pendiente",
        store=True,
        readonly=True,
    )

    @api.depends("qty_to_invoice", "qty_invoiced", "state")
    def _compute_x_invoice(self):
        # Nota: lógica sencilla y robusta. Si tienes reglas más finas, las movemos luego.
        for line in self:
            if line.state == "cancel":
                line.x_invoice = "no"
                continue
            if float_compare(line.qty_to_invoice or 0.0, 0.0, precision_digits=2) > 0:
                line.x_invoice = "to_invoice"
            elif float_compare(line.qty_invoiced or 0.0, 0.0, precision_digits=2) > 0:
                line.x_invoice = "invoiced"
            else:
                line.x_invoice = "no"

    @api.depends("qty_delivered", "product_uom_qty", "state")
    def _compute_x_pendiente(self):
        for line in self:
            if line.state == "cancel":
                line.x_pendiente = "ok"
                continue
            remaining = (line.product_uom_qty or 0.0) - (line.qty_delivered or 0.0)
            if float_compare(remaining, 0.0, precision_digits=2) > 0:
                line.x_pendiente = "pending"
            else:
                line.x_pendiente = "ok"
