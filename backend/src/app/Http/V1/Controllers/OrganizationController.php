<?php

namespace App\Http\V1\Controllers;

use App\Models\Organization;
use App\Models\Preference;
use App\Repositories\FiwareTenantScopeRepository;
use Illuminate\Http\Request;
use App\Http\V1\Controllers\Controller;
use App\Http\V1\Resources\OrganizationResource;
use App\Models\User;
use App\Traits\KeycloakHelper;
use App\Authorization\HasResourcePermissions;
use App\Repositories\OrganizationRepository;
use App\Authorization\AppResourcePermission;
use App\Helpers\ImagePreferenceHelper;
use App\Helpers\PreferenceValidator;
use App\Models\FiwareScope;
use App\Helpers\UserLocaleSyncHelper;
use App\Helpers\ServiceProvisioningHelper;
use App\Helpers\MfaRoleSyncHelper;
use App\Services\UserDeletion\UserDeletionService;


class OrganizationController extends Controller
{
    public function __construct(
        private readonly UserDeletionService $deletionService
    ) {}


    use KeycloakHelper;
    use HasResourcePermissions;

    public function show(int $id)
    {
        $organization = Organization::findOrFail($id);

        $this->authorize('read', $organization);

        return response(new OrganizationResource($organization), 200);
    }

    public function getPreferences(int $id)
    {
        $organization = Organization::findOrFail($id);

        $this->authorize('read', $organization);

        $preferences = $organization->preferences;

        $keyValuePreferences = [];
        foreach ($preferences as $preference) {
            $keyValuePreferences[$preference->name] = $preference->pivot->value;
        }

        $defaultPreferences = Preference::all();
        foreach ($defaultPreferences as $defaultPreference) {
            if (!array_key_exists($defaultPreference->name, $keyValuePreferences)) {
                $keyValuePreferences[$defaultPreference->name] = $defaultPreference->default_value;
            }
        }

        return response($keyValuePreferences, 200);
    }

    public function getPreference(int $id, string $preferenceName)
    {
        $organization = Organization::findOrFail($id);

        $this->authorize('read', $organization);

        $preference = $organization->preferences->where('name', $preferenceName)->first();

        if (!$preference) {
            $preference = Preference::where('name', $preferenceName)->first();
            if (!$preference) {
                return response('The provided preference is not configurable', 404);
            }
        }

        return response([
            'name' => $preference->name,
            'value' => $preference->value || $preference->default_value,
            'real-value' => $preference->pivot?->value ?? $preference->default_value,
        ], 200);
    }

    public function getPreferencesByOrganizationId(int $id)
    {
        $organization = Organization::where('id', $id)->first();

        if (!$organization) {
            return response('Organization not found', 404);
        }

        $allowedPreferences = [
            // Icons
            'themeLightIcon',
            'themeDarkIcon',
            'themeLoginIcon',

            // Language
            'language',

            //Theme
            'displayskinMode',

            // Colors
            "lightThemePrimaryColor",
            "darkThemeLightPrimaryColor",
            "darkThemePrimaryColor",
            "lightThemeLightPrimaryColor",
            "themePrimaryColor",
            "darkThemeSecondaryColor",
        ];

        $preferences = $organization->preferences;

        $keyValuePreferences = [];
        foreach ($preferences as $preference) {
            if (!in_array($preference->name, $allowedPreferences)) {
                continue;
            }
            $keyValuePreferences[$preference->name] = $preference->pivot->value;
        }

        $defaultPreferences = Preference::all();
        foreach ($defaultPreferences as $defaultPreference) {
            if (!array_key_exists($defaultPreference->name, $keyValuePreferences) && in_array($defaultPreference->name, $allowedPreferences)) {
                $keyValuePreferences[$defaultPreference->name] = $defaultPreference->default_value;
            }
        }

        return response($keyValuePreferences, 200);
    }

