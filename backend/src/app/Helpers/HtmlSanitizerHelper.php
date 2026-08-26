<?php

namespace App\Helpers;

/**
 * Sanitizes rich-text preference values (currently the theme custom footer)
 * before they are persisted, as a server-side defense-in-depth layer against
 * stored XSS (pentest hallazgo 5.1.1).
 *
 * The frontend additionally sanitizes the footer with DOMPurify at render time,
 * but client-side controls must never be treated as a security boundary, so the
 * value is also cleaned here — on the authoritative side — before storage.
 */
class HtmlSanitizerHelper
{
    /**
     * Names of preferences whose value is rich HTML and therefore must be
     * sanitized with an allowlist before being stored.
     *
     * @var string[]
     */
    private const HTML_PREFERENCES = [
        'themeCustomFooter',
    ];

    /**
     * HTMLPurifier allowlist for the footer. Keeps the formatting produced by
     * the CKEditor toolbar (text styles, headings, lists, links, images,
     * figures, tables, alignment) while dropping anything executable:
     * <script>, event handlers (onerror/onload/...) and dangerous URI schemes
     * (javascript:, ...) are removed. The data: scheme is allowed but handled by
     * HTMLPurifier's built-in data URI validator, which only accepts real raster
     * images (png/jpeg/gif verified from magic bytes) and rejects SVG or any
     * non-image payload — so CKEditor's base64-embedded images survive
     * sanitization while stored-XSS vectors do not.
     *
     * @var array<string, mixed>
     */
    private const FOOTER_PURIFIER_CONFIG = [
        'HTML.Allowed' =>
        'p,br,b,strong,i,em,u,s,sub,sup,'
            . 'h1,h2,h3,h4,h5,h6,blockquote,'
            . 'ul,ol,li,'
            . 'a[href|title|target|rel],'
            . 'span[style|class],div[style|class],'
            . 'figure[class|style],img[src|alt|width|height|style],'
            . 'table,thead,tbody,tr,td,th',
        'CSS.AllowedProperties' =>
        'width,height,text-align,aspect-ratio,float,'
            . 'color,background-color,font-weight,font-style,text-decoration',
        'URI.AllowedSchemes' => [
            'http' => true,
            'https' => true,
            'mailto' => true,
            'data' => true,
        ],
        'Attr.AllowedFrameTargets' => ['_blank'],
    ];

    /**
     * Whether the given preference name carries rich HTML that must be sanitized.
     */
    public static function isHtmlPreference(string $preferenceName): bool
    {
        return in_array($preferenceName, self::HTML_PREFERENCES, true);
    }

    /**
     * Sanitize the theme custom footer HTML.
     *
     * Uses HTMLPurifier (mews/purifier) when the package is available. Until it
     * is installed (`composer require mews/purifier`), it falls back to escaping
     * the value as plain text, which is always safe — no markup can execute.
     */
    public static function sanitizeFooter(?string $html): ?string
    {
        if ($html === null || trim($html) === '') {
            return $html;
        }

        $purifier = 'Mews\\Purifier\\Facades\\Purifier';

        if (class_exists($purifier)) {
            return $purifier::clean($html, self::FOOTER_PURIFIER_CONFIG);
        }

        // Safe fallback while the sanitizer package is not yet installed:
        // store the footer escaped so it can never be parsed as markup.
        return htmlspecialchars($html, ENT_QUOTES | ENT_HTML5, 'UTF-8');
    }
}
