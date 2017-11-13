/*
 * Directive that dynamically chooses an input type based on the info provided
 * from the backend on data required for a form.
 */

angular.module('djanx').directive('djanxFormField', function() {
  return {
    restrict: 'E',
    //transclude: true,
    scope: {
        schema: '=',
        suffix: '@',
        prefix: '@',
        inputType: '@?',
        ngRequired: '<',
        ngDisabled: '<',
        ngMin: '<',
        ngMax: '<',
        ngMinlength: '<',
        ngMaxlength: '<',
        ngChange: '&?',
        ngModel: '=',
        radioGroup: '<',
        labelClasses: '<',
        controlClasses: '<',
        controlDivClasses: '<',
    },
    link: function(scope, elt, attrs) {

    },
    controllerAs: 'ctrl',
    bindToController: true,
    controller: ['$scope', '$rootScope', function($scope, $rootScope) {
        var self = this;

        $scope.$watch(function() {return self.ngModel;}, function() {
            if(self.ngModel === undefined && self.schema !== undefined)
                self.ngModel = self.schema.initial;
        });

        self.onChange = function() {
            /* Problem! This may fire before the two way binding of ngModel to the 
             * parent is updated, so the parent may see an old value here.*/
            if(self.radioGroup)
                $rootScope.$broadcast('radio-group-changed', 
                        {radioGroup: self.radioGroup, newVal: self.ngModel, 
                            scopeId: $scope.$id});
            if(self.ngChange) {
                self.ngChange({newval: self.ngModel});
            }
        };

        $scope.$on('radio-group-changed', function(event, args) {
            if(args.scopeId != $scope.$id && args.radioGroup == self.radioGroup 
                    && args.newVal)
                self.ngModel = false;
        });


        self.getName = function() {
            if(self.schema)
                return (self.prefix || '') + self.schema.name + (self.suffix || '');
        };

        self.getClass = function() {
            if(self.schema) {
                if(self.schema.choices !== undefined)
                    return "Choice";
                else
                    return self.schema.class;
            }
        };

        
        // Attributes set on the directive override the schema.
        self.getRequired = function() { return self.ngRequired === undefined 
            ? self.schema &&  self.schema.required : self.ngRequired};
        self.getDisabled = function() { return self.ngDisabled === undefined 
            ? self.schema &&  self.schema.disabled : self.ngDisabled};
        self.getMin = function() {return self.ngMin === undefined 
            ? self.schema &&  self.schema.max_value : self.ngMin};
        self.getMax = function() {return self.ngMax === undefined 
            ? self.schema &&  self.schema.min_value : self.ngMax};
        self.getMaxlength = function() {return self.ngMaxlength === undefined 
            ? self.schema &&  self.schema.max_length : self.ngMaxlength};
        self.getMinlength = function() {return self.ngMinlength === undefined 
            ? self.schema &&  self.schema.min_length : self.ngMinlength};

    }],
    // TODO: fix Static Files behavior
    templateUrl: '/static/djanx/partials/djanx_form_field.html'
  }
});


angular.module('djanx').directive('jsonField', function() {
  return {
    restrict: 'A', // only activate on element attribute
    require: 'ngModel', // get a hold of NgModelController
    link: function(scope, element, attrs, ngModelCtrl) {

      var lastValid;

      // push() if faster than unshift(), and avail. in IE8 and earlier (unshift isn't)
      ngModelCtrl.$parsers.push(fromUser);
      ngModelCtrl.$formatters.push(toUser);

      // clear any invalid changes on blur
      element.bind('blur', function() {
        element.val(toUser(scope.$eval(attrs.ngModel)));
      });

      // $watch(attrs.ngModel) wouldn't work if this directive created a new scope;
      // see http://stackoverflow.com/questions/14693052/watch-ngmodel-from-inside-directive-using-isolate-scope how to do it then
      scope.$watch(attrs.ngModel, function(newValue, oldValue) {
        lastValid = lastValid || newValue;

        if (newValue != oldValue) {
          ngModelCtrl.$setViewValue(toUser(newValue));

          // TODO avoid this causing the focus of the input to be lost..
          ngModelCtrl.$render();
        }
      }, true); // MUST use objectEquality (true) here, for some reason..

      function fromUser(text) {
        // Beware: trim() is not available in old browsers
        if (!text || text.trim() === '') {
          return {};
        } else {
          try {
            lastValid = angular.fromJson(text);
            ngModelCtrl.$setValidity('invalidJson', true);
          } catch (e) {
            ngModelCtrl.$setValidity('invalidJson', false);
          }
          return lastValid;
        }
      }

      function toUser(object) {
        // better than JSON.stringify(), because it formats + filters $$hashKey etc.
        return angular.toJson(object, true);
      }
    }
  };
});
