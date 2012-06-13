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


"""Models for IEF-5-specific depositions.  This includes the deposition models
themselves as well as models for layers.  Additionally, there are miscellaneous
models like the one to 6-chamber deposition channels.
"""

from __future__ import absolute_import, unicode_literals

import re
from decimal import Decimal
from django.utils.translation import ugettext_lazy as _, ugettext, pgettext_lazy
import django.core.urlresolvers
from django.utils.http import urlquote, urlquote_plus
from django.db import models
import samples.models_depositions
from samples import permissions
from samples.data_tree import DataNode, DataItem
from chantal_common import search
from chantal_common import models as chantal_common_models
from django.utils.translation import string_concat
from django.contrib.auth.models import User
from chantal_common.utils import get_really_full_name



class ClusterToolHotWireAndPECVDGases(models.Model):
    h2 = models.DecimalField("H₂", max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("in sccm"))
    sih4 = models.DecimalField("SiH₄", max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("in sccm"))
    mms = models.DecimalField("MMS", max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("in sccm"))
    tmb = models.DecimalField("TMB", max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("in sccm"))
    co2 = models.DecimalField("CO₂", max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("in sccm"))
    ph3 = models.DecimalField("PH₃", max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("in sccm"))
    ch4 = models.DecimalField("CH₄", max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("in sccm"))
    ar = models.DecimalField("Ar", max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("in sccm"))

    class Meta:
        abstract = True

    def get_data_items(self):
        return [DataItem("H2/sccm", self.h2),
                DataItem("SiH4/sccm", self.sih4),
                DataItem("MMS/sccm", self.mms),
                DataItem("TMB/sccm", self.tmb),
                DataItem("CO2/sccm", self.co2),
                DataItem("PH3/sccm", self.ph3),
                DataItem("CH4/sccm", self.ch4),
                DataItem("Ar/sccm", self.ar)]

    def get_data_items_for_table_export(self):
        return [DataItem("H₂/sccm", self.h2),
                DataItem("SiH₄/sccm", self.sih4),
                DataItem("MMS/sccm", self.mms),
                DataItem("TMB/sccm", self.tmb),
                DataItem("CO₂/sccm", self.co2),
                DataItem("PH₃/sccm", self.ph3),
                DataItem("CH₄/sccm", self.ch4),
                DataItem("Ar/sccm", self.ar)]


