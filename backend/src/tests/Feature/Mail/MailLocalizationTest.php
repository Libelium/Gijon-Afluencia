<?php

namespace Tests\Feature\Mail;

use App\Helpers\MailLocaleHelper;
use App\Models\Mail\PasswordChanged;
use App\Models\Mail\ResetPassword;
use App\Models\User;
use Tests\TestCase;

/**
 * Localisation of the transactional emails.
 *
 * Needs NO database: the translation files are read from disk and every mailable is rendered directly,
 * so this suite runs anywhere (no DatabaseTransactions, no seeded data).
 *
 * What it guards against — each of these has silently reached a user's inbox in similar projects:
 *   - a key missing from one locale (the email renders the raw key, or English text mid-Greek email);
 *   - a translator dropping or renaming a :placeholder (":name" printed literally, or a broken sentence);
 *   - the locale not actually being applied at render time (body translated, subject still English);
 *   - a key referenced in a template that does not exist in the translation files.
 *
 * ---------------------------------------------------------------------------------------------
 * NOTE ON SCOPE (GDTIS-PT01-FUN-018)
 * ---------------------------------------------------------------------------------------------
 * The previous version of this file referenced three mailable classes that do not exist anywhere
 * in the codebase — App\Models\Mail\AccountBlockedNotice, App\Models\Mail\AccountUnblockedNotice
 * and App\Models\Mail\CriticalIncidentAlert — plus their source paths. Every test that touched
 * them died with "Class not found", which is 13 of the suite's 17 original failures. (The audit
 * report only spotted AccountUnblockedNotice; all three are missing.)
 *
 * app/Models/Mail/ contains exactly two mailables: ResetPassword and PasswordChanged. The three
 * Blade views for the incident emails DO exist and ARE fully translated into the five locales,
 * but nothing in app/, routes/ or config/ ever renders them — see
 * test_incident_mail_views_have_no_mailable_yet(), which pins that fact so the dead code stays
 * visible and so that whoever adds the missing mailables is told to extend the render coverage
 * below.
 *
 * The data-level tests (key parity, placeholders, emptiness, whitelist) still cover ALL the
 * translation keys, including the incident ones, because they work from the Blade views and the
 * JSON files rather than from the mailable classes.
 */
class MailLocalizationTest extends TestCase
{
    /** The only locales the platform ships. Mirrors MailLocaleHelper::SUPPORTED_LOCALES. */
    private const LOCALES = ['en', 'es', 'ca', 'pt', 'el'];

    private const DEFAULT_LOCALE = 'en';

    /**
     * Templates + mailables that must only ever reference existing keys.
     *
     * All five Blade views are listed (they exist and are translated) even though three of them
     * have no mailable class yet; that is precisely how the incident translations keep being
     * validated. Only files that really exist may be listed here — a missing path is a hard
     * failure, which is what made this test obsolete before.
     */
    private const SOURCES = [
        'resources/views/app/account/mail/resetPassword.blade.php',
        'resources/views/app/account/mail/passwordChanged.blade.php',
        'resources/views/app/incidents/mail/criticalIncidentAlert.blade.php',
        'resources/views/app/incidents/mail/accountBlockedNotice.blade.php',
        'resources/views/app/incidents/mail/accountUnblockedNotice.blade.php',
        'app/Models/Mail/ResetPassword.php',
        'app/Models/Mail/PasswordChanged.php',
    ];

    /**
     * Blade views under resources/views/app/incidents/mail/ that are rendered by no mailable.
     * Keyed by view file, valued by the class that is expected to render it one day.
     */
    private const MAIL_VIEWS_WITHOUT_MAILABLE = [
        'resources/views/app/incidents/mail/criticalIncidentAlert.blade.php'   => 'App\Models\Mail\CriticalIncidentAlert',
        'resources/views/app/incidents/mail/accountBlockedNotice.blade.php'    => 'App\Models\Mail\AccountBlockedNotice',
        'resources/views/app/incidents/mail/accountUnblockedNotice.blade.php'  => 'App\Models\Mail\AccountUnblockedNotice',
    ];

