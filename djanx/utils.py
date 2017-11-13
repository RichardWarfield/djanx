from itertools import chain
from django.db import models
from django.db.models.fields import DateField
import dateutil.parser

def model_to_dict(instance, fields=None, exclude=None,
        recurse={}):
    """
    Returns a dict containing the data in ``instance`` suitable for serializing
    to JSON and sending to the Javascript front end.

    ``fields`` is an optional list of field names. If provided, only the named
    fields will be included in the returned dict.

    ``exclude`` is an optional list of field names. If provided, the named
    fields will be excluded from the returned dict, even if they are listed in
    the ``fields`` argument.
    """
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields):
        #if not getattr(f, 'editable', False):
            #continue
        if fields and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue

        if f.is_relation:
            if f.name in recurse:
                data[f.name] = model_to_dict(f.value_from_object(instance), 
                        fields=recurse[f.name].get('fields', None),
                        exclude=recurse[f.name].get('exclude', None),
                        recurse=recurse[f.name].get('recurse', {}))
            else:
                data[f.name] = f.value_from_object(instance)
        else:
            data[f.name] = f.value_from_object(instance)


    for f in opts.many_to_many:
        #if not getattr(f, 'editable', False):
            #continue
        if fields and f.name not in fields:
            continue
        if exclude and f.name in exclude:
            continue
        if f.name in recurse:
            data[f.name] = [model_to_dict(obj,
                    fields=recurse[f.name].get('fields', None),
                    exclude=recurse[f.name].get('exclude', None),
                    recurse=recurse[f.name].get('recurse', {}))
                    for obj in f.value_from_object(instance)]
        else:
            data[f.name] = [obj.pk for obj in f.value_from_object(instance)]

    return data

def dict_to_model(cls, data):
    """
    Create an instance of cls using the values in data.

    The main difference between this and just doing cls(**data) is that this
    function will check if each field is a relation and, if the value given
    is not a model, will set the _id field instead.

    Also will try to convert DateFields from (JS-style) strings.
    """
    opts = cls._meta
    mdata = {}
    for f in chain(opts.concrete_fields, opts.private_fields):
        try:
            val = data[f.name]
        except KeyError:
            continue

        if not getattr(f, 'editable', False):
            continue

        if f.is_relation and not isinstance(val, models.Model):
            mdata[f.name+"_id"] = val
        elif val and isinstance(f, DateField):
            mdata[f.name] = dateutil.parser.parse(val)
        else:
            mdata[f.name] = val

    return cls(**mdata)
