# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, http
from odoo.http import request, content_disposition


class Http(models.AbstractModel):
    _inherit = 'ir.http'
    # access - control - allow - origin
    def _binary_set_headers(self, status, content, filename, mimetype, unique, filehash=None, download=False):
        """
        Change default functionality of response headers that method binary_content uses
            set "default-src'  to  'unsafe-inline'"
        """
        headers = [('Content-Type', mimetype), ('X-Content-Type-Options', 'nosniff'),
                   ('access-control-allow-origin', "*")]
        etag = bool(request) and request.httprequest.headers.get('If-None-Match')
        status = status or 200
        if filehash:
            headers.append(('ETag', filehash))
            if etag == filehash and status == 200:
                status = 304
        headers.append(('Cache-Control', 'max-age=%s' % (http.STATIC_CACHE_LONG if unique else 0)))
        if download:
            headers.append(('Content-Disposition', content_disposition(filename)))

        return status, headers, content

    def binary_content(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       unique=False, filename=None, filename_field='name', download=False,
                       mimetype=None, default_mimetype='application/octet-stream',
                       access_token=None):
        """ Get file, attachment or downloadable content

        If the ``xmlid`` and ``id`` parameter is omitted, fetches the default value for the
        binary field (via ``default_get``), otherwise fetches the field for
        that precise record.

        :param str xmlid: xmlid of the record
        :param str model: name of the model to fetch the binary from
        :param int id: id of the record from which to fetch the binary
        :param str field: binary field
        :param bool unique: add a max-age for the cache control
        :param str filename: choose a filename
        :param str filename_field: if not create an filename with model-id-field
        :param bool download: apply headers to download the file
        :param str mimetype: mintype of the field (for headers)
        :param str default_mimetype: default mintype if no mintype found
        :param str access_token: optional token for unauthenticated access
                                 only available  for ir.attachment
        :returns: (status, headers, content)
        """
        record, status = self._get_record_and_check(xmlid=xmlid, model=model, id=id, field=field,
                                                    access_token=access_token)
        if not record:
            return (status or 404, [], None)

        content, headers, status = None, [], None

        if record._name == 'ir.attachment':
            status, content, default_filename, mimetype, filehash = self._binary_ir_attachment_redirect_content(record,
                                                                                                                default_mimetype=default_mimetype)
            filename = filename or default_filename or record.name
        if not content:
            status, content, filename, mimetype, filehash = self._binary_record_content(
                record, field=field, filename=filename, filename_field=filename_field,
                default_mimetype='application/octet-stream')

        status, headers, content = self._binary_set_headers(
            status, content, filename, mimetype, unique, filehash=filehash, download=download)

        return status, headers, content
