# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import datetime
import django

from collections import OrderedDict

from django import forms
from django.conf import settings
from django.contrib import admin
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext as _

try:
    import pytz
except ImportError:
    pytz = None

try:
    from suit.widgets import SuitDateWidget as AdminDateWidget
except ImportError:
    from django.contrib.admin.widgets import AdminDateWidget


def make_dt_aware(dt):
    if pytz is not None and settings.USE_TZ:
        timezone = pytz.timezone(settings.TIME_ZONE)
        if dt.tzinfo is not None:
            dt = timezone.normalize(dt)
        else:
            dt = timezone.localize(dt)
    return dt


class DateRangeFilter(admin.filters.FieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg_gte = '{}__gte'.format(field_path)
        self.lookup_kwarg_lte = '{}__lte'.format(field_path)

        super(DateRangeFilter, self).__init__(field, request, params, model, model_admin, field_path)

        self.form = self.get_form(request)

    def choices(self, cl):
        yield {
            'system_name': slugify(self.title),
            'query_string': cl.get_query_string(
                {}, remove=[self.lookup_kwarg_gte, self.lookup_kwarg_lte]
            )
        }

    def expected_parameters(self):
        return [self.lookup_kwarg_gte, self.lookup_kwarg_lte]

    def queryset(self, request, queryset):
        if self.form.is_valid():
            validated_data = dict(self.form.cleaned_data.items())
            if validated_data:
                return queryset.filter(
                    **self._make_query_filter(validated_data)
                )
        return queryset

    def _make_query_filter(self, validated_data):
        query_params = {}
        date_value_gte = validated_data.get(self.lookup_kwarg_gte, None)
        date_value_lte = validated_data.get(self.lookup_kwarg_lte, None)

        if date_value_gte:
            query_params['{0}__gte'.format(self.field_path)] = make_dt_aware(
                datetime.datetime.combine(date_value_gte, datetime.time.min)
            )
        if date_value_lte:
            query_params['{0}__lte'.format(self.field_path)] = make_dt_aware(
                datetime.datetime.combine(date_value_lte, datetime.time.min)
            )
        return query_params

    def get_template(self):
        if django.VERSION <= (1, 8):
            return 'rangefilter/date_filter_1_8.html'
        return 'rangefilter/date_filter.html'

    template = property(get_template)

    def get_form(self, request):
        form_class = self._get_form_class()
        return form_class(self.used_parameters)

    def _get_form_class(self):
        fields = self._get_form_fields()

        form_class = type(
            str('DateRangeForm'),
            (forms.BaseForm,),
            {'base_fields': fields}
        )
        form_class.media = self._get_media()

        return form_class

    def _get_form_fields(self):
        return OrderedDict((
                (self.lookup_kwarg_gte, forms.DateField(
                    label='',
                    widget=AdminDateWidget(attrs={'placeholder': _('From date')}),
                    localize=True,
                    required=False
                )),
                (self.lookup_kwarg_lte, forms.DateField(
                    label='',
                    widget=AdminDateWidget(attrs={'placeholder': _('To date')}),
                    localize=True,
                    required=False
                )),
        ))

    @staticmethod
    def _get_media():
        js = [
            'calendar.js',
            'admin/DateTimeShortcuts.js',
        ]
        css = [
            'widgets.css',
        ]
        return forms.Media(
            js=['admin/js/%s' % url for url in js],
            css={'all': ['admin/css/%s' % path for path in css]}
        )
