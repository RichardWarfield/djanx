from django.test import TestCase
from django import forms
from django.forms import ModelForm, modelform_factory, inlineformset_factory, modelformset_factory, BaseModelFormSet

from .form_group import FormGroup
from .models import *
from .forms import *

class MainModelForm(DjanxForm, forms.ModelForm):
    class Meta:
        model = TestMainModel
        fields=['foo']


class OneToOneModelForm(DjanxForm, forms.ModelForm):
    class Meta:
        model = TestOneToOneModel
        fields = ('bar',)

class RelatedModelForm(DjanxForm, forms.ModelForm):
    class Meta:
        model = TestRelatedModel
        fields = ('baz',)

RelatedModelFormSet = inlineformset_factory(TestMainModel, TestRelatedModel, form=RelatedModelForm,
        can_delete=True, formset=DjanxInlineFormSet)

class FormGroupTestCases(TestCase):

    def testUnboundForm(self):
        fg = FormGroup(MainModelForm)
        print((fg.serialize()))

    def testBoundForm(self):
        o2omodel = TestOneToOneModel.objects.create(bar='I am BAR')
        mmodel = TestMainModel.objects.create(foo='I am FOO', o2o=o2omodel)
        rel1 = TestRelatedModel.objects.create(main_model=mmodel, baz='I am BAZ')
        rel2 = TestRelatedModel.objects.create(main_model=mmodel, baz='I also am BAZ')
        fs = RelatedModelFormSet

        fg = FormGroup(MainModelForm, formsets={fs: 'main_model'},
                inline_1to1={'o2o': OneToOneModelForm()})
        content,schema,order = fg.serialize(mmodel)
        print(('content:', content))
        print(('schema:', schema))


    def testUnserializeNewObj(self):
        TestRelatedModel.objects.all().delete()
        in_data = {
                'o2o': {'bar': 'I am BAR'}, 
                'foo': 'I am FOO', 
                'formsets': {
                    'testrelatedmodel': [
                            {'baz': 'I am BAZ'}, 
                            {'baz': 'I also am BAZ'}
                        ], 
                    },
                #u'id': 84
            }
        fs = RelatedModelFormSet
        fg = FormGroup(MainModelForm, formsets={fs: 'main_model'},
                inline_1to1={'o2o': OneToOneModelForm})


        fg.deserialize(in_data)
        self.assertTrue(fg.is_valid())
        main_obj = fg.save(commit=True)

        self.assertEqual(main_obj.o2o.bar, 'I am BAR') 
        self.assertEqual(main_obj.testrelatedmodel_set.count(), 2) 
        self.assertTrue(all([fso.main_model == main_obj for fso in main_obj.testrelatedmodel_set.all()])) 

    def testUnserializeModObj(self):
        TestRelatedModel.objects.all().delete()
        o2omodel = TestOneToOneModel.objects.create(bar='I am BAR')
        mmodel = TestMainModel.objects.create(foo='I am FOO', o2o=o2omodel)
        rel1 = TestRelatedModel.objects.create(main_model=mmodel, baz='I am BAZ')
        rel2 = TestRelatedModel.objects.create(main_model=mmodel, baz='I also am BAZ')

        in_data = {
                'o2o': {'bar': 'I am BARRY', 'id': o2omodel.id}, 
                'foo': 'I am FOORY', 
                'id': mmodel.id,
                'formsets': {
                    'testrelatedmodel': [
                            {'baz': 'I am BAZRY', 'id': rel1.id}, 
                            {'baz': 'I also am BAZRY', 'id': rel2.id}
                        ], 
                    }
            }
        fs = RelatedModelFormSet
        fg = FormGroup(MainModelForm, formsets={fs: 'main_model'},
                inline_1to1={'o2o': OneToOneModelForm})


        fg.deserialize(in_data)
        self.assertTrue(fg.is_valid())
        main_obj = fg.save(commit=True)

        print(('NEW', fg.new_fs_objects))
        print(('CHANGED', fg.changed_fs_objects))
        self.assertEqual(main_obj, mmodel)
        self.assertEqual(main_obj.o2o, o2omodel) 
        self.assertEqual(main_obj.foo, 'I am FOORY')
        self.assertEqual(main_obj.o2o, o2omodel)
        self.assertEqual(main_obj.o2o.bar, 'I am BARRY')
        self.assertEqual(main_obj.testrelatedmodel_set.count(), 2) 
        self.assertTrue(all([fso.main_model == main_obj for fso in main_obj.testrelatedmodel_set.all()])) 
        

    def testUnserializeDelFormSetForm(self):
        TestRelatedModel.objects.all().delete()
        o2omodel = TestOneToOneModel.objects.create(bar='I am BAR')
        mmodel = TestMainModel.objects.create(foo='I am FOO', o2o=o2omodel)
        rel1 = TestRelatedModel.objects.create(main_model=mmodel, baz='I am BAZ')
        rel2 = TestRelatedModel.objects.create(main_model=mmodel, baz='I also am BAZ')

        in_data = {
                'o2o': {'bar': 'I am BARRY', 'id': o2omodel.id}, 
                'foo': 'I am FOORY', 
                'formsets': {
                    'testrelatedmodel': [
                            {'baz': 'I am BAZRY', 'id': rel1.id, 'DELETE': True}, 
                            {'baz': 'I also am BAZRY', 'id': rel2.id}
                        ], 
                    },
                'id': mmodel.id
            }
        fs = RelatedModelFormSet
        fg = FormGroup(MainModelForm, formsets={fs: 'main_model'},
                inline_1to1={'o2o': OneToOneModelForm})


        fg.deserialize(in_data)
        self.assertTrue(fg.is_valid())
        main_obj = fg.save(commit=True)

        self.assertEqual(main_obj.testrelatedmodel_set.count(), 1) 
        self.assertTrue(all([fso.main_model == main_obj for fso in main_obj.testrelatedmodel_set.all()])) 