class ClusterToolDeposition(samples.models_depositions.Deposition):
    """cluster tool depositions..
    """
    carrier = models.CharField(_("carrier"), max_length=10, blank=True)

    class Meta(samples.models_depositions.Deposition.Meta):
        verbose_name = _("cluster tool deposition")
        verbose_name_plural = _("cluster tool depositions")
        _ = lambda x: x
        permissions = (("add_cluster_tool_deposition", _("Can add cluster tool depositions")),
                       ("edit_permissions_for_cluster_tool_deposition",
                       # Translators: Don't abbreviate "perms" in translation
                       # (not even to English)
                        _("Can edit perms for cluster tool I depositions")),
                       ("view_every_cluster_tool_deposition", _("Can view all cluster tool depositions")),
                       ("edit_every_cluster_tool_deposition", _("Can edit all cluster tool depositions")))

    @models.permalink
    def get_absolute_url(self):
        return ("chantal_institute.views.samples.cluster_tool_deposition.show", [urlquote(self.number, safe="")])

    @classmethod
    def get_add_link(cls):
        """Return all you need to generate a link to the “add” view for this
        process.

        :Return:
          the full URL to the add page for this process

        :rtype: str
        """
        _ = ugettext
        return django.core.urlresolvers.reverse("add_cluster_tool_deposition")

    def get_context_for_user(self, user, old_context):
        """
        Additionally, because this is a cluster tool and thus has different
        type of layers, I add a layer list ``layers`` to the template context.
        The template can't access the layers with ``process.layers.all()``
        because they are polymorphic.  But ``layers`` can be conveniently
        digested by the template.
        """
        context = old_context.copy()
        layers = []
        for layer in self.layers.all():
            try:
                layer = layer.clustertoolhotwirelayer
                layer.type = "hot-wire"
            except ClusterToolHotWireLayer.DoesNotExist:
                layer = layer.clustertoolpecvdlayer
                layer.type = "PECVD"
            layers.append(layer)
        context["layers"] = layers
        if permissions.has_permission_to_edit_physical_process(user, self):
            context["edit_url"] = django.core.urlresolvers.reverse("edit_cluster_tool_deposition",
                                                                   kwargs={"deposition_number": self.number})
        else:
            context["edit_url"] = None
        if permissions.has_permission_to_add_physical_process(user, self.__class__):
            context["duplicate_url"] = "{0}?copy_from={1}".format(
                django.core.urlresolvers.reverse("add_cluster_tool_deposition"), urlquote_plus(self.number))
        else:
            context["duplicate_url"] = None
        return super(ClusterToolDeposition, self).get_context_for_user(user, context)

    def get_data(self):
        data_node = super(ClusterToolDeposition, self).get_data()
        data_node.items.append(DataItem("carrier", self.carrier))
        data_node.children = [layer.actual_instance.get_data() for layer in self.layers.all()]
        return data_node

    def get_data_for_table_export(self):
        _ = ugettext
        data_node = super(ClusterToolDeposition, self).get_data_for_table_export()
        data_node.items.append(DataItem(_("carrier"), self.carrier))
        data_node.children = [layer.actual_instance.get_data_for_table_export() for layer in self.layers.all()]
        return data_node

    @classmethod
    def get_search_tree_node(cls):
        """Class method for generating the search tree node for this model
        instance.  I must override the inherited method because I want to offer
        the layer models directly instead of the proxy class
        `OldClusterToolLayer`.

        :Return:
          the tree node for this model instance

        :rtype: ``chantal_common.search.SearchTreeNode``
        """
        model_field = super(ClusterToolDeposition, cls).get_search_tree_node()
        model_field.related_models.update({ClusterToolHotWireLayer: "layers", ClusterToolPECVDLayer: "layers"})
        del model_field.related_models[ClusterToolLayer]
        return model_field

samples.models_depositions.default_location_of_deposited_samples[ClusterToolDeposition] = \
    _("large-area deposition lab")


class ClusterToolLayer(samples.models_depositions.Layer, chantal_common_models.PolymorphicModel):
    """Model for a layer the “cluster tool”.  Note that this is the common
    base class for the actual layer models `ClusterToolHotWireLayer` and
    `ClusterToolPECVDLayer`.  This is *not* an abstract model though because
    it needs to be back-referenced from the deposition.  I need inheritance and
    polymorphism here because cluster tools may have layers with very different
    fields.
    """
    deposition = models.ForeignKey(ClusterToolDeposition, related_name="layers", verbose_name=_("deposition"))

    class Meta(samples.models_depositions.Layer.Meta):
        unique_together = ("deposition", "number")
        verbose_name = _("cluster tool layer")
        verbose_name_plural = _("cluster tool layers")

    def __unicode__(self):
        _ = ugettext
        return _("layer {number} of {deposition}").format(number=self.number, deposition=self.deposition)


