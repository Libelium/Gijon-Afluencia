<?php

namespace App\Services\PushNotifications;

use App\Models\PushNotificationToken;
use App\Models\User;
use App\Repositories\PreferenceRepository;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

/**
 * Turns "notify user X" into a push task on the queue.
 *
 * Split of responsibilities: web-back resolves the recipient's devices, language and final text —
 * all of which need the users/preferences database and lang/ — and hands the queues-consumer a
 * ready-to-deliver message. The consumer only talks to FCM/APNs, so the i18n lives in exactly one
 * place and nothing is duplicated in Python.
 *
 * Delivery is asynchronous on purpose: FCM needs one HTTP call per token, and doing that inline
 * would put Google's latency inside the request that changed the incident — a status cascade over an
 * intervention's member incidents could then run past the gateway timeout, after the change was
 * already committed.
 *
 * Called from NotificationHelper::push(), so push is a second channel for notifications the platform already
 * sends, not a new event source. Alarms (written straight to user_notifications by the consumer) are
 * deliberately out of scope.
 *
 * Task contract — `platform.push-notifications.send`, consumed by queues-consumer:
 *   {platform: 'ios'|'android', bundle_id: string, tokens: string[], title: string, body: string,
 *    data: {k: string}}
 * The consumer is responsible for pruning tokens that the transport reports as permanently dead.
 */
class PushNotificationDispatcher
{
    /** Languages with a file in lang/. */
    private const SUPPORTED_LOCALES = ['ca', 'el', 'en', 'es', 'pt'];

    private const MAX_TOKENS_PER_USER = 10;

    /** Memoised: localeFor() is ~5 queries and fan-outs repeat recipients. */
    private static array $localeCache = [];

    /**
     * @param string $title    i18n key (e.g. `notifications.incidentStatus`).
     * @param string $subtitle i18n key OR literal text — see resolveSubtitle().
     * @param array<string, mixed> $params Placeholders for the text AND the tap-routing data.
     */
    public function dispatch(int $userId, string $title, string $subtitle, array $params = []): void
    {
        if (!config('services.push-notifications.enabled')) {
            return;
        }

        $tokens = PushNotificationToken::where('user_id', $userId)
            ->orderByDesc('last_seen_at')
            ->limit(self::MAX_TOKENS_PER_USER)
            ->get();

        if ($tokens->isEmpty()) {
            return;
        }

        $locale = $this->localeFor($userId);
        $placeholders = $this->translationPlaceholders($params);

        $message = new PushNotificationMessage(
            $this->translate($title, $placeholders, $locale),
            $this->resolveSubtitle($subtitle, $placeholders, $locale),
            PushNotificationMessage::flattenParams($params),
        );

        // One task per platform AND bundle id. Platform because the transports differ and the consumer
        // picks its adapter from it. Bundle id because APNs carries it per send as `apns-topic`, and
        // white-label means one bundle id per instance — a mixed batch could not name a single topic.
        $groups = $tokens->groupBy(fn ($token) => $token->platform . '|' . $token->bundle_id);

        foreach ($groups as $group) {
            $this->publish(
                (string) $group->first()->platform,
                (string) $group->first()->bundle_id,
                $group->pluck('token')->all(),
                $message,
            );
        }
    }

    /**
     * @param string[] $tokens
     */
    private function publish(string $platform, string $bundleId, array $tokens, PushNotificationMessage $message): void
    {
        $endpoint = config('services.queues-consumer.publish');

        try {
            $response = Http::timeout(180)->post($endpoint, [
                'task' => 'platform.push-notifications.send',
                'params' => [
                    'platform' => $platform,
                    'bundle_id' => $bundleId,
                    'tokens' => $tokens,
                    'title' => $message->title,
                    'body' => $message->body,
                    'data' => (object) $message->data,
                ],
            ]);
        } catch (\Throwable $e) {
            Log::warning('[push-notifications] could not enqueue the push task: ' . $e->getMessage());

            return;
        }

        if ($response->status() >= 400) {
            Log::warning('[push-notifications] the queue rejected the push task (HTTP ' . $response->status() . ')');
        }
    }

    /**
     * The subtitle is an i18n key at most call sites but LITERAL USER CONTENT at others — a chat
     * excerpt goes straight through (`NotificationHelper::excerpt($body)`).
     *
     * Gating on the prefix, rather than on "did the lookup miss", avoids two misfires: Laravel
     * applies the placeholders to the key it returns on a miss, so a citizen writing ":ref" would
     * get the incident reference pasted into their own words; and a key present in en.json but not
     * in ca.json would be delivered raw, since JSON translations have no fallback chain.
     */
    private function resolveSubtitle(string $subtitle, array $placeholders, string $locale): string
    {
        if ($subtitle === '') {
            return '';
        }

        return str_starts_with($subtitle, 'notifications.')
            ? $this->translate($subtitle, $placeholders, $locale)
            : $subtitle;
    }

    /**
     * Falls back to English by hand: `trans()` looks a JSON key up in the requested locale only
     * (`fallback_locale` covers the PHP-array loader, not this one), so a key missing from ca.json
     * would otherwise reach the phone as the literal "notifications.incidentStatus".
     */
    private function translate(string $key, array $placeholders, string $locale): string
    {
        $translated = trans($key, $placeholders, $locale);

        if ($translated === $key && $locale !== 'en') {
            $translated = trans($key, $placeholders, 'en');
        }

        return is_string($translated) ? $translated : $key;
    }

    /**
     * The `:ref` / `:status` values `trans()` substitutes into the VISIBLE TEXT. Not to be confused
     * with PushNotificationMessage::flattenParams(), which builds the invisible `data` bag from the same
     * $params — and drops nulls instead of blanking them, because an empty value routes nothing.
     *
     * Everything is coerced to a string because trans() feeds these to strtr(): a null `status` or
     * `category` (both nullable at the call sites) raises a deprecation on PHP 8.1+, and an array
     * would land in the notification text as the literal "Array".
     *
     * @param array<string, mixed> $params
     * @return array<string, string>
     */
    private function translationPlaceholders(array $params): array
    {
        $placeholders = [];
        foreach ($params as $key => $value) {
            if (is_array($value) || is_object($value)) {
                continue;
            }
            $placeholders[(string) $key] = $value === null ? '' : (string) $value;
        }

        return $placeholders;
    }

    /**
     * Account preference → organization → platform default, a chain PreferenceRepository already
     * implements. The `locale` the device reports at registration is only a hint (token is per
     * device, preference is per user) and is deliberately unused.
     *
     * Normalised because nothing validates what was stored: a `pt-PT` would silently fall through.
     */
    private function localeFor(int $userId): string
    {
        return self::$localeCache[$userId] ??= $this->resolveLocale($userId);
    }

    private function resolveLocale(int $userId): string
    {
        $user = User::find($userId);
        if ($user === null) {
            return 'en';
        }

        try {
            $locale = PreferenceRepository::getUserPreference($user, 'language');
        } catch (\Throwable $e) {
            Log::warning('[push-notifications] could not resolve the language preference: ' . $e->getMessage());

            return 'en';
        }

        $locale = strtolower(substr((string) $locale, 0, 2));

        return in_array($locale, self::SUPPORTED_LOCALES, true) ? $locale : 'en';
    }
}
