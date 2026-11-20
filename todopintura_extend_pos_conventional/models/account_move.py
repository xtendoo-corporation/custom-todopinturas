# -*- coding: utf-8 -*-

from odoo import models
from odoo.exceptions import UserError

A4_INVOICE_REPORT = "todopintura_administration.report_factura_todopintura_document"


class AccountMove(models.Model):
    _inherit = "account.move"

    def _tp_get_a4_invoice_pdf(self):
        """PDF de la factura A4 generado una sola vez.

        Si la factura ya tiene su PDF oficial (``invoice_pdf_report_id``) y la
        plantilla por defecto de esa factura es la A4 de Todo Pintura, se
        devuelve ese adjunto sin volver a pasar por wkhtmltopdf. Si no lo tiene,
        se genera y, cuando la factura está publicada, se guarda como PDF
        oficial (igual que hace Odoo al enviar), para que las reimpresiones y el
        "Enviar e imprimir" posteriores no lo vuelvan a generar.
        """
        self.ensure_one()
        self.check_access("read")
        # Elegir plantilla y leer el adjunto oficial son operaciones internas:
        # el dominio de disponibilidad del informe lee campos (p. ej.
        # pos_order_ids) que un usuario sin grupo de TPV no puede leer.
        is_default_template = self._tp_a4_is_default_pdf_template()
        official_pdf = self.sudo().invoice_pdf_report_id
        if is_default_template and official_pdf:
            return official_pdf.raw

        # Igual que antes en el controlador: _get_report_from_name devuelve el
        # informe en sudo y se renderiza desde él.
        report = self.env["ir.actions.report"]._get_report_from_name(A4_INVOICE_REPORT)
        pdf, _fmt = report._render_qweb_pdf(A4_INVOICE_REPORT, [self.id])

        if (
            is_default_template
            and self.state == "posted"
            and self.is_sale_document()
            and pdf.startswith(b"%PDF")  # en modo test Odoo devuelve HTML
        ):
            self._tp_store_invoice_pdf(pdf)
        return pdf

    def _tp_a4_is_default_pdf_template(self):
        self.ensure_one()
        move = self.sudo()
        try:
            default_report = move.env["account.move.send"]._get_default_pdf_report_id(move)
        except UserError:
            return False
        return default_report.report_name == A4_INVOICE_REPORT

    def _tp_store_invoice_pdf(self, pdf):
        """Guarda ``pdf`` como PDF oficial de la factura (invoice_pdf_report_file),
        replicando account.move.send._link_invoice_documents."""
        self.ensure_one()
        move = self.sudo()
        move.invalidate_recordset(["invoice_pdf_report_id", "invoice_pdf_report_file"])
        if move.invoice_pdf_report_id:  # otra petición lo guardó mientras tanto
            return
        report = move.env["ir.actions.report"]._get_report_from_name(A4_INVOICE_REPORT)
        attachment = move.env["ir.attachment"].create({
            "name": move._get_invoice_report_filename(report=report),
            "raw": pdf,
            "mimetype": "application/pdf",
            "res_model": move._name,
            "res_id": move.id,
            "res_field": "invoice_pdf_report_file",
        })
        move.message_main_attachment_id = attachment
        move.invalidate_recordset(["invoice_pdf_report_id", "invoice_pdf_report_file"])
        move.is_move_sent = True
