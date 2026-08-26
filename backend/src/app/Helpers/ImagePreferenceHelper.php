<?php

namespace App\Helpers;

/**
 * Validates image-bearing organization preferences (theme icons) before they
 * are stored, rejecting SVG / non-image data URIs that could carry stored XSS
 * (pentest hallazgo 5.2.4).
 */
class ImagePreferenceHelper
{
    /**
     * Preferences whose value must be a safe raster-image data URI (theme icons).
     *
     * @var string[]
     */
    private const IMAGE_PREFERENCES = [
        'themeDarkIcon',
        'themeLightIcon',
        'themeLoginIcon',
    ];

    /**
     * Raster image MIME types accepted for icon preferences.
     *
     * @var string[]
     */
    private const ALLOWED_MIME_TYPES = [
        'image/png',
        'image/jpeg',
        'image/webp',
        'image/gif',
    ];

    /**
     * Whether the given preference name must hold a (safe) image data URI.
     */
    public static function isImagePreference(string $preferenceName): bool
    {
        return in_array($preferenceName, self::IMAGE_PREFERENCES, true);
    }

    /**
     * Whether the value is a safe raster-image data URI.
     *
     * Rejects SVG and any non-image payload (e.g. "data:image/svg+xml,<svg>
     * <script>…</script></svg>"). An empty value (clearing the icon) is allowed.
     * The real content type is verified from the decoded magic bytes, so a forged
     * MIME label is caught.
     */
    public static function isSafeImageDataUri(?string $value): bool
    {
        if ($value === null || trim($value) === '') {
            return true;
        }

        if (!preg_match('#^data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=\s]+)$#', $value, $matches)) {
            return false;
        }

        $binary = base64_decode($matches[2], true);
        if ($binary === false || $binary === '') {
            return false;
        }

        // Confirm the real type from magic bytes (defeats SVG/script polyglots).
        $realMime = (new \finfo(FILEINFO_MIME_TYPE))->buffer($binary);

        return in_array($realMime, self::ALLOWED_MIME_TYPES, true);
    }
}
