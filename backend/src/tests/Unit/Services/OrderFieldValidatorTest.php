<?php

namespace Tests\Unit\Services;

use App\Services\OrderFieldValidator;
use PHPUnit\Framework\TestCase;

/**
 * The entity listing used to read `orderDirection` by truthiness, so "asc" sorted descending and
 * the table could not offer an ascending order. These pin how the direction and the column are
 * resolved now. Pure functions: no database needed.
 */
class OrderFieldValidatorTest extends TestCase
{
    private const ENTITY_COLUMNS = ['id', 'urn', 'datamodel', 'tenant', 'scope'];

    public function test_a_direction_string_is_read_by_its_value(): void
    {
        $this->assertSame('asc', OrderFieldValidator::resolveDirection('asc'));
        $this->assertSame('desc', OrderFieldValidator::resolveDirection('desc'));
        $this->assertSame('desc', OrderFieldValidator::resolveDirection(' DESC '));
    }

    public function test_the_legacy_boolean_flag_still_means_true_for_desc(): void
    {
        $this->assertSame('desc', OrderFieldValidator::resolveDirection(true));
        $this->assertSame('asc', OrderFieldValidator::resolveDirection(false));
        $this->assertSame('desc', OrderFieldValidator::resolveDirection(1));
        $this->assertSame('asc', OrderFieldValidator::resolveDirection(0));
    }

    public function test_anything_else_falls_back_to_asc(): void
    {
        $this->assertSame('asc', OrderFieldValidator::resolveDirection(null));
        $this->assertSame('asc', OrderFieldValidator::resolveDirection(''));
        $this->assertSame('asc', OrderFieldValidator::resolveDirection('sideways'));
    }

    public function test_an_offered_column_is_qualified_with_its_table(): void
    {
        $this->assertSame(
            'entities.datamodel',
            OrderFieldValidator::resolveColumn('datamodel', self::ENTITY_COLUMNS, 'entities.id', 'entities')
        );
        $this->assertSame(
            'entities.tenant',
            OrderFieldValidator::resolveColumn('entities.tenant', self::ENTITY_COLUMNS, 'entities.id', 'entities')
        );
    }

    public function test_a_column_the_listing_does_not_offer_falls_back_to_the_default(): void
    {
        $this->assertSame(
            'entities.id',
            OrderFieldValidator::resolveColumn('password', self::ENTITY_COLUMNS, 'entities.id', 'entities')
        );
        $this->assertSame(
            'entities.id',
            OrderFieldValidator::resolveColumn(null, self::ENTITY_COLUMNS, 'entities.id', 'entities')
        );
    }
}
