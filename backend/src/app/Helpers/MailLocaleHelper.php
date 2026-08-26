<?php

namespace App\Helpers;

use App\Models\Organization;
use App\Models\User;
use App\Repositories\PreferenceRepository;

/**
 * Resolves the locale a transactional email must be rendered in.
 *
 * The language comes from the existing `language` preference (the value the apps' language selector
 * writes, resolved by PreferenceRepository as user -> organization -> seeded default). It is
 * normalized and whitelisted here because the preference is stored as a free scalar
 * (PreferenceValidator has no enum for it), so the stored value can be empty, mixed case or a full
 * BCP-47 tag such as `es-ES`.
 *
 * Pass the result to `Mail::to(...)->locale($code)` (or `$mailable->locale($code)`) so the mailable's
 * build() — and therefore the subject too — renders under that locale.
 */
class MailLocaleHelper
{
    /**
     * Locales the transactional emails are translated into: exactly the set the platform ships
     * (lang/{en,es,ca,pt,el}.json here, the same five bundles as the frontend i18n and the same
     * whitelist as UserLocaleSyncHelper). English is the default and the fallback.
     */
    private const SUPPORTED_LOCALES = ['en', 'es', 'ca', 'pt', 'el'];

    /** Default/fallback locale, matching config('app.locale') and config('app.fallback_locale'). */
    private const DEFAULT_LOCALE = 'en';

    /**
     * Mail locale for a recipient user. Never throws: any failure (missing `language` preference row,
     * user without organization, DB error) yields the default locale.
     */
    public static function forUser(?User $user): string
    {
        if (!$user) {
            return self::DEFAULT_LOCALE;
        }

        try {
            return self::normalize(PreferenceRepository::getUserPreference($user, 'language'));
        } catch (\Throwable $e) {
            return self::DEFAULT_LOCALE;
        }
    }

    /**
     * Mail locale for an organization. Used when the recipients are not users of the platform (e.g.
     * the arbitrary addresses configured in `criticalAlertConfig`), so there is no per-user language.
     * Never throws.
     */
    public static function forOrganization(?Organization $organization): string
    {
        if (!$organization) {
            return self::DEFAULT_LOCALE;
        }

        try {
            return self::normalize(PreferenceRepository::getOrganizationPreference($organization, 'language'));
        } catch (\Throwable $e) {
            return self::DEFAULT_LOCALE;
        }
    }

    /**
     * Trim, lowercase and keep only the primary subtag ('es-ES' -> 'es'); return the default locale
     * when the result is not one we translate the emails into.
     */
    private static function normalize(?string $language): string
    {
        $code = strtolower(trim((string) $language));
        $code = preg_split('/[-_]/', $code)[0] ?? '';

        return in_array($code, self::SUPPORTED_LOCALES, true) ? $code : self::DEFAULT_LOCALE;
    }
}