    /** @return array<string, string> flat key => translation */
    private function translations(string $locale): array
    {
        $path = base_path("lang/{$locale}.json");
        $this->assertFileExists($path, "Missing translation file for locale '{$locale}'.");

        $decoded = json_decode(file_get_contents($path), true);
        $this->assertIsArray($decoded, "lang/{$locale}.json is not valid JSON.");

        return $decoded;
    }

    /** Placeholder names (":name", ":ref"…) used in a translation value. */
    private function placeholders(string $value): array
    {
        preg_match_all('/:([a-zA-Z]+)/', $value, $matches);
        $found = array_unique($matches[1]);
        sort($found);

        return $found;
    }

    // ---------------------------------------------------------------- data files

    public function test_every_locale_defines_exactly_the_same_keys(): void
    {
        $reference = array_keys($this->translations(self::DEFAULT_LOCALE));
        sort($reference);
        $this->assertNotEmpty($reference, 'The English translation file is empty.');

        foreach (self::LOCALES as $locale) {
            $keys = array_keys($this->translations($locale));
            sort($keys);

            $this->assertSame(
                $reference,
                $keys,
                "lang/{$locale}.json key set differs from English. Missing: "
                    . implode(', ', array_diff($reference, $keys))
                    . ' | Unexpected: ' . implode(', ', array_diff($keys, $reference))
            );
        }
    }

    public function test_no_translation_is_empty(): void
    {
        foreach (self::LOCALES as $locale) {
            foreach ($this->translations($locale) as $key => $value) {
                $this->assertIsString($value, "lang/{$locale}.json: '{$key}' is not a string.");
                $this->assertNotSame('', trim($value), "lang/{$locale}.json: '{$key}' is empty.");
            }
        }
    }

    public function test_translations_keep_the_same_placeholders_as_english(): void
    {
        $english = $this->translations(self::DEFAULT_LOCALE);

        foreach (self::LOCALES as $locale) {
            if ($locale === self::DEFAULT_LOCALE) {
                continue;
            }

            $translated = $this->translations($locale);

            foreach ($english as $key => $englishValue) {
                $this->assertSame(
                    $this->placeholders($englishValue),
                    $this->placeholders($translated[$key] ?? ''),
                    "lang/{$locale}.json: '{$key}' does not use the same placeholders as English. "
                        . 'A dropped or renamed placeholder ships a broken sentence.'
                );
            }
        }
    }

    public function test_every_key_referenced_in_code_exists_in_every_locale(): void
    {
        $used = [];
        foreach (self::SOURCES as $relative) {
            $path = base_path($relative);
            $this->assertFileExists($path, "{$relative} is listed in SOURCES but does not exist.");
            preg_match_all('/__\(\s*[\'"]([^\'"]+)[\'"]/', file_get_contents($path), $matches);
            foreach ($matches[1] as $key) {
                $used[$key] = $relative;
            }
        }

        $this->assertNotEmpty($used, 'No __() calls found — the templates are not localised at all.');

        foreach (self::LOCALES as $locale) {
            $available = $this->translations($locale);
            foreach ($used as $key => $source) {
                $this->assertArrayHasKey(
                    $key,
                    $available,
                    "'{$key}' is used in {$source} but missing from lang/{$locale}.json."
                );
            }
        }
    }

    /**
     * No translation key is dead weight: every `emails.*` key in the JSON files is referenced by
     * at least one of the sources above. Catches the opposite drift of the test before this one —
     * a template stops using a key and nobody removes it from five JSON files.
     */
    public function test_no_email_translation_key_is_unused(): void
    {
        $used = [];
        foreach (self::SOURCES as $relative) {
            preg_match_all('/__\(\s*[\'"]([^\'"]+)[\'"]/', file_get_contents(base_path($relative)), $matches);
            foreach ($matches[1] as $key) {
                $used[$key] = true;
            }
        }

        // Subjects are set in the mailables via __('...') too, but the three mailables that do not
        // exist yet cannot reference theirs — allow exactly those.
        $subjectsOfMissingMailables = [
            'emails.accountBlocked.subject',
            'emails.accountUnblocked.subject',
            'emails.criticalIncident.subject',
        ];

        $unused = [];
        foreach (array_keys($this->translations(self::DEFAULT_LOCALE)) as $key) {
            if (!str_starts_with($key, 'emails.')) {
                continue;
            }
            if (isset($used[$key]) || in_array($key, $subjectsOfMissingMailables, true)) {
                continue;
            }
            $unused[] = $key;
        }

        $this->assertSame(
            [],
            $unused,
            'These emails.* keys exist in lang/*.json but are referenced by no template or mailable: '
                . implode(', ', $unused)
        );
    }