    public function getPreferenceByOrganizationId(int $id, string $preferenceName)
    {
        $allowedPreferences = [
            // Icons
            'themeLightIcon',
            'themeDarkIcon',
            'themeLoginIcon',

            // Language
            'language',

            //Theme
            'displayskinMode',

            // Colors
            "lightThemePrimaryColor",
            "darkThemeLightPrimaryColor",
            "darkThemePrimaryColor",
            "lightThemeLightPrimaryColor",
            "themePrimaryColor",
            "darkThemeSecondaryColor",
        ];

        if (!in_array($preferenceName, $allowedPreferences)) {
            return response('The provided preference is not retrievable', 404);
        }

        $organization = Organization::where('id', $id)->firstOrFail();

        $preference = $organization->preferences->where('name', $preferenceName)->first();

        if (!$preference) {
            $preference = Preference::where('name', $preferenceName)->first();
            if (!$preference) {
                return response('The provided preference is not configurable', 404);
            }
        }

        return response([
            'name' => $preference->name,
            'value' => $preference->value || $preference->default_value,
        ], 200);
    }

    /**
     * Serve an image-bearing organization preference (a theme icon) as an actual image.
     *
     * The Keycloak login theme needs the organization's image before any session exists, and it runs
     * on a different origin: a cross-origin fetch of the JSON endpoints above is blocked, because the
     * CORS allowlist only ever contains frontend origins (config/cors.php, never '*'). An <img> or a
     * CSS url() is not subject to CORS, so the stored value — a base64 data URI, see
     * ImagePreferenceHelper — is decoded and returned as bytes here. This also keeps megabytes of
     * base64 out of the login page and lets the browser cache the image.
     *
     * Unauthenticated by design, mounted next to the public /preferences endpoints, which already
     * expose these same values.
     */
    public function getPreferenceImageByOrganizationId(int $id, string $preferenceName, Request $request)
    {
        if (!ImagePreferenceHelper::isImagePreference($preferenceName)) {
            return response('The provided preference is not an image', 404);
        }

        $organization = Organization::where('id', $id)->firstOrFail();

        $preference = $organization->preferences->where('name', $preferenceName)->first();
        $value = $preference?->pivot?->value
            ?? Preference::where('name', $preferenceName)->first()?->default_value;

        if (!$value || !preg_match('#^data:image/[a-z+.-]+;base64,(.+)$#is', trim($value), $matches)) {
            return response('', 404);
        }

        $binary = base64_decode($matches[1], true);
        if ($binary === false || $binary === '') {
            return response('', 404);
        }

        // Content type taken from the decoded bytes, never from the label inside the data URI.
        $mime = (new \finfo(FILEINFO_MIME_TYPE))->buffer($binary);
        if (!is_string($mime) || !str_starts_with($mime, 'image/')) {
            return response('', 404);
        }

        // ETag over the stored value, so a re-upload invalidates immediately, while the short max-age
        // keeps the login page from hitting the API on every single load.
        $etag = '"' . sha1($value) . '"';
        $cacheHeaders = ['ETag' => $etag, 'Cache-Control' => 'public, max-age=300'];

        if (trim((string) $request->header('If-None-Match')) === $etag) {
            return response('', 304, $cacheHeaders);
        }

        return response($binary, 200, $cacheHeaders + [
            'Content-Type' => $mime,
            'Content-Length' => strlen($binary),
        ]);
    }

    public function updatePreference(int $id, string $preferenceName, Request $request)
    {
        $organization = Organization::findOrFail($id);

        $this->authorize('update', $organization);

        $validation = PreferenceValidator::validate($preferenceName, $request->value);
        if (!$validation['valid']) {
            return response($validation['error'] ?? 'Invalid preference value', 422);
        }

        $value = $validation['value'];

        $preference = $organization->preferences->where('name', $preferenceName)->first();

        // If the preference is not assigned to the organization, add it
        if (!$preference) {
            $preference = Preference::where('name', $preferenceName)->first();

            if (!$preference) {
                return response('The provided preference is not configurable', 404);
            }

            $organization->preferences()->attach($preference->id, ['value' => $value]);
        } else {
            $organization->preferences()->updateExistingPivot($preference->id, ['value' => $value]);
        }

        if ($preferenceName === 'activeMFA') {
            $mfaHelper = new MfaRoleSyncHelper();
            $mfaHelper->syncOrganizationMfaRole($organization, $request->value === 'true');
        }

        // Re-sync the Keycloak locale of org users that inherit the org language preference.
        if ($preferenceName === 'language') {
            (new UserLocaleSyncHelper())->syncOrganizationLocale($organization);
        }

        return response('Preference updated', 204);
    }

