<?php

namespace Tests\Feature;

use App\Authorization\AppResourcePermission;
use App\Enums\UserStatus;
use App\Models\Entity;
use App\Models\FiwareScope;
use App\Models\FiwareTenant;
use App\Models\Organization;
use App\Models\Realtime\EntityProperty;
use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseTransactions;
use Illuminate\Support\Str;
use Tests\TestCase;

/**
 * POST /api/V1/entities/paginate with `bounds`, the query of the map view. The location lives in
 * the realtime database as text, in Python or JSON quoting, and is read with regular expressions.
 */
class EntityBoundsFilterTest extends TestCase
{
    use DatabaseTransactions;

    protected $connectionsToTransact = ['pgsql', 'pgsql_realtime'];

    private User $user;
    private FiwareTenant $tenant;
    private FiwareScope $scope;

    /** The visible area of the tests: central Gijon. */
    private const BOUNDS = ['south' => 43.53, 'west' => -5.68, 'north' => 43.56, 'east' => -5.64];

    protected function setUp(): void
    {
        parent::setUp();

        $this->user = User::create([
            'name'               => '[TEST] Bounds',
            'email'              => 'bounds.' . strtolower(Str::random(8)) . '@bounds-test.local',
            'enabled'            => true,
            'status'             => UserStatus::Active,
            'keycloak_client_id' => 'test-kc-' . strtolower(Str::random(8)),
        ]);
        $organization = Organization::create(['name' => '[TEST] Bounds org ' . Str::random(6), 'admin' => $this->user->id]);
        $this->user->organization_id = $organization->id;
        $this->user->save();

        $this->tenant = FiwareTenant::create(['name' => 'test_bounds_' . strtolower(Str::random(6))]);
        $this->scope = FiwareScope::create(['name' => '/', 'fiware_tenant_id' => $this->tenant->id]);
        $this->user->giveResourcePermissionsTo([AppResourcePermission::READ], $this->tenant);
    }

    public function test_a_point_inside_the_area_is_listed_and_one_outside_is_not(): void
    {
        $this->entity('Inside', "{'type': 'Point', 'coordinates': [-5.6627, 43.5455]}");
        $this->entity('Outside', "{'type': 'Point', 'coordinates': [-3.7038, 40.4168]}");

        $this->assertSame(['Inside'], $this->listed());
    }

    public function test_a_polygon_zone_is_listed_by_its_first_vertex(): void
    {
        $this->entity(
            'Plaza',
            "{'type': 'Polygon', 'coordinates': [[[-5.6642, 43.5447], [-5.6612, 43.5449], [-5.6610, 43.5463], [-5.6642, 43.5447]]]}",
        );
        $this->entity(
            'Madrid',
            '{"type": "Polygon", "coordinates": [[[-3.70, 40.41], [-3.69, 40.41], [-3.69, 40.42], [-3.70, 40.41]]]}',
        );
        $this->entity(
            'Playa',
            '{"type": "Polygon", "coordinates": [[[-5.6600, 43.5418], [-5.6520, 43.5400], [-5.6515, 43.5385], [-5.6600, 43.5418]]]}',
        );

        $this->assertSame(['Playa', 'Plaza'], $this->listed());
    }

    public function test_a_location_that_is_not_a_geometry_is_left_out(): void
    {
        $this->entity('Text', 'Calle Corrida 1');

        $this->assertSame([], $this->listed());
    }

    // ----------------------------------------------------------------- helpers

    private function listed(): array
    {
        $response = $this->actingAs($this->user)->postJson('/api/V1/entities/paginate', [
            'bounds'         => self::BOUNDS,
            'tenant'         => $this->tenant->name,
            'orderBy'        => 'urn',
            'orderDirection' => 'asc',
            'paginationSize' => 50,
        ]);
        $response->assertOk();

        return array_map(fn (array $row) => substr(strrchr($row['urn'], ':'), 1), $response->json('rows'));
    }

    private function entity(string $tail, string $location): void
    {
        $entity = Entity::create([
            'urn'             => "urn:ngsi-ld:TestZone:{$tail}",
            'datamodel'       => 'TestZone',
            'tenant'          => $this->tenant->name,
            'scope'           => $this->scope->name,
            'fiware_scope_id' => $this->scope->id,
        ]);

        EntityProperty::create([
            'urn'       => $entity->urn,
            'tenant'    => $entity->tenant,
            'scope'     => $entity->scope,
            'entity_id' => $entity->id,
            'name'      => 'location',
            'value'     => $location,
            'units'     => '',
            'timestamp' => '2026-11-01 00:00:00',
        ]);
    }
}
