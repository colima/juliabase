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


from django import forms
from django.contrib.auth.models import User, Permission
from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404
from django.utils.translation import ugettext as _, ugettext_lazy, ugettext
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.http import require_http_methods
from django.template import RequestContext
from django.utils.text import capfirst
from django.contrib.contenttypes.models import ContentType
from chantal_common import utils as common_utils
from samples.models import Process, Task
from samples.views import utils, feed_utils, form_utils
from samples import permissions


class SamplesForm(forms.Form):
    u"""Form for the list selection of samples.
    """
    _ = ugettext_lazy
    sample_list = form_utils.MultipleSamplesField(label=_(u"Samples"))

    def __init__(self, user, preset_sample, task, data=None, **kwargs):
        samples = list(user.my_samples.all())
        self.savable = True
        if task:
            kwargs["initial"] = {"sample_list": task.samples.values_list("pk", flat=True)}
            if user != task.customer or task.status != u"0_new":
                self.fields["sample_list"].widget.attrs["disabled"] = "disabled"
                super(SamplesForm, self).__init__(**kwargs)
            else:
                super(SamplesForm, self).__init__(data, **kwargs)
            samples.extend(task.samples.all())
        else:
            super(SamplesForm, self).__init__(data, **kwargs)
            self.fields["sample_list"].initial = []
            if preset_sample:
                samples.append(preset_sample)
                self.fields["sample_list"].initial.append(preset_sample.pk)
        self.fields["sample_list"].set_samples(samples, user)
        self.fields["sample_list"].widget.attrs.update({"size": "17", "style": "vertical-align: top"})


class TaskForm(forms.ModelForm):
    u"""Model form for a task.
    """
    _ = ugettext_lazy

    operator = forms.ChoiceField(label=capfirst(_(u"operator")), required=False)
    process_content_type = forms.ChoiceField(label=capfirst(_(u"process class")))
    finished_process = forms.ChoiceField(label=capfirst(_(u"finished process")), required=False)

    def __init__(self, user, data=None, **kwargs):
        self.task = kwargs.get("instance")
        super(TaskForm, self).__init__(data, **kwargs)
        self.user = user
        self.fields["customer"].required = False
        self.fields["operator"].choices = [(u"", u"---------")]
        if self.task:
            permission_codename = "add_{0}".format(
                utils.camel_case_to_underscores(self.task.process_content_type.model_class().__name__))
            try:
                add_permission = Permission.objects.get(codename=permission_codename)
            except Permission.DoesNotExist:
                add_permission = None
            eligible_operators = User.objects.filter(is_active=True, chantal_user_details__is_administrative=False). \
                filter(Q(groups__permissions=add_permission) |
                       Q(user_permissions=add_permission)).distinct()
            self.fields["operator"].choices.extend((user.pk, common_utils.get_really_full_name(user))
                                                   for user in utils.sorted_users(eligible_operators))
        self.fields["process_content_type"].choices = form_utils.choices_of_content_types(
            permissions.get_all_addable_physical_process_models())
        self.fields["finished_process"].choices = [(u"", u"---------")]
        if self.task:
            old_finished_process_pk = self.task.finished_process.pk if self.task.finished_process else None
            if self.user == self.task.operator:
                self.fields["finished_process"].choices.extend(
                    [(process.pk, process.actual_instance)
                     for process in Process.objects.filter(
                            Q(operator=self.user, content_type=self.task.process_content_type) |
                            Q(pk=old_finished_process_pk)).order_by("-timestamp")[:10]])
            elif old_finished_process_pk:
                self.fields["finished_process"].append((old_finished_process_pk, self.task.finished_process))
        self.fields["comments"].widget.attrs["cols"] = 30
        self.fields["comments"].widget.attrs["rows"] = 5
        self.fixed_fields = set()
        if self.task:
            self.fixed_fields.add("process_content_type")
            if self.task.status == u"0_new":
                self.fixed_fields.add("finished_process")
            elif self.task.status in [u"1_accepted", u"2_in progress"]:
                if self.user != self.task.operator:
                    self.fixed_fields.update(["status", "priority", "finished_process", "operator"])
                    if self.user != self.task.customer:
                        self.fixed_fields.add("comments")
            else:
                self.fixed_fields.update(["priority", "finished_process", "operator"])
                if self.user != self.task.operator:
                    self.fixed_fields.add("status")
                    if self.user != self.task.customer:
                        self.fixed_fields.add("comments")
        else:
            self.fixed_fields.update(["status", "finished_process", "operator"])
        # for field_name in self.fixed_fields:
        #     self.fields[field_name].widget.attrs["disabled"] = "disabled"

    def clean_status(self):
        if "status" in self.fixed_fields:
            return self.task.status if self.task else u"0_new"
        return self.cleaned_data["status"]

    def clean_process_content_type(self):
        if "process_content_type" in self.fixed_fields:
            return self.task.process_content_type
        pk = self.cleaned_data.get("process_content_type")
        if pk:
            return ContentType.objects.get(pk=int(pk))

    def clean_priority(self):
        if "priority" in self.fixed_fields:
            return self.task.priority
        return self.cleaned_data["priority"]

    def clean_finished_process(self):
        if "finished_process" in self.fixed_fields:
            return self.task.finished_process if self.task else None
        pk = self.cleaned_data.get("finished_process")
        if pk:
            return Process.objects.get(pk=int(pk))

    def clean_comments(self):
        if "comments" in self.fixed_fields:
            return self.task.comments
        return self.cleaned_data["comments"]

    def clean_customer(self):
        return self.task.customer if self.task else self.user

    def clean_operator(self):
        if "operator" in self.fixed_fields:
            return self.task.operator if self.task else None
        pk = self.cleaned_data.get("operator")
        if pk:
            return User.objects.get(pk=int(pk))

    def clean(self):
        _ = ugettext
        cleaned_data = super(TaskForm, self).clean()
        if cleaned_data.get("status") in [u"1_accepted", u"2_in progress", u"3_finished"]:
            if not cleaned_data.get("operator"):
                common_utils.append_error(self, _(u"With this status, you must set an operator."), "operator")
        return cleaned_data

    class Meta:
        model = Task
        exclude = ("samples")


