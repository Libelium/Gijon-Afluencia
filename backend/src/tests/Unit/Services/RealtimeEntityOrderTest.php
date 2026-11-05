<?php

namespace Tests\Unit\Services;

use App\Services\RealtimeEntityOrder;
use PHPUnit\Framework\TestCase;

/**
 * The entity listing orders by name and by latest reading, two keys that live in the realtime
 * database. These pin that order: Spanish text for names, entities without a key last in either
 * direction, and the id as tie-breaker so a page is stable between requests. Pure function.
 */
class RealtimeEntityOrderTest extends TestCase
{
    private static function rows(array $keys): array
    {
        return array_map(fn ($id, $key) => ['id' => $id, 'key' => $key], array_keys($keys), $keys);
    }

    public function test_names_are_ordered_as_text_ignoring_case_and_accents(): void
    {
        $rows = self::rows([1 => 'Plaza Norte', 2 => 'ábside', 3 => 'Centro', 4 => 'barrio']);

        $this->assertSame([2, 4, 3, 1], RealtimeEntityOrder::sort($rows, 'asc', true));
        $this->assertSame([1, 3, 4, 2], RealtimeEntityOrder::sort($rows, 'desc', true));
    }

    public function test_the_ene_goes_after_the_n_as_in_a_spanish_dictionary(): void
    {
        $rows = self::rows([1 => 'Ñora', 2 => 'Oeste', 3 => 'Norte']);

        $this->assertSame([3, 1, 2], RealtimeEntityOrder::sort($rows, 'asc', true));
    }

    public function test_timestamps_are_ordered_in_time(): void
    {
        $rows = self::rows([
            1 => '2026-11-04 10:00:00',
            2 => '2026-11-04 12:00:00',
            3 => '2026-11-03 23:59:59',
        ]);

        $this->assertSame([3, 1, 2], RealtimeEntityOrder::sort($rows, 'asc', false));
        $this->assertSame([2, 1, 3], RealtimeEntityOrder::sort($rows, 'desc', false));
    }

    public function test_an_entity_without_a_key_goes_last_in_either_direction(): void
    {
        $rows = self::rows([1 => null, 2 => '2026-11-04 10:00:00', 3 => '', 4 => '2026-11-04 12:00:00']);

        $this->assertSame([2, 4, 1, 3], RealtimeEntityOrder::sort($rows, 'asc', false));
        $this->assertSame([4, 2, 3, 1], RealtimeEntityOrder::sort($rows, 'desc', false));
    }

    public function test_equal_keys_are_broken_by_id_in_the_same_direction(): void
    {
        $rows = self::rows([7 => 'Zona', 3 => 'zona', 5 => 'Zóna']);

        $this->assertSame([3, 5, 7], RealtimeEntityOrder::sort($rows, 'asc', true));
        $this->assertSame([7, 5, 3], RealtimeEntityOrder::sort($rows, 'desc', true));
    }
}
