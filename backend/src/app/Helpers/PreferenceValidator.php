<?php

namespace App\Helpers;

/**
 * Central server-side validation for preference values (user and organization).
 *
 * Returns a result array: ['valid' => bool, 'value' => mixed, 'error' => ?string].
 * On success 'value' is the value to store (sanitized where applicable).
 */
class PreferenceValidator
{
    private const COLOR_PREFERENCES = [
        'themePrimaryColor',
        'themeSecondaryColor',
        'themeLightPrimaryColor',
        'lightThemePrimaryColor',
        'lightThemeSecondaryColor',
        'lightThemeLightPrimaryColor',
        'darkThemePrimaryColor',
        'darkThemeSecondaryColor',
        'darkThemeLightPrimaryColor',
    ];

    private const BOOLEAN_PREFERENCES = [
        'activeMFA',
        'accessLogEnabled',
        'subscriptionAutoSync',
        'exportDeviceProperties',
    ];

    private const INTEGER_PREFERENCES = [
        'numRecordsCharts',
        'maxAccessAttempts',
    ];

    private const MAX_SCALAR_LENGTH = 512;

    /**
     * @return array{valid: bool, value: mixed, error: ?string}
     */
    public static function validate(string $preferenceName, mixed $value): array
    {
        // HTML (footer) and theme icons have their own sanitization rules.
        $special = self::validateSpecialCases($preferenceName, $value);
        if ($special !== null) {
            return $special;
        }

        // Clearing any preference is always allowed.
        if ($value === null || (is_string($value) && trim($value) === '')) {
            return self::ok($value);
        }

        return self::validateByType($preferenceName, $value);
    }

    /**
     * Preferences whose validation does not follow the generic type rules.
     * Returns a result array, or null if no special case applies.
     */
    private static function validateSpecialCases(string $preferenceName, mixed $value): ?array
    {
        // Rich-text HTML (footer): sanitized with an allowlist, always returns a safe value.
        if (HtmlSanitizerHelper::isHtmlPreference($preferenceName)) {
            return self::ok(HtmlSanitizerHelper::sanitizeFooter($value));
        }

        // Theme icons: must be a safe raster-image data URI.
        if (ImagePreferenceHelper::isImagePreference($preferenceName)) {
            return self::result(
                ImagePreferenceHelper::isSafeImageDataUri($value),
                $value,
                'Invalid image for this preference'
            );
        }

        return null;
    }

    /**
     * Validates a non-empty value according to the preference's declared type,
     * falling back to a safe-scalar rule for anything unrecognized.
     */
    private static function validateByType(string $preferenceName, mixed $value): array
    {
        return match (self::typeOf($preferenceName)) {
            'color'   => self::result(self::isHexColor($value), $value, 'Invalid color value'),
            'boolean' => self::result(self::isValidBoolean($value), $value, 'Invalid boolean value'),
            'integer' => self::result(self::isIntegerLike($value), $value, 'Invalid numeric value'),
            'columns' => self::validateCustomColumns($value),
            'json'    => self::validateJsonArray($value),
            default   => self::validateSafeScalar($value),
        };
    }

    private static function typeOf(string $preferenceName): string
    {
        $groups = [
            'color'   => self::COLOR_PREFERENCES,
            'boolean' => self::BOOLEAN_PREFERENCES,
            'integer' => self::INTEGER_PREFERENCES,
        ];

        foreach ($groups as $type => $names) {
            if (in_array($preferenceName, $names, true)) {
                return $type;
            }
        }

        if ($preferenceName === 'devicesListCustomColumns') {
            return 'columns';
        }

        return $preferenceName === 'customModules' ? 'json' : 'scalar';
    }

    private static function ok(mixed $value): array
    {
        return ['valid' => true, 'value' => $value, 'error' => null];
    }

    private static function fail(string $message): array
    {
        return ['valid' => false, 'value' => null, 'error' => $message];
    }

    private static function result(bool $valid, mixed $value, string $error): array
    {
        return $valid ? self::ok($value) : self::fail($error);
    }