cluster_tool_wire_material_choices = (
    ("unknown", _("unknown")),
    ("rhenium", _("rhenium")),
    ("tantalum", _("tantalum")),
    ("tungsten", _("tungsten")),
)
class ClusterToolHotWireLayer(ClusterToolLayer, ClusterToolHotWireAndPECVDGases):
    """Model for a hot-wire layer in the cluster tool.  We have no
    “chamber” field here because there is only one hot-wire chamber anyway.
    """
    pressure = models.DecimalField(_("deposition pressure"), max_digits=5, decimal_places=3, help_text=_("in mbar"),
                                   null=True, blank=True)
    time = models.CharField(_("deposition time"), max_length=9, help_text=_("format HH:MM:SS"), blank=True)
    substrate_wire_distance = models.DecimalField(_("substrate–wire distance"), null=True, blank=True, max_digits=4,
                                                  decimal_places=1, help_text=_("in mm"))
    comments = models.TextField(_("comments"), blank=True)
    transfer_in_chamber = models.CharField(_("transfer in the chamber"), max_length=10, default="Ar", blank=True)
    pre_heat = models.CharField(_("pre-heat"), max_length=9, blank=True, help_text=_("format HH:MM:SS"))
    gas_pre_heat_gas = models.CharField(_("gas of gas pre-heat"), max_length=10, blank=True)
    gas_pre_heat_pressure = models.DecimalField(_("pressure of gas pre-heat"), max_digits=5, decimal_places=3,
                                                null=True, blank=True, help_text=_("in mbar"))
    gas_pre_heat_time = models.CharField(_("time of gas pre-heat"), max_length=15, blank=True,
                                         help_text=_("format HH:MM:SS"))
    heating_temperature = models.IntegerField(_("heating temperature"), help_text=_("in ℃"), null=True, blank=True)
    transfer_out_of_chamber = models.CharField(_("transfer out of the chamber"), max_length=10, default="Ar", blank=True)
    filament_temperature = models.DecimalField(_("filament temperature"), max_digits=5, decimal_places=1,
                                               null=True, blank=True, help_text=_("in ℃"))
    current = models.DecimalField(_("wire current"), max_digits=6, decimal_places=2, null=True, blank=True,
                                  # Translators: Ampère
                                  help_text=_("in A"))
    voltage = models.DecimalField(_("wire voltage"), max_digits=6, decimal_places=2, null=True, blank=True,
                                  # Translators: Volt
                                  help_text=_("in V"))
    wire_power = models.DecimalField(_("wire power"), max_digits=6, decimal_places=2, null=True, blank=True,
                                     help_text=_("in W"))
    wire_material = models.CharField(_("wire material"), max_length=20, choices=cluster_tool_wire_material_choices)
    base_pressure = models.FloatField(_("base pressure"), help_text=_("in mbar"), null=True, blank=True)

    class Meta(ClusterToolLayer.Meta):
        verbose_name = _("cluster tool hot-wire layer")
        verbose_name_plural = _("cluster tool hot-wire layers")


    def get_data(self):
        # See `Layer.get_data` for the documentation.
        data_node = samples.models_depositions.Layer.get_data(self)
        data_node.items = [DataItem("layer type", "hot-wire"),
                           DataItem("pressure/mbar", self.pressure),
                           DataItem("time", self.time),
                           DataItem("substrate-wire distance/mm", self.substrate_wire_distance),
                           DataItem("comments", self.comments),
                           DataItem("transfer in chamber", self.transfer_in_chamber),
                           DataItem("pre-heat", self.pre_heat),
                           DataItem("gas pre-heat gas", self.gas_pre_heat_gas),
                           DataItem("gas pre-heat pressure/mbar", self.gas_pre_heat_pressure),
                           DataItem("gas pre-heat time", self.gas_pre_heat_time),
                           DataItem("heating temperature/degC", self.heating_temperature),
                           DataItem("transfer out of chamber", self.transfer_out_of_chamber),
                           DataItem("filament temperature/degC", self.filament_temperature),
                           DataItem("current/A", self.current),
                           DataItem("voltage/V", self.voltage),
                           DataItem("wire power/W", self.wire_power),
                           DataItem("wire material", self.wire_material),
                           DataItem("base pressure/mbar", self.base_pressure)]
        data_node.items.extend(ClusterToolHotWireAndPECVDGases.get_data_items(self))
        return data_node


    def get_data_for_table_export(self):
        # See `Layer.get_data_for_table_export` for the documentation.
        _ = ugettext
        data_node = samples.models_depositions.Layer.get_data_for_table_export(self)
        data_node.items = [DataItem(_("pressure") + "/mbar", self.pressure),
                            DataItem(_("time"), self.time),
                            DataItem(_("substrate–wire distance") + "/mm", self.substrate_wire_distance),
                            DataItem(_("comments"), self.comments),
                            DataItem(_("transfer in chamber"), self.transfer_in_chamber),
                            DataItem(_("pre-heat"), self.pre_heat),
                            DataItem(_("gas pre-heat gas"), self.gas_pre_heat_gas),
                            DataItem(_("gas pre-heat pressure") + "/mbar", self.gas_pre_heat_pressure),
                            DataItem(_("gas pre-heat time"), self.gas_pre_heat_time),
                            DataItem(_("heating temperature") + "/degC", self.heating_temperature),
                            DataItem(_("transfer out of chamber"), self.transfer_out_of_chamber),
                            DataItem(_("filament temperature") + "/degC", self.filament_temperature),
                            DataItem(_("current") + "/A", self.current),
                            DataItem(_("voltage") + "/V", self.voltage),
                            DataItem(_("wire power") + "/W", self.wire_power),
                            DataItem(_("wire material"), self.get_wire_material_display()),
                            DataItem(_("base pressure") + "/mbar", self.base_pressure)]
        data_node.items.extend(ClusterToolHotWireAndPECVDGases.get_data_items_for_table_export(self))
        return data_node


