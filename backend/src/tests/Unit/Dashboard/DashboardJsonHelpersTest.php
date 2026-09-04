<?php

namespace Tests\Unit\Dashboard;

use App\Services\Dashboards\DashboardContentService;
use PHPUnit\Framework\TestCase;
use ReflectionMethod;

/**
 * Characterization tests for the two pure helpers that feed DashboardContentService::apply
 * (GDTIS-PT01-COD-075). They are the part of that method's NPath (358 512) that can be pinned with no
 * database at all, so they run in milliseconds and stay useful even when the DB is unavailable.
 *
 * These document CURRENT behaviour, including the sharp edges. They were the safety net for the
 * refactor that split that method into DashboardContentService — if a behaviour asserted here
 * changes, the refactor changed semantics, which is exactly what must not happen silently.
 *
 * Both helpers are `private static`, so they are reached by reflection on purpose: the point is to
 * pin behaviour BEFORE the code is reshaped, not to endorse the visibility.
 */
class DashboardJsonHelpersTest extends TestCase
{
    private static function call(string $method, array $args)
    {
        $ref = new ReflectionMethod(DashboardContentService::class, $method);
        $ref->setAccessible(true);

        return $ref->invokeArgs(null, $args);
    }

    private static function remap($node, array $keyToId)
    {
        return self::call('remapDashboardRefs', [$node, $keyToId]);
    }

    private static function strip(array $serie): array
    {
        return self::call('stripSerieIds', [$serie]);
    }

    // ------------------------------------------------------------------ remapDashboardRefs

    public function test_a_known_at_key_is_replaced_by_the_real_id(): void
    {
        $this->assertSame(42, self::remap('@traffic', ['traffic' => 42]));
    }

    public function test_an_unknown_at_key_is_left_untouched(): void
    {
        // No entry in the map: the literal string survives. A dashboard referencing a sibling that
        // was not part of the batch keeps the raw "@key" rather than becoming null.
        $this->assertSame('@missing', self::remap('@missing', ['traffic' => 42]));
    }

    public function test_replacement_is_recursive_through_nested_arrays(): void
    {
        $config = [
            'type' => 'Map',
            'popup' => [
                'entityDashboards' => ['@air', '@traffic', 'literal'],
                'deep' => ['deeper' => ['@air']],
            ],
        ];

        $this->assertSame(
            [
                'type' => 'Map',
                'popup' => [
                    'entityDashboards' => [7, 42, 'literal'],
                    'deep' => ['deeper' => [7]],
                ],
            ],
            self::remap($config, ['air' => 7, 'traffic' => 42])
        );
    }

    public function test_array_keys_are_preserved_and_not_remapped(): void
    {
        // Only VALUES are remapped; a key that happens to look like "@air" stays as a key.
        $this->assertSame(
            ['@air' => 7],
            self::remap(['@air' => '@air'], ['air' => 7])
        );
    }

    public function test_a_bare_at_sign_is_not_a_reference(): void
    {
        // strlen($node) > 1 guards this: "@" alone is left alone even if "" were a map key.
        $this->assertSame('@', self::remap('@', ['' => 99]));
    }

    public function test_non_string_scalars_pass_through_unchanged(): void
    {
        $this->assertSame(5, self::remap(5, ['a' => 1]));
        $this->assertNull(self::remap(null, ['a' => 1]));
        $this->assertTrue(self::remap(true, ['a' => 1]));
        $this->assertSame('plain', self::remap('plain', ['a' => 1]));
        // An email-like value does not start with "@", so it is safe.
        $this->assertSame('user@example.test', self::remap('user@example.test', ['a' => 1]));
    }

    public function test_an_empty_map_changes_nothing(): void
    {
        $config = ['a' => '@x', 'b' => ['@y']];
        $this->assertSame($config, self::remap($config, []));
    }

    /**
     * Sharp edge, pinned deliberately: the replacement value is whatever the map holds, and the map
     * is built from Dashboard::create()->id, so the "@key" string becomes an INT. Anything
     * downstream comparing it with === against a string id will not match.
     */
    public function test_the_substituted_value_keeps_the_maps_type(): void
    {
        $this->assertSame(42, self::remap('@k', ['k' => 42]));
        $this->assertSame('42', self::remap('@k', ['k' => '42']));
    }

    // ------------------------------------------------------------------ stripSerieIds

    public function test_the_serie_id_is_removed(): void
    {
        $this->assertSame(
            ['name' => 'temperature'],
            self::strip(['id' => 11, 'name' => 'temperature'])
        );
    }

    public function test_stripping_a_serie_without_an_id_is_a_no_op(): void
    {
        $this->assertSame(['name' => 'temperature'], self::strip(['name' => 'temperature']));
    }

    public function test_ids_are_stripped_recursively_from_dimensions(): void
    {
        $serie = [
            'id' => 1,
            'name' => 'outer',
            'dimensions' => [
                ['id' => 2, 'name' => 'inner'],
                ['id' => 3, 'name' => 'inner2', 'dimensions' => [['id' => 4, 'name' => 'deep']]],
            ],
        ];

        $this->assertSame(
            [
                'name' => 'outer',
                'dimensions' => [
                    ['name' => 'inner'],
                    ['name' => 'inner2', 'dimensions' => [['name' => 'deep']]],
                ],
            ],
            self::strip($serie)
        );
    }

    public function test_a_non_array_dimensions_value_is_left_alone(): void
    {
        // The `is_array` guard means a malformed payload does not explode here; it is passed on
        // to PanelRepository unchanged.
        $this->assertSame(
            ['name' => 'x', 'dimensions' => 'not-an-array'],
            self::strip(['id' => 9, 'name' => 'x', 'dimensions' => 'not-an-array'])
        );
    }

    public function test_every_other_key_survives_stripping(): void
    {
        $serie = [
            'id' => 1,
            'name' => 'temperature',
            'entity_id' => 55,
            'aggregation' => 'avg',
            'style' => ['color' => '#fff'],
        ];

        $stripped = self::strip($serie);

        unset($serie['id']);
        $this->assertSame($serie, $stripped);
    }
}