    // ---------------------------------------------------------------- dead code tripwire

    /**
     * Pins the fact that three incident e-mail templates are fully translated but rendered by
     * nothing. This is NOT a desirable state — it is recorded so it cannot be forgotten, and so
     * that adding the mailable class turns this test red and points at the coverage that must be
     * added at the same time.
     */
    public function test_incident_mail_views_have_no_mailable_yet(): void
    {
        foreach (self::MAIL_VIEWS_WITHOUT_MAILABLE as $view => $expectedClass) {
            $this->assertFileExists(base_path($view), "{$view} disappeared; update this test.");

            $this->assertFalse(
                class_exists($expectedClass),
                "{$expectedClass} now exists. Good — but this test and the render coverage in "
                    . 'test_every_mailable_renders_in_the_given_locale() were written while it did not. '
                    . "Add it to mailables() so its subject and body are checked in all five locales, "
                    . "and remove it from MAIL_VIEWS_WITHOUT_MAILABLE."
            );
        }
    }

    // ---------------------------------------------------------------- locale resolution

    public function test_locale_helper_defaults_to_english_without_a_user(): void
    {
        // No database needed: a null target must short-circuit to the default locale.
        $this->assertSame(self::DEFAULT_LOCALE, MailLocaleHelper::forUser(null));
        $this->assertSame(self::DEFAULT_LOCALE, MailLocaleHelper::forOrganization(null));
    }

    // ---------------------------------------------------------------- rendering

    /**
     * Every mailable that EXISTS, in every locale: the body must contain that locale's
     * heading/intro and the subject must be that locale's subject. This is what proves the locale
     * is really applied — a regression here is the "translated body, English subject" bug.
     *
     * @dataProvider localeProvider
     */
    public function test_every_mailable_renders_in_the_given_locale(string $locale): void
    {
        $t = $this->translations($locale);

        foreach ($this->mailables($t) as [$mailable, $bodyKey, $expectedSubject]) {
            $class = get_class($mailable);

            $body = $mailable->locale($locale)->render();

            $this->assertStringContainsString(
                $this->visibleText($t[$bodyKey]),
                $this->visibleText($body),
                "{$class} rendered in '{$locale}' does not contain the '{$bodyKey}' translation."
            );

            $this->assertSame(
                $expectedSubject,
                $mailable->subject,
                "{$class} subject is not localised to '{$locale}'."
            );
        }
    }

    /**
     * The greeting interpolates the recipient's name. Assert the name actually lands in the body
     * and that no raw ":name" placeholder survives — in any locale.
     *
     * @dataProvider localeProvider
     */
    public function test_recipient_name_is_interpolated_and_no_placeholder_survives(string $locale): void
    {
        $body = (new PasswordChanged($this->recipient()))->locale($locale)->render();

        $this->assertStringContainsString('Ana Pérez', $body, "The recipient name is missing from the '{$locale}' email.");
        $this->assertStringNotContainsString(':name', $body, "A raw ':name' placeholder leaked into the '{$locale}' email.");
    }

    /** The reset link is rendered as the CTA href, in every locale. */
    public function test_reset_password_link_is_rendered(): void
    {
        $url = 'https://example.test/reset?token=abc123';

        foreach (self::LOCALES as $locale) {
            $body = (new ResetPassword($this->recipient(), $url))->locale($locale)->render();

            $this->assertStringContainsString(
                $url,
                html_entity_decode($body, ENT_QUOTES | ENT_HTML5, 'UTF-8'),
                "The reset URL is missing from the '{$locale}' email."
            );
        }
    }

