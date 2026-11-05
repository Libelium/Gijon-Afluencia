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
 * POST /api/V1/entities/paginate ordered by `name` and by `last_data`. Both keys live in the
 * realtime database, so the listing orders them apart from its own query; these check that the
 * order, the page slice, the total and the permission filter survive that. The database rolls
 * back after each test.
 */
class EntityListingOrderTest extends TestCase
{
    use DatabaseTransactions;

    protected $connectionsToTransact = ['pgsql', 'pgsql_realtime'];

    private User $user;
    private FiwareTenant $tenant;
    private FiwareScope $scope;

    /** @var array<string, Entity> by URN tail */
    private array $entities = [];

    protected function setUp(): void
    {
        parent::setUp();

        $this->user = User::create([
            'name'               => '[TEST] Listing',
            'email'              => 'listing.' . strtolower(Str::random(8)) . '@order-test.local',
            'enabled'            => true,
            'status'             => UserStatus::Active,
            'keycloak_client_id' => 'test-kc-' . strtolower(Str::random(8)),
        ]);
        $organization = Organization::create(['name' => '[TEST] Order org ' . Str::random(6), 'admin' => $this->user->id]);
        $this->user->organization_id = $organization->id;
        $this->user->save();

        [$this->tenant, $this->scope] = $this->tenantWithRootScope();
        $this->user->giveResourcePermissionsTo([AppResourcePermission::READ], $this->tenant);

        // Named entities and two without a name, listed and ordered by their URN tail; Z09 has
        // no property at all, so it has no latest reading either.
        $this->entity('Z03', name: 'Plaza Norte', lastData: '2026-11-04 10:00:00');
        $this->entity('Z01', name: 'ábside', lastData: '2026-11-04 12:00:00');
        $this->entity('Z02', name: 'Centro', lastData: '2026-11-03 23:00:00');
        $this->entity('Barrio', name: null, lastData: '2026-11-04 11:00:00');
        $this->entity('Z09', name: null, lastData: null);
    }

    public function test_by_name_follows_the_name_shown_and_ignores_case_and_accents(): void
    {
        $this->assertSame(['Z01', 'Barrio', 'Z02', 'Z03', 'Z09'], $this->order('name', 'asc'));
        $this->assertSame(['Z09', 'Z03', 'Z02', 'Barrio', 'Z01'], $this->order('name', 'desc'));
    }

    public function test_by_last_data_follows_the_latest_reading_and_leaves_the_silent_one_last(): void
    {
        $this->assertSame(['Z01', 'Barrio', 'Z03', 'Z02', 'Z09'], $this->order('last_data', 'desc'));
        $this->assertSame(['Z02', 'Z03', 'Barrio', 'Z01', 'Z09'], $this->order('last_data', 'asc'));
    }

    public function test_a_page_is_a_slice_of_the_whole_order_and_the_count_is_the_total(): void
    {
        $response = $this->listing(['orderBy' => 'name', 'orderDirection' => 'asc', 'paginationSize' => 2, 'page' => 2]);

        $response->assertOk();
        $this->assertSame(5, $response->json('count'));
        $this->assertSame(['Z02', 'Z03'], $this->tails($response->json('rows')));
        $this->assertSame(['Centro', 'Plaza Norte'], array_column($response->json('rows'), 'name'));
    }

    public function test_a_page_past_the_end_is_empty_but_keeps_the_count(): void
    {
        $response = $this->listing(['orderBy' => 'last_data', 'paginationSize' => 10, 'page' => 2]);

        $response->assertOk();
        $this->assertSame(5, $response->json('count'));
        $this->assertSame([], $response->json('rows'));
    }

    public function test_the_order_does_not_open_entities_the_user_cannot_read(): void
    {
        [$otherTenant, $otherScope] = $this->tenantWithRootScope();
        $this->entity('Fuera', name: 'Aaa', lastData: '2026-11-05 00:00:00', tenant: $otherTenant, scope: $otherScope);

        $response = $this->listing(['orderBy' => 'name', 'orderDirection' => 'asc', 'tenant' => $otherTenant->name]);

        $response->assertOk();
        $this->assertSame(0, $response->json('count'));
    }

    public function test_the_other_columns_still_order_in_the_query(): void
    {
        $this->assertSame(['Barrio', 'Z01', 'Z02', 'Z03', 'Z09'], $this->order('urn', 'asc'));
    }

    // ----------------------------------------------------------------- helpers

    private function order(string $column, string $direction): array
    {
        $response = $this->listing(['orderBy' => $column, 'orderDirection' => $direction, 'paginationSize' => 50]);
        $response->assertOk();

        return $this->tails($response->json('rows'));
    }

    private function listing(array $body)
    {
        return $this->actingAs($this->user)->postJson('/api/V1/entities/paginate', $body + ['tenant' => $this->tenant->name]);
    }

    private function tails(array $rows): array
    {
        return array_map(fn (array $row) => substr(strrchr($row['urn'], ':'), 1), $rows);
    }

    /** @return array{0: FiwareTenant, 1: FiwareScope} */
    private function tenantWithRootScope(): array
    {
        $tenant = FiwareTenant::create(['name' => 'test_order_' . strtolower(Str::random(6))]);
        $scope = FiwareScope::create(['name' => '/', 'fiware_tenant_id' => $tenant->id]);

        return [$tenant, $scope];
    }

    private function entity(
        string $tail,
        ?string $name,
        ?string $lastData,
        ?FiwareTenant $tenant = null,
        ?FiwareScope $scope = null,
    ): void {
        $tenant ??= $this->tenant;
        $scope ??= $this->scope;

        $entity = Entity::create([
            'urn'             => "urn:ngsi-ld:TestZone:{$tail}",
            'datamodel'       => 'TestZone',
            'tenant'          => $tenant->name,
            'scope'           => $scope->name,
            'fiware_scope_id' => $scope->id,
        ]);
        $this->entities[$tail] = $entity;

        $property = fn (string $property, string $value, string $timestamp) => EntityProperty::create([
            'urn'       => $entity->urn,
            'tenant'    => $entity->tenant,
            'scope'     => $entity->scope,
            'entity_id' => $entity->id,
            'name'      => $property,
            'value'     => $value,
            'units'     => '',
            'timestamp' => $timestamp,
        ]);

        // The name is stamped earlier than any reading, so it never decides the latest one.
        if ($name !== null) {
            $property('name', $name, '2026-01-01 00:00:00');
        }
        if ($lastData !== null) {
            $property('peopleCount', '12', $lastData);
            $property('occupancy', '0.4', '2026-11-01 00:00:00');
        }
    }
}
