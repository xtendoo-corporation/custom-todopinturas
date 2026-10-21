import io
import re
from urllib.parse import quote

from pypdf import PdfReader, PdfWriter

from odoo import http
from odoo.http import request

A4_INVOICE_REPORT = "todopintura_administration.report_factura_todopintura_document"
ALBARAN_REPORT = "todopintura_administration.report_albaran_todopintura_document"


class TodopinturaExtendPosConventionalController(http.Controller):
    @http.route('/todopintura_extend_pos_conventional/user_permissions', type='json', auth='user', methods=['POST'])
    def user_permissions(self):
        user = http.request.env.user
        return {
            'pos_can_edit_price': bool(getattr(user, 'pos_can_edit_price', False)),
        }

    @http.route(
        '/todopintura_extend_pos_conventional/invoice_a4/<int:move_id>',
        type='http',
        auth='user',
        methods=['GET'],
    )
    def invoice_a4_pdf(self, move_id, **kwargs):
        """Factura A4 en PDF (wkhtmltopdf) para imprimir desde el TPV.

        A diferencia de /report/html, el PDF respeta los margenes, la cabecera y
        el pie fijos de la plantilla, y se sirve con un nombre de archivo legible.
        """
        move = request.env['account.move'].browse(move_id).exists()
        if not move:
            return request.not_found()
        move.check_access('read')
        report = request.env['ir.actions.report']._get_report_from_name(A4_INVOICE_REPORT)
        pdf, _fmt = report._render_qweb_pdf(A4_INVOICE_REPORT, [move.id])
        label = move.name if move.name and move.name != '/' else 'borrador'
        filename = re.sub(r'[\\/:*?"<>|]+', '-', 'Factura %s' % label).strip() + '.pdf'
        pdf = self._set_pdf_title(pdf, filename[:-len('.pdf')])
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', "inline; filename*=UTF-8''%s" % quote(filename)),
        ]
        return request.make_response(pdf, headers=headers)

    @http.route(
        '/todopintura_extend_pos_conventional/albaran_pdf/<string:picking_ids>',
        type='http',
        auth='user',
        methods=['GET'],
    )
    def albaran_pdf(self, picking_ids, **kwargs):
        """Albarán Todo Pintura en PDF para imprimir desde el TPV."""
        try:
            ids = [int(i) for i in picking_ids.split(',') if i]
        except ValueError:
            return request.not_found()
        pickings = request.env['stock.picking'].browse(ids).exists()
        if not pickings:
            return request.not_found()
        pickings.check_access('read')
        report = request.env['ir.actions.report']._get_report_from_name(ALBARAN_REPORT)
        pdf, _fmt = report._render_qweb_pdf(ALBARAN_REPORT, pickings.ids)
        title = 'Albaran %s' % ', '.join(pickings.mapped('name'))
        filename = re.sub(r'[\\/:*?"<>|]+', '-', title).strip() + '.pdf'
        pdf = self._set_pdf_title(pdf, filename[:-len('.pdf')])
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', "inline; filename*=UTF-8''%s" % quote(filename)),
        ]
        return request.make_response(pdf, headers=headers)

    @staticmethod
    def _set_pdf_title(pdf, title):
        """El visor de Chrome usa el titulo interno del PDF como nombre al
        imprimir/guardar; sin el, el archivo acababa llamandose "_.pdf"."""
        if not pdf.startswith(b'%PDF'):  # en modo test Odoo devuelve HTML
            return pdf
        writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
        writer.add_metadata({'/Title': title})
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