    /**
     * The whitelist in MailLocaleHelper is the ONLY thing standing between a user and an email full
     * of raw translation keys.
     *
     * Why: Laravel's JSON translations do NOT fall back to `fallback_locale`. Translator::get() looks
     * up the flat key in the ('*','*') JSON store for the REQUESTED locale only; when there is no
     * lang/<locale>.json it drops to the group/file lookup ("emails" group), finds no
     * lang/<locale>/emails.php either, and returns the key itself. Rendering with an unsupported
     * locale therefore emails "emails.passwordChanged.body" to a person — verified below, so nobody
     * "simplifies" the helper by dropping the whitelist.
     *
     * The protection is that every locale the helper can return HAS a file, which is what this asserts.
     */
    public function test_supported_locales_all_have_a_translation_file(): void
    {
        $supported = (new \ReflectionClass(MailLocaleHelper::class))
            ->getConstant('SUPPORTED_LOCALES');

        $onDisk = array_map(
            fn (string $path) => basename($path, '.json'),
            glob(base_path('lang/*.json'))
        );

        sort($supported);
        sort($onDisk);

        $this->assertSame(
            $supported,
            $onDisk,
            'MailLocaleHelper::SUPPORTED_LOCALES and lang/*.json must match exactly. A locale in the '
                . 'whitelist without a file emails raw translation keys (JSON has no fallback); a file '
                . 'that is not whitelisted is dead weight.'
        );
        // Order is irrelevant — what matters is the set.
        $this->assertEqualsCanonicalizing(
            self::LOCALES,
            $supported,
            'The platform ships exactly these five locales.'
        );
    }

    /** Characterises the framework gap the whitelist exists for. */
    public function test_an_unwhitelisted_locale_would_render_raw_keys(): void
    {
        // 'fr' ships no lang/fr.json. This documents WHY MailLocaleHelper must never return it.
        $body = (new PasswordChanged($this->recipient()))->locale('fr')->render();

        $this->assertStringContainsString(
            'emails.passwordChanged.body',
            $body,
            'Laravel JSON translations are expected NOT to fall back to English. If this now falls back, '
                . 'the framework behaviour changed and the note on the whitelist can be relaxed.'
        );

        // And the guarantee that matters: the helper can only ever hand out a supported locale.
        $this->assertContains(MailLocaleHelper::forUser(null), self::LOCALES);
        $this->assertContains(MailLocaleHelper::forOrganization(null), self::LOCALES);
    }

    public static function localeProvider(): array
    {
        return array_combine(
            self::LOCALES,
            array_map(fn (string $l) => [$l], self::LOCALES)
        );
    }

    /**
     * The mailables that exist, as [mailable, body key that must appear, expected subject].
     *
     * @param array<string, string> $t translations for the locale under test
     * @return array<int, array{0: \Illuminate\Mail\Mailable, 1: string, 2: string}>
     */
    private function mailables(array $t): array
    {
        $user = $this->recipient();

        return [
            [new ResetPassword($user, 'https://example.test/reset'), 'emails.resetPassword.cta', $t['emails.resetPassword.subject']],
            [new PasswordChanged($user), 'emails.passwordChanged.body', $t['emails.passwordChanged.subject']],
        ];
    }

    /** An unsaved User — the mailables only read ->name, so no database is involved. */
    private function recipient(): User
    {
        return new User(['name' => 'Ana Pérez', 'email' => 'ana@example.test']);
    }

    /**
     * Normalise text for comparison: strips HTML tags (some translations embed <strong>) and collapses
     * whitespace, so an assertion is about the words and not about Blade's indentation.
     */
    private function visibleText(string $html): string
    {
        return trim(preg_replace('/\s+/', ' ', html_entity_decode(strip_tags($html), ENT_QUOTES | ENT_HTML5, 'UTF-8')));
    }
}
