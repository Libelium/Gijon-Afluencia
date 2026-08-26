<?php

namespace App\Services\PushNotifications;

/** A notification as it reaches the handset: text already in the recipient's language, plus the
 *  flat data bag the app uses to route the tap. */
class PushNotificationMessage
{
    /**
     * @param string $title Visible title, already translated.
     * @param string $body  Visible body, already translated (may be empty).
     * @param array<string, string> $data Flat string map — see below.
     */
    public function __construct(
        public readonly string $title,
        public readonly string $body,
        public readonly array $data = [],
    ) {
    }

    /**
     * FCM's `data` is a Map<String, String>: nested objects are rejected. So the payload is FLAT —
     * `['ref' => 'OC-2026-2468893']`, never `['params' => ['ref' => ...]]`. The app accepts both
     * shapes on purpose (`src/services/push.ts` → `PushPayload`).
     *
     * @param array<string, mixed> $params
     * @return array<string, string>
     */
    public static function flattenParams(array $params): array
    {
        $data = [];
        foreach ($params as $key => $value) {
            if ($value === null || is_array($value) || is_object($value)) {
                continue;
            }
            $data[(string) $key] = (string) $value;
        }

        return $data;
    }
}
