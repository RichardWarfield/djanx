
angular.module('djanx').factory('djanx', ['$sce', function($sce) {
    var djanx = {
        decode: function(serverValues, schema, inplace) {
            /*
             * Handle dates
             */
            if(!inplace)
                var result = angular.copy(serverValues);
            else
                var result = serverValues;

            for(var field in schema) {
                if(schema[field].class == "DateField" && result[field])
                    result[field] = moment.utc(result[field]).toDate();
            }
            return result;
        },

        describeErrors: function(formErrors, loc) {
            /*
             * Describe the formErrors that come from the Django backend for a form group
             */
            var errString = '';

            if(typeof formErrors == 'string'){
                errString += "<div>Error in " + loc + ": " + formErrors + "</div>";
            } else if(angular.isArray(formErrors)) {
                formErrors.forEach(function(item, idx) {
                    errString += '\n'+ djanx.describeErrors(item, loc);
                });
            } else if(angular.isObject(formErrors)) {
                for(var subfield in formErrors) {
                    if(loc)
                        errString += '\n' + djanx.describeErrors(formErrors[subfield], loc + " > " + subfield);
                    else
                        errString += '\n' + djanx.describeErrors(formErrors[subfield], subfield);
                }
            }
            return $sce.trustAsHtml(errString);

        }

    };

    return djanx;
}]);

console.log("Loaded!");





