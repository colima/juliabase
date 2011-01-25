#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Chantal, the samples database.
#
# Copyright (C) 2010 Forschungszentrum Jülich, Germany,
#                    Marvin Goblet <m.goblet@fz-juelich.de>,
#                    Torsten Bronger <t.bronger@fz-juelich.de>
#
# You must not use, install, pass on, offer, sell, analyse, modify, or
# distribute this software without explicit permission of the copyright holder.
# If you have received a copy of this software without the explicit permission
# of the copyright holder, you must destroy it immediately and completely.


u"""View for showing a plot as a PDF file.
"""

from __future__ import absolute_import

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from samples import models, permissions
from samples.views import utils
from chantal_common.utils import static_file_response


@login_required
def show_plot(request, process_id, number):
    u"""Shows a particular plot.  Although its response is a bitmap rather than
    an HTML file, it is served by Django in order to enforce user permissions.

    :Parameters:
      - `request`: the current HTTP Request object
      - `process_id`: the database ID of the process to show
      - `number`: the number of the image.  This is mostly ``0`` because most
        measurement models have only one graphics.

    :type request: ``HttpRequest``
    :type process_id: unicode
    :type number: unicode

    :Returns:
      the HTTP response object with the image

    :rtype: ``HttpResponse``
    """
    process = get_object_or_404(models.Process, pk=utils.convert_id_to_int(process_id))
    process = process.actual_instance
    permissions.assert_can_view_physical_process(request.user, process)
    number = int(number)
    plot_locations = process.calculate_plot_locations(number)
    return static_file_response(plot_locations["plot_file"], process.get_plotfile_basename(number) + ".pdf")


@login_required
def show_thumbnail(request, process_id, number):
    u"""Shows the thumbnail of a particular plot.  Although its response is a
    bitmap rather than an HTML file, it is served by Django in order to enforce
    user permissions.

    :Parameters:
      - `request`: the current HTTP Request object
      - `process_id`: the database ID of the process to show
      - `number`: the number of the image.  This is mostly ``0`` because most
        measurement models have only one graphics.

    :type request: ``HttpRequest``
    :type process_id: unicode
    :type number: unicode

    :Returns:
      the HTTP response object with the thumbnail image

    :rtype: ``HttpResponse``
    """
    process = get_object_or_404(models.Process, pk=utils.convert_id_to_int(process_id))
    process = process.actual_instance
    permissions.assert_can_view_physical_process(request.user, process)
    number = int(number)
    plot_locations = process.calculate_plot_locations(number)
    return static_file_response(plot_locations["thumbnail_file"])