class ChooseTaskListsForm(forms.Form):
    u"""Form for the task lists multiple selection list.
    """
    visible_task_lists = forms.MultipleChoiceField(label=capfirst(_(u"show task lists for")), required=False)

    def __init__(self, user, data=None, **kwargs):
        super(ChooseTaskListsForm, self).__init__(data, **kwargs)
        self.fields["visible_task_lists"].choices = form_utils.choices_of_content_types(
            list(permissions.get_all_addable_physical_process_models()))
        self.fields["visible_task_lists"].initial = [content_type.id for content_type
                                                     in user.samples_user_details.visible_task_lists.iterator()]
        self.fields["visible_task_lists"].widget.attrs["size"] = "15"


class TaskForTemplate(object):
    u"""Class for preparing the tasks for the show template.
    """
    def __init__(self, task, user):
        self.task = task
        self.samples = [sample if (sample.topic and not sample.topic.confidential)
                        or (permissions.has_permission_to_fully_view_sample(user, sample) or
                            permissions.has_permission_to_add_edit_physical_process(user, self.finished_process,
                                                                                    task.process_content_type.model_class()))
                        else _(u"confidential sample") for sample in task.samples.all()]
        self.user_can_edit = user == task.customer or permissions.has_permission_to_add_edit_physical_process(
            user, self.finished_process, task.process_content_type.model_class())


def save_to_database(task_form, samples_form, user, old_task):
    u"""Saves the data for a task into the database.  All validation checks
    must have done before calling this function.

    :Parameters:
      - `task_form`: a bound and valid task form
      - `samples_form`: a bound and valid samples form iff we create a new
        task, or an unbound samples form
      - `user`: the user who has created or edited the task.  It can be the
        customer or the operator of the physical process.
      - `old_task`: the old task instance, which is ``None`` if we newly create
        one

    :type task_form: `TaskForm`
    :type samples_form: `SamplesForm`
    :type user: ``django.contrib.auth.models.User``
    :type old_task: `Task`

    :Returns:
     the saved task database object.

    :rtype: `samples.models.Task`
    """
    task = task_form.save()
    if samples_form.is_bound:
        task.samples = samples_form.cleaned_data["sample_list"]
    if old_task and old_task.status == "0_new" and task.status == "1_accepted":
        user.my_samples.add(*task.samples.all())
    return task


