<?php

namespace App\Services;

/**
 * Whitelist for the `orderBy` / `orderDirection` parameters of the paginated listings.
 *
 * The order column arrives straight from the request. It is NOT a SQL injection vector — the
 * query grammar quotes the identifier, so a hostile value ends as a PostgreSQL 42703 error and
 * never as executed SQL — but an unbounded value still lets a caller
 *
 *   - probe the schema by watching which names error and which do not (an error oracle, worse
 *     when APP_DEBUG is on), and
 *   - force sorts on unindexed expressions on large tables.
 *
 * Both disappear once the caller can only name a column the listing actually offers.
 *
 * Rejecting is deliberately silent: ordering is a presentation detail, and a listing that fails
 * because of a stray query parameter is worse than one that falls back to its default order.
 */
class OrderFieldValidator
{
    /**
     * Resolves a requested order column against a whitelist of bare column names.
     *
     * A qualified name (`entities.urn`) is accepted and normalised, so callers that already pass
     * the table prefix keep working.
     *
     * @param string|null $requested The column asked for by the caller.
     * @param array $allowed Whitelist of bare column names.
     * @param string $default Column used when $requested is missing or not allowed.
     * @param string|null $tablePrefix Table to qualify the result with, if the query needs it.
     * @return string A column name that is safe to hand to orderBy().
     */
    public static function resolveColumn(
        ?string $requested,
        array $allowed,
        string $default,
        ?string $tablePrefix = null
    ): string {
        $requested = trim((string) $requested);

        $bare = str_contains($requested, '.')
            ? substr(strrchr($requested, '.'), 1)
            : $requested;

        if ($bare === '' || !in_array($bare, $allowed, true)) {
            return $default;
        }

        return $tablePrefix ? $tablePrefix . '.' . $bare : $bare;
    }

    /**
     * Resolves the sort direction. Only asc and desc exist; anything else becomes asc.
     */
    public static function resolveDirection(?string $requested): string
    {
        return strtolower(trim((string) $requested)) === 'desc' ? 'desc' : 'asc';
    }
}
