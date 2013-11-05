'use strict';

portalApp.factory('PortalApi', function($http, Conf) {
   return {
       signIn: function(authResult) {
           return $http.post(Conf.apiBase + 'connect', authResult);
       },
       disconnect: function() {
           return $http.post(Conf.apiBase + 'disconnect');
       }
   };
});