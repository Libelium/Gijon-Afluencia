/* Per-organization parallax image, from the themeLoginIcon preference. Loaded as an image URL and
   not fetched as JSON, because the backend's CORS allowlist has no Keycloak origin. */
(function () {
    var ORG_STORAGE_KEY = 'kcOrganizationId';
    var PREFERENCE = 'themeLoginIcon';

    /* Validated: it goes into a URL path. */
    function isValidOrganizationId(value) {
        return typeof value === 'string' && /^[0-9]{1,10}$/.test(value);
    }

    function resolveOrganizationId() {
        var fromQuery = new URLSearchParams(window.location.search).get('organization');

        if (isValidOrganizationId(fromQuery)) {
            /* Cached: login-actions/* pages (failed login, register, email links) have no param. */
            try {
                localStorage.setItem(ORG_STORAGE_KEY, fromQuery);
            } catch (e) {
                /* Private mode. */
            }

            return fromQuery;
        }

        try {
            var cached = localStorage.getItem(ORG_STORAGE_KEY);

            return isValidOrganizationId(cached) ? cached : null;
        } catch (e) {
            return null;
        }
    }

    /* Some values files deploy BACKEND_URL with no scheme, or with a single slash ("https:/host"). */
    function normalizeBackendUrl(raw) {
        if (typeof raw !== 'string') {
            return null;
        }

        var url = raw.trim().replace(/\/+$/, '');
        if (!url || url.indexOf('__') === 0) {
            return null;
        }

        url = url.replace(/^(https?:)\/(?!\/)/i, '$1//');

        return /^https?:\/\//i.test(url) ? url : 'https://' + url;
    }

    /* Deferred because this script runs from <head>, before the element exists. */
    function applyLogo(url) {
        var apply = function () {
            var logo = document.querySelector('#main-logo img');

            if (logo) {
                logo.src = url;
            }
        };

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', apply);
        } else {
            apply();
        }
    }

    var organizationId = resolveOrganizationId();
    if (!organizationId) {
        return;
    }

    var backendUrl = normalizeBackendUrl(window.BACKEND_URL);
    if (!backendUrl) {
        return;
    }

    var imageUrl = backendUrl + '/api/V1/publicOrganizations/' + organizationId +
        '/preferences/' + PREFERENCE + '/image';

    /* Probed first so a 404 (organization with no image) leaves the default in place, not a broken
       image. Same cache entry, so not a second download. */
    var probe = new Image();

    probe.onload = function () {
        applyLogo(imageUrl);
    };
    probe.src = imageUrl;
})();
