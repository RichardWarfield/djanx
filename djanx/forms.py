from django import forms as djforms
from django.utils import timezone, six
from django.core.exceptions import ValidationError
from django.contrib.postgres.forms import jsonb
from django.utils.translation import ugettext_lazy as _
import dateutil

# TODO: initial data from model/queryset

class DjanxForm(object):

    @classmethod
    def get_base_schema(cls):
        """
        Returns a JSON representation of the django model, based on the
        base_fields of the form class.
        """
        try:
            hidden_fields = set(cls.Meta.hidden)
        except AttributeError:
            hidden_fields = set()

        try:
            static_data = cls.Meta.static
        except AttributeError:
            static_data = {}
        return _create_schema(cls.base_fields, hidden_fields, static_data)


    def get_schema(self):
        """
        Returns a JSON representation of the django model, based on the 
        concrete fields of the form instance.
        """
        try:
            hidden_fields = set(self.Meta.hidden)
        except AttributeError:
            hidden_fields = set()

        try:
            static_data = self.Meta.static
        except AttributeError:
            static_data = {}
        return _create_schema(self.fields, hidden_fields, static_data)


    def get_static(self, obj):
        try:
            static_data = self.Meta.static
        except AttributeError:
            static_data = {}

        objs_qs = obj._meta.model.objects.filter(pk=obj.pk) # one object
        fields = [sd['field'] for sd in list(static_data.values())]
        rawdata = objs_qs.values(*fields)[0]
        return {k: rawdata[v['field']] for (k,v) in list(static_data.items())}

def _create_schema(fields, hidden_fields, static_data):
    result = {}
    for (fname, formfield) in list(fields.items()):

        field_schema = get_formfield_schema(formfield)
        field_schema['name'] = fname
        field_schema['hidden'] = (fname in hidden_fields)
        result[fname] = field_schema

    def add_disabled(d):
        b=d.copy()
        b['disabled'] = True
        return b
    static_ = {k: add_disabled(v) for (k,v) in list(static_data.items())}
    result.update(static_)

    result['order_'] = list(fields.keys())
        
    return result

class DjanxFormSetMixin(object):

    @classmethod
    def from_json(cls, data, initial_forms=0, *args, **kwargs):
        """
        Takes a list of forms derived from JSON as the data object and converts
        into the prefix style expected by the FormSet constructor

        Note - the initial_forms argument is important! 
        """
        flatdata = {}
        prefix = kwargs['prefix'] if 'prefix' in kwargs else cls.get_default_prefix()
        for (i,formobj) in enumerate(data):
            flatdata.update({('%s-%d-%s' % (prefix, i, k)): v for (k,v) in list(formobj.items())})

        flatdata['%s-TOTAL_FORMS'%prefix] = len(data)
        flatdata['%s-INITIAL_FORMS'%prefix] = initial_forms
        return cls(flatdata, *args, **kwargs)


    def get_schema(self):
        """
        Returns a JSON representation of the django model.
        """
        management_form = self.management_form

        form_schema = {}
        for (fname, formfield) in list(self.form.base_fields.items()):

            field_schema = get_formfield_schema(formfield)
            field_schema['name'] = fname
            form_schema[fname] = field_schema

        return {'prefix': self.prefix, 'form': form_schema, 
                'fields': list(self.form.base_fields.keys()),
                'total_forms': self.total_form_count(),
                'initial_forms': self.initial_form_count(), 
                'max_num_forms': self.max_num, 'min_num_forms': self.min_num ,
                'type_': 'formset'}

class DjanxModelFormSet(DjanxFormSetMixin, djforms.BaseModelFormSet):
    pass

class DjanxInlineFormSet(DjanxFormSetMixin, djforms.BaseInlineFormSet):
    pass

class DjanxFormSet(DjanxFormSetMixin, djforms.BaseModelFormSet):
    pass

def get_formfield_schema(formfield):

    result = {'class': formfield.__class__.__name__}

    for attr in ('help_text', 'disabled', 'label', 'label_suffix', 'initial', 
            'required', 'max_value', 'min_value', 'max_length'):
        try:
            result[attr] = getattr(formfield, attr)
        except AttributeError:
            pass

    if hasattr(formfield, 'choices') and formfield.choices:
        result['choices'] = [{'pk': t[0], 'text': t[1]} for t in formfield.choices]
        #{'pk': m.pk, 'text': str(m)} 
                #for m in formfield.queryset]
    result['type_'] = 'field'
    return result

######################################
# Djanx versions of builtin form fields
######################################

class DateField(djforms.DateField):
    def strptime(self, value, format):
        return dateutil.parser.parse(value).date()

    #def value_to_string(self, obj):
    #    print "VALUE TO STRING!!!"
    #    dt = self.value_from_object(obj)
    #    return timezone.utc.localize(timezone.datetime(dt.year, dt.month, dt.day)).isoformat()

class InvalidJSONInput(six.text_type):
    pass


class JSONString(six.text_type):
    pass

class JSONField(jsonb.JSONField):
    """
    Taken from :
    https://github.com/django/django/blob/master/django/contrib/postgres/forms/jsonb.py 
    on the master branch.  Properly handles the case when the 
    data is already an object (dict etc) instead of a string.
    As of 16 Jan 2017 this is still not in a release.  Once it is we should be
    able to start using the built-in JSONField.
    """

    default_error_messages = {
        'invalid': _("'%(value)s' value must be valid JSON."),
    }
    widget = djforms.Textarea

    def to_python(self, value):
        if self.disabled:
            return value
        if value in self.empty_values:
            return None
        elif isinstance(value, (list, dict, int, float, JSONString)):
            return value
        try:
            converted = json.loads(value)
        except ValueError:
            raise djforms.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )
        if isinstance(converted, six.text_type):
            return JSONString(converted)
        else:
            return converted

    def bound_data(self, data, initial):
        if self.disabled:
            return initial
        try:
            return json.loads(data)
        except ValueError:
            return InvalidJSONInput(data)

    def prepare_value(self, value):
        if isinstance(value, InvalidJSONInput):
            return value
        return json.dumps(value)
