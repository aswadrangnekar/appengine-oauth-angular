'use strict';

portalApp.controller('MainController',
    function MainController($scope, $location, Conf, PortalApi) {
        $scope.isSignedIn = false;
        $scope.immediateFailed = true;

        $scope.signIn = function (authResult) {
            $scope.$apply(function() {
                $scope.processAuth(authResult);
            })
        }

        $scope.signedIn = function (profile) {
            $scope.isSignedIn = true;
            $scope.userProfile = profile;
        };

        $scope.processAuth = function(authResult) {
            $scope.immediateFailed = true;
            if ($scope.isSignedIn) {
                return 0;
            }
            if (authResult['access_token']) {
                $scope.immediateFailed = false;

                // Successfully authorized. Create a session
                PortalApi.signIn(authResult).then(function(response) {
                    $scope.signedIn(response.data);
                });
            } else if (authResult['error']) {
                if (authResult['error'] == 'immediate_failed') {
                    $scope.immediateFailed = true;
                }
            }
        }

        $scope.renderSignIn = function() {
            gapi.signin.render('myGsignin', {
                'callback': $scope.signIn,
            'clientid': Conf.clientId,
            'requestvisibleactions': Conf.requestvisibleactions,
            'scope': Conf.scopes,
            'apppackagename': Conf.apppackagename,
            'theme': 'dark',
            'cookiepolicy': Conf.cookiepolicy,
            'accesstype': 'offline'
            });
        }

        $scope.disconnect = function() {
            PortalApi.disconnect().then(function() {
                $scope.isSignedIn = false;
                $scope.immediateFailed = true;
            });
        }

        $scope.renderSignIn();
    }
);