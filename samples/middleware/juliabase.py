#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of JuliaBase, see http://www.juliabase.org.
# Copyright © 2008–2015 Forschungszentrum Jülich GmbH, Jülich, Germany
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from __future__ import absolute_import, unicode_literals

from django.template import loader, RequestContext
from django.utils.translation import ugettext as _
import django.http
from django.shortcuts import render
from jb_common.utils.base import HttpResponseUnauthorized
import samples.utils.views as utils
from samples.permissions import PermissionError

"""Middleware for handling samples-database-specific exceptions.
"""


# FixMe: A JSON client should see JSON responses.

class ExceptionsMiddleware(object):
    """Middleware for catching JuliaBase-samples-specific exceptions raised by
    views.  I handle only `PermissionError` and `AmbiguityException` here.
    These exceptions mean a redirect in one way or another.

    It is important that this class comes after non-JuliaBase middleware in
    ``MIDDLEWARE_CLASSES`` in the ``settings`` module, otherwise the above
    mentioned exceptions may propagate to other middleware which treats them as
    real errors.
    """

    def process_exception(self, request, exception):
        if isinstance(exception, PermissionError):
            return HttpResponseUnauthorized(
                loader.render_to_string("samples/permission_error.html",
                                        {"title": _("Access denied"), "exception": exception}, request=request))
        elif isinstance(exception, utils.AmbiguityException):
            return render(request, "samples/disambiguation.html",
                          {"alias": exception.sample_name, "samples": exception.samples,
                           "title": _("Ambiguous sample name")})
