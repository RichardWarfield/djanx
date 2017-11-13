import itertools , collections
from django.core.exceptions import ValidationError

from .utils import model_to_dict

class FormGroup(object):
    """
    Convenience class for serializing and deserializing a group of forms consisting of 
    a main ModelForm, zero or more related ModelFormSets, and zero or more
    ModelForms related through a OneToOneField on the main form.
    """

    def __init__(self, form_class, formsets={}, inline_1to1={}):
        """
        Args:
            form_class (subclass of DjanxForm): the form class

            formsets (dict): mapping from type (DjanxModelFormSet subclass) to str. 
            str is the name of the ForeignKey field in the underlying model.

            inline_1to1 (dict): mapping from str to DjanxModelFormSet. key is the name 
            of the OneToOneField field in the model.
        """
        self.form_class = form_class
        self.formsets = formsets
        self.inline_1to1 = inline_1to1

    def serialize(self, obj=None, fs_querysets={}, field_overrides={}):
        """
        Args:
            obj (Model or None): if given, the model to serialize

            fs_querysets (dict): if given, mapping from type (DjanxModelFormSet subclass)
            to queryset.

            field_overrides (dict): if given, overrides to be applied to 
            attributes on fields in the main form.  Entries of the form:
            (field name, attribute) -> new value. For example:
            ('account', 'queryset': Account.objects.filter(...)

        Returns:
            tuple: content, schema, order.  
            content is a dict: field name -> value.  Empty if obj is not given.
            schema is a dict: field name -> Djanx schema (used in frontend)
            order is a list of field names in the order given by the field.
        """
        form_class = self.form_class
        formsets = self.formsets
        inline_1to1 = self.inline_1to1

        model = form_class._meta.model
        if obj:
            content = model_to_dict(obj)
        else:
            content = {}

        #if obj:
        #    obj['extra_values'] = obj=obj).extra_values(content)
        main_form = form_class(instance=obj)
        for ((fname, attrname), val) in list(field_overrides.items()):
            setattr(main_form.fields[fname], attrname, val)

        fs_instances = {fs(instance=obj, queryset=fs_querysets.get(fs, None)): fkey 
                for (fs, fkey) in list(self.formsets.items())}

        schema = main_form.get_schema() 
        #schema = form_class.get_base_schema()

        field_order = list(form_class._meta.fields)

        schema['formsets'] = collections.OrderedDict()
        content['formsets'] = collections.OrderedDict()
        for (fs_inst, other_model_field) in list(fs_instances.items()):
            other_model = fs_inst.form._meta.model
            reverse_lookup = other_model._meta.get_field(other_model_field).remote_field.name
            schema['formsets'][reverse_lookup] = fs_inst.get_schema()
            schema['formsets'][reverse_lookup]['_parent_key_field'] = other_model_field
            field_order.append(reverse_lookup)

            if obj:
                content['formsets'][reverse_lookup] = [model_to_dict(m) for m in fs_inst.queryset]
            else:
                content['formsets'][reverse_lookup] = []

        for (o2o_field, otherform) in list(inline_1to1.items()):
            schema[o2o_field] = otherform.get_schema()
            schema[o2o_field]['type_'] = 'one2one'
            field_order.append(o2o_field)

            if obj:
                try:
                    other_model = getattr(obj,o2o_field)
                except AttributeError:
                    other_model = None
                
                if other_model:
                    content[o2o_field] = model_to_dict(other_model)


        return content, schema, field_order

    def deserialize(self, in_data):
        """
        Consumes the values in in_data to populate the forms in preparation for validation.

        Args:
            in_data (dict): A dictionary mapping field names to values.  
            For formsets, the key is the reverse mapping name (excluding the _set suffix) 
            and value is a list of dicts for setting up the model with the ForeignKey.  
            For OneToOneFields, the key is the field name and value is a dict of values for
            the other model.
        """
        form_class = self.form_class
        formsets = self.formsets
        inline_1to1 = self.inline_1to1

        if 'id' in in_data:
            instance = form_class.Meta.model.objects.get(pk=in_data['id'])
        else:
            instance = None

        # After excluding the formset and o2o data, whatever remains should be the 
        # main form fields.
        main_form_fields = in_data.copy()

        self.bound_formsets = {} # Indexed by (reverse_lookup, other_model_field)
        for (formset, other_model_field) in list(formsets.items()):
            other_model = formset.form._meta.model
            reverse_lookup = other_model._meta.get_field(other_model_field).remote_field.name
            #import ipdb; ipdb.set_trace()
            if instance:
                initial_forms = formset.form._meta.model.objects.filter(**{other_model_field: instance.pk}).count()
            else:
                initial_forms = 0
            bfs = formset.from_json(in_data['formsets'][reverse_lookup], initial_forms=initial_forms, instance=instance)

            self.bound_formsets[reverse_lookup,other_model_field] = bfs

        self.o2o_forms = {}
        for (o2o_field, otherform_class) in list(inline_1to1.items()):
            other_model_class = otherform_class.Meta.model
            if o2o_field in in_data and in_data[o2o_field]:
                # It's a model specification; deserialize it.
                if 'id' in in_data[o2o_field]:
                    o2o_obj = other_model_class.objects.get(id=in_data[o2o_field]['id'])
                else:
                    o2o_obj = None
                o2o_form = otherform_class(in_data[o2o_field], initial=in_data[o2o_field], 
                        instance=o2o_obj)
                self.o2o_forms[o2o_field] = o2o_form
                del main_form_fields[o2o_field]
                
        self.main_form = form_class(main_form_fields, initial=main_form_fields, 
                instance=instance)


    def is_valid(self):
        return (self.main_form.is_valid() and all([f.is_valid() for f in list(self.o2o_forms.values())]) 
            and all([fs.is_valid() for fs in list(self.bound_formsets.values())]))

    @property
    def errors(self):
        form_errors = self.main_form.errors.copy()
        for f in list(self.o2o_forms.values()):
            form_errors[f] = f.errors

        for ((reverse_lookup,_), fs) in list(self.bound_formsets.items()):
            form_errors[reverse_lookup] = fs.errors

        return form_errors

    def save(self, commit=True):
        """
        Saves the models.

        Returns:
            tuple: (main_obj, fs_objs, o2o_objs)

            fs_objs is a dict mapping reverse lookup names to lists of related model
            instances.

            o2o_objs is a dict mapping the one-to-one field names in main_obj to related
            model instances.
        """
        if not self.is_valid():
            raise ValidationError("Form group did not pass validation")

        main_obj = self.main_form.save(commit=commit)

        o2o_objs = {}
        for (field,boundform) in list(self.o2o_forms.items()):
            o2o_obj = boundform.save(commit=True)
            setattr(main_obj, field, o2o_obj)
            o2o_objs[field] = o2o_obj

        if commit:
            main_obj.save()

        self.new_fs_objects = {}
        self.changed_fs_objects = {}
        self.deleted_fs_objects = {}
        for ((reverse_lookup, other_model_field), fs) in list(self.bound_formsets.items()):

            fs.instance = main_obj
            fs.save(commit=False)

            self.new_fs_objects[reverse_lookup] = fs.new_objects
            self.changed_fs_objects[reverse_lookup] = fs.changed_objects
            self.deleted_fs_objects[reverse_lookup] = fs.deleted_objects

            for fobj in fs.new_objects:
                setattr(fobj, other_model_field, main_obj)
                if commit:
                    fobj.save()

            for (fobj, changed_fields) in fs.changed_objects:
                setattr(fobj, other_model_field, main_obj)
                if commit:
                    fobj.save()

            if commit:
                for fobj in fs.deleted_objects:
                    fobj.delete()

        return main_obj