@login_required
def edit(request, task_id):
    u"""Edit or create a task.

    :Parameters:
      - `request`: the current HTTP Request object
      - `task_id`: number of the task to be edited.  If this is
        ``None``, create a new one.

    :type request: ``HttpRequest``
    :type task_id: unicode

    :Returns:
      the HTTP response object

    :rtype: ``HttpResponse``
    """
    task = get_object_or_404(Task, id=utils.convert_id_to_int(task_id)) if task_id is not None else None
    user = request.user
    if task and user != task.customer:
        permissions.assert_can_add_physical_process(request.user, task.process_content_type.model_class())
    preset_sample = utils.extract_preset_sample(request) if not task else None
    if request.method == "POST":
        task_form = TaskForm(user, request.POST, instance=task)
        samples_form = SamplesForm(user, preset_sample, task, request.POST)
        if task_form.is_valid() and (not samples_form.is_bound or samples_form.is_valid()):
            new_task = save_to_database(task_form, samples_form, user, old_task=task)
            if task:
                edit_description = {"important": True, "description": u""}
                if task.status != new_task.status:
                    edit_description["description"] += \
                        _(u"* Status is now {new_status}.\n").format(new_status=new_task.status)
                if task.priority != new_task.priority:
                    edit_description["description"] += \
                        _(u"* Priority is now {new_priority}.").format(new_priority=new_task.priority)
                if task.finished_process != new_task.finished_process:
                    edit_description["description"] += _(u"* Connected process.")
                if set(task.samples.all()) != set(new_task.samples.all()):
                    edit_description["description"] += u"* {0}.".format(utils.capitalize_first_letter(_(u"samples")))
                if task.comments != new_task.comments:
                    edit_description["description"] += u"* {0}.".format(utils.capitalize_first_letter(_(u"comments")))
            else:
                edit_description = None
            feed_utils.Reporter(request.user).report_task(new_task, edit_description)
            message = _(u"Task was {verb} successfully.").format(verb=u"edited" if task else u"added")
            return utils.successful_response(request, message, "samples.views.task_lists.show")
    else:
        samples_form = SamplesForm(user, preset_sample, task)
        initial = {}
        if task:
            initial["process_content_type"] = task.process_content_type.pk
            initial["finished_process"] = task.finished_process.pk if task.finished_process else None
        elif "process_class" in request.GET:
            initial["process_content_type"] = request.GET["process_class"]
        task_form = TaskForm(request.user, instance=task, initial=initial)
    title = _(u"Edit task") if task else _(u"Add task")
    return render_to_response("samples/edit_task.html", {"title": title,
                                                         "task": task_form,
                                                         "samples": samples_form},
                              context_instance=RequestContext(request))

@login_required
def show(request):
    u"""Shows the task lists the user wants to see.
    It also provides the multiple choice list to select the task lists
    for the user.

    :Paramerters:
     - `request`: the current HTTP Request object

    :Returns:
      the HTTP response object

    :rtype: ``HttpResponse``
    """
    if request.method == "POST":
        choose_task_lists_form = ChooseTaskListsForm(request.user, request.POST)
        if choose_task_lists_form.is_valid():
            request.user.samples_user_details.visible_task_lists = \
                [ContentType.objects.get_for_id(int(id_))
                 for id_ in choose_task_lists_form.cleaned_data["visible_task_lists"]]
            # In order to have a GET instead of a POST as the last request
            return utils.successful_response(request, view=show)
    else:
        choose_task_lists_form = ChooseTaskListsForm(request.user)
    task_lists = dict([(content_type, [TaskForTemplate(task, request.user)
                                       for task in content_type.tasks.order_by("-status", "priority", "last_modified")])
                       for content_type in request.user.samples_user_details.visible_task_lists.iterator()])
    return render_to_response("samples/task_lists.html", {"title": _(u"Task lists"),
                                                          "chose_task_lists": choose_task_lists_form,
                                                          "task_lists": task_lists},
                              context_instance=RequestContext(request))


@login_required
@require_http_methods(["POST"])
def remove(request, task_id):
    u"""Deletes a task from the database.

    :Paramerters:
     - `request`: the current HTTP Request object
     - `task_id`: the id from the task, which has to be deleted

    :Return:
      the HTTP response object

    :rtype: ``HttpResponse``
    """
    task = get_object_or_404(Task, id=utils.convert_id_to_int(task_id))
    if task.customer == request.user:
        physical_process_content_type = task.process_content_type
        samples = list(task.samples.all())
        task.delete()
        feed_utils.Reporter(request.user).report_removed_task(physical_process_content_type, samples)
    else:
        raise permissions.PermissionError(request.user, u"You cannot remove this task.")
    return utils.successful_response(request, _(u"The task was successfully removed."), show)
