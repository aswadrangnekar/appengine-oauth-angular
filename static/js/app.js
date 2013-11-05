'use strict';

var portalApp = angular.module('portalApp', ['ngRoute']).
    config(['$routeProvider', '$locationProvider', function($routeProvider, $locationProvider) {
        $locationProvider.html5Mode(true);
    }]);