    private static function isValidBoolean(mixed $value): bool
    {
        return in_array($value, ['true', 'false', true, false], true);
    }

    private static function isHexColor(mixed $value): bool
    {
        return is_string($value) && preg_match('/^#[0-9A-Fa-f]{3,8}$/', $value) === 1;
    }

    private static function isIntegerLike(mixed $value): bool
    {
        return is_int($value) || (is_string($value) && preg_match('/^\d{1,9}$/', $value) === 1);
    }

    /**
     * Markup (angle brackets) or ASCII control chars (except tab/CR/LF) → unsafe.
     */
    private static function containsMarkupOrControl(string $value): bool
    {
        return preg_match('/[<>]/', $value) === 1
            || preg_match('/[\x00-\x08\x0B\x0C\x0E-\x1F]/', $value) === 1;
    }

    private static function validateSafeScalar(mixed $value): array
    {
        if (is_bool($value) || is_int($value) || is_float($value)) {
            return self::ok($value);
        }

        if (!is_string($value)) {
            return self::fail('Invalid preference value');
        }

        $error = self::scalarStringError($value);
        return $error === null ? self::ok($value) : self::fail($error);
    }

    /**
     * Validation error for a string scalar, or null when it is safe to store.
     */
    private static function scalarStringError(string $value): ?string
    {
        $checks = [
            [mb_strlen($value) > self::MAX_SCALAR_LENGTH, 'Preference value is too long'],
            [self::containsMarkupOrControl($value), 'Preference value contains invalid characters'],
        ];

        foreach ($checks as [$failed, $message]) {
            if ($failed) {
                return $message;
            }
        }

        return null;
    }

    /**
     * customModules is a JSON array of module configs (title, icon, path, url…).
     * It can legitimately exceed the scalar length limit, so it is validated as
     * structured JSON: it must decode to an array and no string value anywhere in
     * the structure may contain markup or control characters.
     */
    private static function validateJsonArray(mixed $value): array
    {
        $decoded = is_string($value) ? json_decode($value, true) : $value;

        if (!is_array($decoded)) {
            return self::fail('Invalid preference value');
        }

        return self::jsonContainsMarkup($decoded)
            ? self::fail('Preference value contains invalid characters')
            : self::ok($value);
    }

    /**
     * True if any string anywhere in the (possibly nested) structure contains
     * markup or control characters.
     */
    private static function jsonContainsMarkup(mixed $node): bool
    {
        if (is_string($node)) {
            return self::containsMarkupOrControl($node);
        }

        if (is_array($node)) {
            foreach ($node as $child) {
                if (self::jsonContainsMarkup($child)) {
                    return true;
                }
            }
        }

        return false;
    }

    /**
     * devicesListCustomColumns is a JSON array of column configs. No field may
     * contain markup, and each "command" must be a safe property identifier.
     */
    private static function validateCustomColumns(mixed $value): array
    {
        $decoded = is_string($value) ? json_decode($value, true) : $value;

        if (!is_array($decoded)) {
            return self::fail('Invalid devicesListCustomColumns value');
        }

        foreach ($decoded as $column) {
            $error = self::columnError($column);
            if ($error !== null) {
                return self::fail($error);
            }
        }

        return self::ok($value);
    }

    /**
     * Validation error for a single column config, or null when it is safe.
     */
    private static function columnError(mixed $column): ?string
    {
        if (!is_array($column) || self::columnHasMarkup($column)) {
            return 'Invalid column definition';
        }

        if (self::hasInvalidCommand($column)) {
            return 'Invalid column command';
        }

        return null;
    }

    private static function columnHasMarkup(array $column): bool
    {
        foreach ($column as $field) {
            if (is_string($field) && self::containsMarkupOrControl($field)) {
                return true;
            }
        }

        return false;
    }

    private static function hasInvalidCommand(array $column): bool
    {
        return isset($column['command']) && is_string($column['command'])
            && preg_match('/^[A-Za-z0-9_.\- :]+$/', $column['command']) !== 1;
    }
}
