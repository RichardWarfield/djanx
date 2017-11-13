import json
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from django.http.response import HttpResponseBadRequest
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.views.generic import TemplateView

from common.decorators import wrap_exceptions

from .form_group import FormGroup

import logging
logger = logging.getLogger(__name__)

class BaseFormGroupView(TemplateView):
    """
    Provides sensible default behavior for a form view for a FormGroup.

    Define the following variables on the class and you should be good to go:

        id_variable
        noun
        form
        create_if_no_id
        change_permission_name
    """

    # Defaults
    create_if_no_id = False
    change_permission_name = None

    @wrap_exceptions(response_class=JsonResponse)
    def get(self, request, *args, **kwargs):
        obj_id = request.GET.get(self.id_variable, None)

        if obj_id:
            # Fill in the initial data
            try:
                obj = self.form.Meta.model.objects.get(id=obj_id)
            except ObjectDoesNotExist:
                logging.error("%s got request for id %s which does not exist" % 
                        (self.__class__.__name__, obj_id))
                raise ObjectDoesNotExist("%s %s does not exist" % (self.noun, obj_id))
        else:
            if self.create_if_no_id:
                obj = None
            else:
                raise ObjectDoesNotExist("No %s id given" % self.noun.lower())

        form_group = FormGroup(self.form)

        contents, schema, order = form_group.serialize(obj)

        return JsonResponse({'contents': contents, 'schema': schema, 'order': order},
                status=200)

    @wrap_exceptions(response_class=JsonResponse)
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        Create or modify the object

        If successful, response contains a success message.

        If failed, response contains a dictionary mapping field names to errors.
        """
        if not request.is_ajax():
            return HttpResponseBadRequest('Expected an XMLHttpRequest')

        if self.change_permission_name:
            if not request.user or not request.user.has_perm(self.change_permission_name):

                raise PermissionDenied("Sorry, you are not permitted to add or change a %s"
                        % self.__class__.__name__)

        in_data = json.loads(request.body)
        logger.info("in_data: %s" % in_data)

        form_group = FormGroup(self.form)
        form_group.deserialize(in_data)

        if form_group.is_valid():
            obj = form_group.save(commit=True)
            self.post_save(obj)
            message = "Saved %s" % self.noun.lower()
            return JsonResponse({'message': message, 'id': obj.id}, status=200)
        else:
            logger.error(form_group.errors)
            return JsonResponse({'form_errors': form_group.errors}, status=400)

    def post_save(self, obj):
        """
        Hook for sub classes.
        """
        pass

