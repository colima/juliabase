#!/usr/bin/env python
# -*- coding: utf-8 -*-

u"""General helper functions for connecting to RefDB.
"""

from __future__ import absolute_import

import hashlib
import pyrefdb
from django.conf import settings
from django.utils.translation import ugettext as _


def get_password(user):
    u"""Retrieves the RefDB password for a user.  For connection to RefDB, both
    username and password are computed from the Django user ID.  In this
    routine, I calculate the password, which is a shortened, salted SHA-1 hash
    of the user ID.

    :Parameters:
      - `user`: the user whose RefDB password should be retrieved

    :type user: ``django.contrib.auth.models.User``

    :Return:
      the RefDB password

    :rtype: str
    """
    user_hash = hashlib.sha1()
    user_hash.update(settings.SECRET_KEY)
    user_hash.update(str(user.id))
    return user_hash.hexdigest()[:10]


def get_username(user_id):
    u"""Retrieves the RefDB username for a user.  For connection to RefDB, both
    username and password are computed from the Django user ID.  In this
    routine, I calculate the username, which is the user ID with a constant
    prefix, namely `settings.REFDB_USERNAME_PREFIX`.

    :Parameters:
      - `user_id`: the Django user ID of the user

    :type user_id: int

    :Return:
      the RefDB username of the current user

    :rtype: str
    """
    # FixMe: For the sake of consistence, a full user object should be passed,
    # although only the ID is used.
    return settings.REFDB_USERNAME_PREFIX + str(user_id)


def get_connection(user):
    u"""Returns a RefDB connection object for the user, or returns a RefDB root
    connection.

    :Parameters:
      - `user`: the user whose RefDB password should be retrieved; if
        ``"root"`` is given instead, a connection with RefDB admin account is
        returned

    :type user: ``django.contrib.auth.models.User`` or str

    :Return:
      the RefDB connection object

    :rtype: ``pyrefdb.Connection``
    """
    if user == "root":
        return pyrefdb.Connection(settings.REFDB_USER, settings.REFDB_PASSWORD)
    else:
#         print get_username(user.id), get_password(user)
        return pyrefdb.Connection(get_username(user.id), get_password(user))


def get_lists(user, citation_key=None):
    u"""Retrieves the personal reference lists for a user.  Additionally, if
    ``citation_key`` is given, return a list of all personal reference lists in
    which this reference occurs.

    :Parameters:
      - `user`: the user whose personal reference lists should be retrieved
      - `citation_key`: citation key of a reference whose membership in the
        personal reference lists should be returned

    :type user: ``django.contrib.auth.models.User`` or str

    :Return:
      The personal reference lists of the user as a list of tupes (short name,
      verbose name), and a list of all reference lists (by their short names)
      in which the given reference occurs.  The latter is an empty list of no
      citation key was given.  The first list is ready-to-use as a ``choices``
      parameter in a choice form field.

    :rtype: list of (str, unicode), list of str
    """
    username = get_username(user.id)
    extended_notes = get_connection(user).get_extended_notes(":NCK:~^%s-" % username)
    choices = [(username, _(u"main list"))]
    initial = []
    for note in extended_notes:
        short_name = note.citation_key.partition("-")[2]
        if short_name:
            verbose_name = (note.content.text if note.content is not None else None) or short_name
            if short_name != username:
                choices.append((short_name, verbose_name))
            if citation_key:
                # FixMe: The following code works only if there are only
                # citation keys in the "target" attributes of the XNote
                # dataset, and not IDs.
                #
                # Maybe this is always the case anyway.  See
                # <https://sourceforge.net/tracker/?func=detail&aid=2872544&group_id=26091&atid=385991>.
                for link in note.links:
                    if link[0] == "reference" and link[1] == citation_key:
                        initial.append(short_name)
                        break
    return choices, initial


def get_shelves():
    u"""Returns all shelves available in the current database.  The result can
    be used directly for a choice field in a form.

    :Return:
      all shelved available in the database, as (short name, verbose name)
      tuples

    :rtype: list of (str, unicode)
    """
    prefix = "django-refdb-shelf-"
    extended_notes = get_connection("root").get_extended_notes(":NCK:~" + prefix)
    choices = [(note.citation_key[len(prefix):], note.content.text) for note in extended_notes]
    return choices


def get_verbose_listname(short_listname, user):
    username = get_username(user.id)
    if short_listname == username:
        return _(u"main list")
    try:
        note = get_connection(user).get_extended_notes(":NCK:=%s-%s" % (username, short_listname))[0]
    except IndexError:
        return None
    return (note.content.text if note.content is not None else None) or short_listname