cluster_tool_pecvd_chamber_choices = (
    ("#1", "#1"),
    ("#2", "#2"),
    ("#3", "#3"),
)
class ClusterToolPECVDLayer(ClusterToolLayer, ClusterToolHotWireAndPECVDGases):
    """Model for a PECDV layer in the cluster tool.
    """
    deposition_frequency = models.DecimalField(_("deposition frequency"), max_digits=5, decimal_places=2,
                                               null=True, blank=True, help_text=_("in MHz"))
    chamber = models.CharField(_("chamber"), max_length=5, choices=cluster_tool_pecvd_chamber_choices)
    pressure = models.DecimalField(_("deposition pressure"), max_digits=5, decimal_places=3, help_text=_("in mbar"),
                                   null=True, blank=True)
    time = models.CharField(_("deposition time"), max_length=9, help_text=_("format HH:MM:SS"), blank=True)
    substrate_electrode_distance = \
        models.DecimalField(_("substrate–electrode distance"), null=True, blank=True, max_digits=4,
                            decimal_places=1, help_text=_("in mm"))
    comments = models.TextField(_("comments"), blank=True)
    transfer_in_chamber = models.CharField(_("transfer in the chamber"), max_length=10, default="Ar", blank=True)
    pre_heat = models.CharField(_("pre-heat"), max_length=9, blank=True, help_text=_("format HH:MM:SS"))
    gas_pre_heat_gas = models.CharField(_("gas of gas pre-heat"), max_length=10, blank=True)
    gas_pre_heat_pressure = models.DecimalField(_("pressure of gas pre-heat"), max_digits=5, decimal_places=3,
                                                null=True, blank=True, help_text=_("in mbar"))
    gas_pre_heat_time = models.CharField(_("time of gas pre-heat"), max_length=15, blank=True,
                                         help_text=_("format HH:MM:SS"))
    heating_temperature = models.IntegerField(_("heating temperature"), help_text=_("in ℃"), null=True, blank=True)
    transfer_out_of_chamber = models.CharField(_("transfer out of the chamber"), max_length=10, default="Ar", blank=True)
    plasma_start_power = models.DecimalField(_("plasma start power"), max_digits=6, decimal_places=2, null=True, blank=True,
                                             help_text=_("in W"))
    plasma_start_with_shutter = models.BooleanField(_("plasma start with shutter"), default=False)
    deposition_power = models.DecimalField(_("deposition power"), max_digits=6, decimal_places=2, null=True, blank=True,
                                           help_text=_("in W"))
    base_pressure = models.FloatField(_("base pressure"), help_text=_("in mbar"), null=True, blank=True)


    class Meta(ClusterToolLayer.Meta):
        verbose_name = _("cluster tool PECVD layer")
        verbose_name_plural = _("cluster tool PECVD layers")


    def get_data(self):
        # See `Layer.get_data` for the documentation.
        data_node = samples.models_depositions.Layer.get_data(self)
        data_node.items = [DataItem("layer type", "PECVD"),
                            DataItem("chamber", self.chamber),
                            DataItem("pressure/mbar", self.pressure),
                            DataItem("time", self.time),
                            DataItem("substrate-electrode distance/mm", self.substrate_electrode_distance),
                            DataItem("comments", self.comments),
                            DataItem("transfer in chamber", self.transfer_in_chamber),
                            DataItem("pre-heat", self.pre_heat),
                            DataItem("gas pre-heat gas", self.gas_pre_heat_gas),
                            DataItem("gas pre-heat pressure/mbar", self.gas_pre_heat_pressure),
                            DataItem("gas pre-heat time", self.gas_pre_heat_time),
                            DataItem("heating temperature/degC", self.heating_temperature),
                            DataItem("transfer out of chamber", self.transfer_out_of_chamber),
                            DataItem("plasma start power/W", self.plasma_start_power),
                            DataItem("plasma start with shutter", self.plasma_start_with_shutter),
                            DataItem("deposition frequency/MHz", self.deposition_frequency),
                            DataItem("deposition power/W", self.deposition_power),
                            DataItem("base pressure/mbar", self.base_pressure)]
        data_node.items.extend(ClusterToolHotWireAndPECVDGases.get_data_items(self))
        return data_node


    def get_data_for_table_export(self):
        _ = ugettext
        # See `Layer.get_data_for_table_export` for the documentation.
        data_node = samples.models_depositions.Layer.get_data_for_table_export(self)
        data_node.items = [DataItem(_("chamber"), self.get_chamber_display()),
                            DataItem(_("pressure") + "/mbar", self.pressure),
                            DataItem(_("time"), self.time),
                            DataItem(_("substrate–electrode distance") + "/mm", self.substrate_electrode_distance),
                            DataItem(_("comments"), self.comments),
                            DataItem(_("transfer in chamber"), self.transfer_in_chamber),
                            DataItem(_("pre-heat"), self.pre_heat),
                            DataItem(_("gas pre-heat gas"), self.gas_pre_heat_gas),
                            DataItem(_("gas pre-heat pressure") + "/mbar", self.gas_pre_heat_pressure),
                            DataItem(_("gas pre-heat time"), self.gas_pre_heat_time),
                            DataItem(_("heating temperature") + "/degC", self.heating_temperature),
                            DataItem(_("transfer out of chamber"), self.transfer_out_of_chamber),
                            DataItem(_("plasma start power") + "/W", self.plasma_start_power),
                            DataItem(_("plasma start with shutter"), _("yes") if self.plasma_start_with_shutter else _("no")),
                            DataItem(_("deposition frequency") + "/MHz", self.deposition_frequency),
                            DataItem(_("deposition power") + "/W", self.deposition_power),
                            DataItem(_("base pressure") + "/mbar", self.base_pressure)]
        data_node.items.extend(ClusterToolHotWireAndPECVDGases.get_data_items_for_table_export(self))
        return data_node