    public function deletePreference(int $id, string $preferenceName)
    {
        $organization = Organization::findOrFail($id);

        $this->authorize('update', $organization);

        $preference = $organization->preferences->where('name', $preferenceName)->first();

        if (!$preference) {
            return response('Preference was not configured for the organization', 204);
        }

        $organization->preferences()->detach($preference->id);

        if ($preferenceName === 'activeMFA') {
            $mfaHelper = new MfaRoleSyncHelper();
            $mfaHelper->syncOrganizationMfaRole($organization, false);
        }

        // Org language removed: inheriting users fall back to the default, re-sync their locale.
        if ($preferenceName === 'language') {
            (new UserLocaleSyncHelper())->syncOrganizationLocale($organization);
        }

        return response('Preference deleted', 204);
    }

    private function normalizeName(string $name): string
    {

        $name = strtolower($name);
        $name = str_replace(' ', '_', $name);
        $name = preg_replace('/[^A-Za-z0-9_]/', '', $name);

        // due to max length of 52 characters in fiware
        // we have to limit the tenant name to 44 characters
        $maxLength = 44;
        $words = explode('_', $name);

        $name = '';
        foreach ($words as $word) {
            if (strlen($name) + strlen($word) >= $maxLength) {
                break;
            }
            if ($name == '') {
                $name = $word;
                continue;
            }
            $name .= '_' . $word;
        }

        return $name;
    }

    /**
     * This setups the fiware scopes for the organization. This is:
     *
     *  - The organization has a mainScope:
     *    - Tenant: <organization name>
     *    - Scope: /
     *
     *  - And a dedicated platform data scope:
     *    - Tenant: <organization name>_platform
     *    - Scope: /
     *
     * This creates the scopes and gives permissions to the organization admin.
     *
     * @param \App\Models\Organization $organization
     * @param \App\Models\User $organizationAdmin
     * @return void
     */
    public function setupOrganizationFiwareScopes(Organization $organization): void
    {
        $normalizedOrganizationName = $this->normalizeName($organization->name);

        // main tenant
        $mainScope = $this->createTenantScopeForOrganization(
            $normalizedOrganizationName,
            '/',
            $organization->adminUser,
            'mainScope'
        );

        // platform data tenant
        $dataScope = $this->createTenantScopeForOrganization(
            $normalizedOrganizationName . '_platform',
            '/',
            $organization->adminUser,
            'platformDataScope'
        );

        ServiceProvisioningHelper::provisionAndSubscribe($organization, $mainScope, $dataScope);
    }

    /**
     * Normalizes a tenant slug: lowercase, spaces to underscores and only
     * alphanumeric/underscore characters (no length restriction here, the
     * combined name + slug length is validated by the caller).
     */
    private function createTenantScopeForOrganization(
        string $tenantName,
        string $scopeName,
        User $organizationAdmin,
        ?string $preferenceName = null
    ): FiwareScope {
        $FiwareScope = FiwareTenantScopeRepository::createScope(
            strtolower($tenantName),
            strtolower($scopeName)
        );

        // Give permissions to the organization admin over the tenant
        $defaultPermissions = AppResourcePermission::defaultPermissions();
        $organizationAdmin->giveResourcePermissionsTo(
            $defaultPermissions,
            $FiwareScope->tenant
        );

        // assign tenant to organization, the scope is not needed
        // (because it belongs to the tenant)
        OrganizationRepository::assignResourceToOrganization(
            $organizationAdmin->organization_id,
            $FiwareScope->tenant
        );

        // The canonical scopes (mainScope/platformDataScope) are tracked as
        // single-valued organization preferences. Extra tenants (e.g. slug
        // based ones) must not overwrite those, so the preference is optional.
        if ($preferenceName !== null) {
            $preference = Preference::where('name', $preferenceName)->firstOrFail();

            $organizationAdmin->organization->preferences()
                ->attach($preference->id, ['value' => $FiwareScope->id]);
        }

        return $FiwareScope;
    }
}
