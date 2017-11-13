

from django.db import models


class TestMainModel(models.Model):

    foo = models.TextField()
    o2o = models.OneToOneField("TestOneToOneModel", null=True)

class TestOneToOneModel(models.Model):
    bar = models.TextField()

class TestRelatedModel(models.Model):
    baz = models.TextField()
    main_model = models.ForeignKey("TestMainModel")
