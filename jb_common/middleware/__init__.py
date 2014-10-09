#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of JuliaBase, the samples database.
#
# Copyright (C) 2010 Forschungszentrum Jülich, Germany,
#                    Marvin Goblet <m.goblet@fz-juelich.de>,
#                    Torsten Bronger <t.bronger@fz-juelich.de>
#
# You must not use, install, pass on, offer, sell, analyse, modify, or
# distribute this software without explicit permission of the copyright holder.
# If you have received a copy of this software without the explicit permission
# of the copyright holder, you must destroy it immediately and completely.


from __future__ import absolute_import, unicode_literals

import locale, re, json, hashlib, random, time
from django.contrib.messages.storage import default_storage
from django.utils.cache import patch_vary_headers, add_never_cache_headers
from django.utils import translation
from django.template import loader, RequestContext
from django.contrib.auth import logout
import django.core.urlresolvers
from jb_common.models import UserDetails, ErrorPage
from jb_common.utils import is_json_requested, JSONRequestException
from django.conf import settings
from django.utils.translation import ugettext as _
import django.http
from django.shortcuts import render_to_response


"""Middleware classes for various totally unrelated things."""


class LocaleMiddleware(object):
    """This is a simple middleware that parses a request and decides what
    translation object to install in the current thread context depending on
    what's found in `models.UserDetails`. This allows pages to be dynamically
    translated to the language the user desires (if the language is available,
    of course).

    It must be after ``AuthenticationMiddleware`` in the list.
    """
    language_pattern = re.compile("[a-zA-Z0-9]+")

    @staticmethod
    def get_language_for_user(request):
        if request.user.is_authenticated():
            try:
                language = request.user.jb_user_details.language
                return language
            except UserDetails.DoesNotExist:
                pass
        return translation.get_language_from_request(request)

    def get_language_code_only(self, language):
        match = self.language_pattern.match(language)
        return match.group(0) if match else "en"

    def process_request(self, request):
        language = self.get_language_for_user(request)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
        # FixMe: Find a better way to map language codes to locales.  In
        # particular, sublanguages should be taken into account.
        new_locale = settings.LOCALES_DICT.get(self.get_language_code_only(language)) or (None, None)
        old_locale = locale.getlocale()
        # Changing the locale might be an expensive operation, so only if
        # necessary.
        if old_locale != new_locale:
            locale.setlocale(locale.LC_ALL, new_locale)

    def process_response(self, request, response):
        patch_vary_headers(response, ("Accept-Language",))
        response["Content-Language"] = translation.get_language()
        translation.deactivate()
        return response


class MessageMiddleware(object):
    """Middleware that handles temporary messages.  It is a copy of Django's
    original ``MessageMiddleware`` but it adds cache disabling.  This way,
    pages with messages are never cached by the browser, so that the messages
    don't get persistent.
    """
    def process_request(self, request):
        request._messages = default_storage(request)

    def process_response(self, request, response):
        """
        Updates the storage backend (i.e., saves the messages).

        If not all messages could not be stored and ``DEBUG`` is ``True``, a
        ``ValueError`` is raised.
        """
        # A higher middleware layer may return a request which does not contain
        # messages storage, so make no assumption that it will be there.
        if hasattr(request, '_messages'):
            unstored_messages = request._messages.update(response)
            if unstored_messages and settings.DEBUG:
                raise ValueError('Not all temporary messages could be stored.')
            if request._messages.used:
                del response["ETag"]
                del response["Last-Modified"]
                response["Expires"] = "Fri, 01 Jan 1990 00:00:00 GMT"
                # FixMe: One should check whether the following settings are
                # sensible.
                response["Pragma"] = "no-cache"
                response["Cache-Control"] = "no-cache, no-store, max-age=0, must-revalidate, private"
        return response


class ActiveUserMiddleware(object):
    """Middleware to prevent a non-active user from using the site.  Unfortunately,
    ``is_active=False`` only prevents a user from logging.  If he was already
    logged in before ``is_active`` was set to ``False`` and doesn't log out, he
    can use the site until the session is purged.  This middleware prevents
    this.

    Alternatively to this middleware, you can make sure that all the user's
    sessions are purged when he or she is set to inactive.

    This middleware must be after AuthenticationMiddleware in the list of
    installed middleware classes.
    """
    def process_request(self, request):
        if request.user.is_authenticated() and not request.user.is_active:
            logout(request)


class HttpResponseUnauthorised(django.http.HttpResponse):
    status_code = 401


class HttpResponseUnprocessableEntity(django.http.HttpResponse):
    status_code = 422


class JSONClientMiddleware(object):
    """Middleware to convert responses to JSON if this was requested by the
    client.

    It is important that this class comes after all non-JuliaBase middleware in
    ``MIDDLEWARE_CLASSES`` in the ``settings`` module, otherwise the
    ``Http404`` exception may be already caught.  FixMe: Is this really the
    case?
    """

    def process_response(self, request, response):
        """Return a HTTP 422 response if a JSON response was requested and an
        HTML page with form errors is returned.
        """
        if is_json_requested(request) and response._headers["content-type"][1].startswith("text/html") and \
                response.status_code == 200:
            user = request.user
            if not user.is_authenticated():
                # Login view was returned
                return HttpResponseUnauthorised()
            hash_ = hashlib.sha1()
            hash_.update(str(random.random()))
            # For some very obscure reason, a random number was not enough --
            # it led to collisions time after time.
            hash_.update(str(time.time()))
            hash_value = hash_.hexdigest()
            ErrorPage.objects.create(hash_value=hash_value, user=user, requested_url=request.get_full_path(),
                                     html=response.content)
            return HttpResponseUnprocessableEntity(
                json.dumps((1, django.core.urlresolvers.reverse("jb_common.views.show_error_page",
                                                                kwargs={"hash_value": hash_value}))),
                content_type="application/json; charset=ascii")
        return response


    def process_exception(self, request, exception):
        """Convert response to exceptions to JSONised version if the response
        is requested to be JSON.
        """
        if isinstance(exception, django.http.Http404):
            if is_json_requested(request):
                return django.http.HttpResponseNotFound(json.dumps((2, exception.args[0])),
                                                        content_type="application/json; charset=ascii")
        elif isinstance(exception, JSONRequestException):
            return HttpResponseUnprocessableEntity(json.dumps((exception.error_number, exception.error_message)),
                                                   content_type="application/json; charset=ascii")
