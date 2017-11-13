from django.shortcuts import render
import django.forms as djforms
from django.views.generic import TemplateView
from django.core.exceptions import ValidationError
from django.http import JsonResponse

class DjanxBaseModelFormView(TemplateView):

    def get(self, request, *args, **kwargs):
        """
        Return a description of the models that Angular can understand.
        """
        pass

    def post(self, request, *args, **kwargs):
        """
        Populate the form and validate.
        """
        if not request.is_ajax():
            return HttpResponseBadRequest('Expected an XMLHttpRequest')

        in_data = json.loads(request.body)

        logging.info(in_data)

        if validation_ok:
            response = {}

            return JsonResponse(response, status=200)
        else:
            response = {}

            return JsonResponse(response, status=400)

