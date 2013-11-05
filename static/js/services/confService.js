'use strict';

portalApp.factory('Conf', function($location) {
    function getRootUrl() {
        var rootUrl = $location.protocol() + '://' + $location.host();
        if ($location.port()) {
            rootUrl += ':' + $location.port();
        }
        return rootUrl;
    };
    return {
        'clientId': 'YOUR CLIENT ID',
        'apiBase': '/auth/',
        'rootUrl': getRootUrl(),
        'scopes': 'https://www.googleapis.com/auth/plus.login ',
        'requestvisibleactions': 'http://schemas.google.com/AddActivity ' +
            'http://schemas.google.com/ReviewActivity',
        'cookiepolicy': 'single_host_origin'
    };
});