class FiveChamberDeposition(samples.models_depositions.Deposition):
    """5-chamber depositions.
    """
    class Meta(samples.models_depositions.Deposition.Meta):
        verbose_name = _("5-chamber deposition")
        verbose_name_plural = _("5-chamber depositions")
        _ = lambda x: x
        permissions = (("add_five_chamber_deposition", _("Can add 5-chamber depositions")),
                       # Translators: Don't abbreviate "perms" in translation
                       # (not even to English)
                       ("edit_permissions_for_five_chamber_deposition", _("Can edit perms for 5-chamber depositions")),
                       ("view_every_five_chamber_deposition", _("Can view all 5-chamber depositions")),
                       ("edit_every_five_chamber_deposition", _("Can edit all 5-chamber depositions")))

    @models.permalink
    def get_absolute_url(self):
        return ("chantal_institute.views.samples.five_chamber_deposition.show", [urlquote(self.number, safe="")])

    @classmethod
    def get_add_link(cls):
        """Return all you need to generate a link to the “add” view for this
        process.  See `SixChamberDeposition.get_add_link`.

        :Return:
          the full URL to the add page for this process

        :rtype: str
        """
        _ = ugettext
        return django.core.urlresolvers.reverse("add_5-chamber_deposition")

    def get_context_for_user(self, user, old_context):
        context = old_context.copy()
        if permissions.has_permission_to_edit_physical_process(user, self):
            context["edit_url"] = \
                django.core.urlresolvers.reverse("edit_5-chamber_deposition", kwargs={"deposition_number": self.number})
        else:
            context["edit_url"] = None
        if permissions.has_permission_to_add_physical_process(user, self.__class__):
            context["duplicate_url"] = "{0}?copy_from={1}".format(
                django.core.urlresolvers.reverse("add_5-chamber_deposition"), urlquote_plus(self.number))
        else:
            context["duplicate_url"] = None
        return super(FiveChamberDeposition, self).get_context_for_user(user, context)

    @classmethod
    def get_search_tree_node(cls):
        """Class method for generating the search tree node for this model
        instance.  I must override the inherited method because I want to offer
        the layer models directly instead of the proxy class
        `NewClusterToolLayer`.

        :Return:
          the tree node for this model instance

        :rtype: ``chantal_common.search.SearchTreeNode``
        """
        model_field = super(FiveChamberDeposition, cls).get_search_tree_node()
        model_field.related_models.update({FiveChamberLayer: "layers"})
        return model_field

