<?php

namespace App\Services;

use Collator;

/**
 * Order of an entity listing by a key that lives in the realtime database (the entity's name or
 * the time of its latest reading), which the main query cannot ORDER BY: it is another database.
 *
 * Entities without a key always go last, in either direction, so a sensor that never reported
 * does not head a "latest data" listing. Ties are broken by id, in the same direction, so a page
 * never repeats or loses rows between requests.
 */
class RealtimeEntityOrder
{
    /**
     * @param array<int, array{id: int, key: string|null}> $rows
     * @param string $direction 'asc' or 'desc'
     * @param bool $asText true for names (compared as Spanish text, ignoring case and accents);
     *                     false for timestamps (ISO strings, compared as such)
     * @return int[] The ids in order.
     */
    public static function sort(array $rows, string $direction, bool $asText): array
    {
        $collator = $asText ? new Collator('es_ES') : null;
        $collator?->setStrength(Collator::PRIMARY);
        $sign = $direction === 'desc' ? -1 : 1;

        usort($rows, function (array $a, array $b) use ($collator, $sign) {
            $aMissing = $a['key'] === null || $a['key'] === '';
            $bMissing = $b['key'] === null || $b['key'] === '';
            if ($aMissing !== $bMissing) {
                return $aMissing ? 1 : -1;
            }
            $byKey = $aMissing ? 0 : ($collator ? $collator->compare($a['key'], $b['key']) : strcmp($a['key'], $b['key']));

            return $sign * ($byKey ?: $a['id'] <=> $b['id']);
        });

        return array_map(fn (array $row) => $row['id'], $rows);
    }
}
