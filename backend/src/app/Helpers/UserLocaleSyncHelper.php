<?php

namespace App\Helpers;

use App\Models\Organization;
use App\Models\Preference;
use App\Models\Preferencable;
use App\Models\User;
use App\Repositories\PreferenceRepository;
use App\Traits\KeycloakHelper;
use Illuminate\Support\Facades\Log;

/**
 * Mirrors a user's effective language (user preference -> organization preference ->
 * default) into the Keycloak `locale` user attribute.
 */
class UserLocaleSyncHelper
{
    use KeycloakHelper;

    /**
     * Resolve the user's effective language and push it to Keycloak.
     */
    public function syncUserLocale(User $user): bool
    {
        if (empty($user->keycloak_client_id)) {
            Log::warning('locale.sync.user.skip', [
                'user_id' => $user->id,
                'reason' => 'No keycloak_client_id',
            ]);
            return false;
        }

        $language = PreferenceRepository::getUserPreference($user, 'language');
        $locale = $this->normalizeLocale($language);

        if ($locale === null) {
            Log::warning('locale.sync.user.skip', [
                'user_id' => $user->id,
                'reason' => 'Unsupported language',
                'language' => $language,
            ]);
            return false;
        }

        return $this->setUserLocale($user->keycloak_client_id, $locale);
    }

    /**
     * Re-sync every user of the organization that does NOT have a personal language
     * preference (those users inherit the organization value). Users with their own
     * language preference are left untouched.
     */
    public function syncOrganizationLocale(Organization $organization): void
    {
        $preference = Preference::where('name', 'language')->first();
        if (!$preference) {
            return;
        }

        $users = $organization->users()->whereNotNull('keycloak_client_id')->get();

        foreach ($users as $user) {
            if ($this->userHasOwnLanguagePreference($user, $preference->id)) {
                continue;
            }
            $this->syncUserLocale($user);
        }
    }

    private function userHasOwnLanguagePreference(User $user, int $languagePreferenceId): bool
    {
        $pref = Preferencable::where('user_id', $user->id)
            ->where('preference_id', $languagePreferenceId)
            ->first();

        return $pref !== null && $pref->value !== null && trim((string) $pref->value) !== '';
    }

    /**
     * Map a platform language value to a Keycloak supported locale, or null if unsupported.
     */
private function normalizeLocale(?string $language): ?string
{
    $code = strtolower(trim((string) $language));
    return in_array($code, ['es','en','ca','el','pt'], true) ? $code : null;
}
}