samples.models_depositions.default_location_of_deposited_samples[FiveChamberDeposition] = _("5-chamber deposition lab")


five_chamber_chamber_choices = (
    ("i1", "i1"),
    ("i2", "i2"),
    ("i3", "i3"),
    ("p", "p"),
    ("n", "n"),
)

five_chamber_layer_type_choices = (
    ("p", "p"),
    ("i", "i"),
    ("n", "n"),
)

five_chamber_hf_frequency_choices = (
    (Decimal("13.26"), "13.26"),
    (Decimal("13.56"), "13.56"),
    (Decimal("16.56"), "16.56"),
    (Decimal("40"), "40"),
    (Decimal("100"), "100"),
)

five_chamber_impurity_choices = (
    ("O2", "O₂"),
    ("N2", "N₂"),
    ("PH3", "PH₃"),
    ("TMB", "TMB"),
    ("Air", _("Air")),
)

five_chamber_measurement_choices = (
    ("Raman", "Raman"),
    ("OES", "OES"),
    ("FTIR", "FTIR"),
)

class FiveChamberLayer(samples.models_depositions.Layer):
    """One layer in a 5-chamber deposition.
    """
    deposition = models.ForeignKey(FiveChamberDeposition, related_name="layers", verbose_name=_("deposition"))
    date = models.DateField(_("date"))
    layer_type = models.CharField(_("layer type"), max_length=2, choices=five_chamber_layer_type_choices, blank=True)
    chamber = models.CharField(_("chamber"), max_length=2, choices=five_chamber_chamber_choices)
    sih4 = models.DecimalField("SiH₄", max_digits=7, decimal_places=3, help_text=_("in sccm"), null=True, blank=True)
    h2 = models.DecimalField("H₂", max_digits=7, decimal_places=3, help_text=_("in sccm"), null=True, blank=True)
    tmb = models.DecimalField("TMB", max_digits=7, decimal_places=3, help_text=_("in sccm"), null=True, blank=True)
    ch4 = models.DecimalField("CH₄", max_digits=7, decimal_places=3, help_text=_("in sccm"), null=True, blank=True)
    co2 = models.DecimalField("CO₂", max_digits=7, decimal_places=3, help_text=_("in sccm"), null=True, blank=True)
    ph3 = models.DecimalField("PH₃", max_digits=7, decimal_places=3, help_text=_("in sccm"), null=True, blank=True)
    power = models.DecimalField(_("power"), max_digits=7, decimal_places=3, help_text=_("in W"), null=True, blank=True)
    pressure = models.DecimalField(_("pressure"), max_digits=7, decimal_places=3, help_text=_("in Torr"), null=True,
                                   blank=True)
    base_pressure = models.FloatField(_("base pressure"), help_text=_("in Torr"), null=True,
                                   blank=True)
    temperature_1 = models.DecimalField(_("temperature 1"), max_digits=7, decimal_places=3, help_text=_("in ℃"),
                                      null=True, blank=True)
    temperature_2 = models.DecimalField(_("temperature 2"), max_digits=7, decimal_places=3, help_text=_("in ℃"),
                                      null=True, blank=True)
    hf_frequency = models.DecimalField(_("HF frequency"), max_digits=5, decimal_places=2, null=True, blank=True,
                                       choices=five_chamber_hf_frequency_choices, help_text=_("in MHz"))
    time = models.IntegerField(_("time"), help_text=_("in sec"), null=True, blank=True)
    dc_bias = models.DecimalField(_("DC bias"), max_digits=7, decimal_places=3, help_text=_("in V"), null=True,
                                  blank=True)
    electrodes_distance = models.DecimalField(_("electrodes distance"), max_digits=7, decimal_places=3,
                                               help_text=_("in mm"), null=True, blank=True)
    impurity = models.CharField(_("impurity"), max_length=5, choices=five_chamber_impurity_choices, blank=True)
    in_situ_measurement = models.CharField(_("in-situ measurement"), max_length=10, blank=True,
                                            choices=five_chamber_measurement_choices)
    data_file = models.CharField(_("measurement data file"), max_length=80, blank=True,
                                 help_text=_("only the relative path below \"5k_PECVD/\""))

    class Meta(samples.models_depositions.Layer.Meta):
        unique_together = ("deposition", "number")
        verbose_name = _("5-chamber layer")
        verbose_name_plural = _("5-chamber layers")

    def __unicode__(self):
        _ = ugettext
        return _("layer {number} of {deposition}").format(number=self.number, deposition=self.deposition)

    def get_data(self):
        # See `Layer.get_data` for the documentation.
        data_node = super(FiveChamberLayer, self).get_data()
        if self.sih4 and self.h2:
            silane_normalized = 0.6 * float(self.sih4)
            silane_concentration = silane_normalized / (silane_normalized + float(self.h2)) * 100
        else:
            silane_concentration = 0
        data_node.items.extend([DataItem("date", self.date),
                                DataItem("layer type", self.layer_type),
                                DataItem("chamber", self.chamber),
                                DataItem("SiH4/sccm", self.sih4),
                                DataItem("H2/sccm", self.h2),
                                DataItem("TMB/sccm", self.tmb),
                                DataItem("CH4/sccm", self.ch4),
                                DataItem("CO2/sccm", self.co2),
                                DataItem("PH3/sccm", self.ph3),
                                DataItem("SC/%", "{0:5.2f}".format(silane_concentration)),
                                DataItem("power/W", self.power),
                                DataItem("pressure/Torr", self.pressure),
                                DataItem("base pressure/Torr", self.base_pressure),
                                DataItem("T/degC (1)", self.temperature_1),
                                DataItem("T/degC (2)", self.temperature_2),
                                DataItem("f_HF/MHz", self.hf_frequency),
                                DataItem("time/s", self.time),
                                DataItem("DC bias/V", self.dc_bias),
                                DataItem("elec. dist./mm", self.electrodes_distance),
                                DataItem("impurity", self.impurity),
                                DataItem("in-situ measurement", self.in_situ_measurement),
                                DataItem("data file", self.data_file)])
        return data_node

    def get_data_for_table_export(self):
        # See `Layer.get_data_for_table_export` for the documentation.
        _ = ugettext
        data_node = super(FiveChamberLayer, self).get_data_for_table_export()
        if self.sih4 and self.h2:
            silane_normalized = 0.6 * float(self.sih4)
            silane_concentration = silane_normalized / (silane_normalized + float(self.h2)) * 100
        else:
            silane_concentration = 0
        data_node.items.extend([DataItem(_("date"), self.date),
                                DataItem(_("layer type"), self.get_layer_type_display()),
                                DataItem(_("chamber"), self.get_chamber_display()),
                                DataItem("SiH₄/sccm", self.sih4),
                                DataItem("H₂/sccm", self.h2),
                                DataItem("TMB/sccm", self.tmb),
                                DataItem("CH₄/sccm", self.ch4),
                                DataItem("CO₂/sccm", self.co2),
                                DataItem("PH₃/sccm", self.ph3),
                                DataItem("SC/%", "{0:5.2f}".format(silane_concentration)),
                                DataItem(_("power") + "/W", self.power),
                                DataItem(_("pressure") + "/Torr", self.pressure),
                                DataItem(_("base pressure") + "/Torr", self.base_pressure),
                                DataItem("T/℃ (1)", self.temperature_1),
                                DataItem("T/℃ (2)", self.temperature_2),
                                DataItem("f_HF/MHz", self.hf_frequency),
                                DataItem(_("time") + "/s", self.time),
                                DataItem(_("DC bias") + "/V", self.dc_bias),
                                DataItem(_("elec. dist.") + "/mm", self.electrodes_distance),
                                DataItem(_("impurity"), self.get_impurity_display()),
                                DataItem(_("in-situ measurement"), self.get_in_situ_measurement_display()),
                                DataItem(_("data file"), self.data_file)])
        return data_node
