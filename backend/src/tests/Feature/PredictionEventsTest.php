<?php

namespace Tests\Feature;

use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Enums\UserStatus;
use App\Models\FiwareScope;
use App\Models\FiwareTenant;
use App\Models\Organization;
use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseTransactions;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Tests\TestCase;

/**
 * /api/V1/prediction-events: the events registry of the predictions component, read and written
 * in the bucket as that component reads it (crowd_predictions/events_registry.py). The bucket is
 * faked; the database rolls back after each test.
 */
class PredictionEventsTest extends TestCase
{
    use DatabaseTransactions;

    protected $connectionsToTransact = ['pgsql', 'pgsql_realtime'];

    private const ZONE = 'urn:ngsi-ld:TestZone:plaza';

    private const OTHER_ZONE = 'urn:ngsi-ld:TestZone:muelle';

    private FiwareTenant $tenant;

    private User $editor;

    protected function setUp(): void
    {
        parent::setUp();

        Storage::fake('s3');
        $this->tenant = $this->tenantWithScopes('/');
        $this->editor = $this->user([AppPermission::PREDICTION_EVENTS_READ, AppPermission::PREDICTION_EVENTS_UPDATE]);
        $this->editor->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $this->tenant);
    }

    // ----------------------------------------------------------------- the file predictions reads

    public function test_an_event_is_written_where_and_as_predictions_reads_it(): void
    {
        $this->store([
            'date' => '2026-12-14',
            'end_date' => '2026-12-20',
            'event_type' => 'market',
            'device_ids' => [self::ZONE, self::OTHER_ZONE],
            'notes' => 'Mercado de Navidad, "el grande"',
            'start_hour' => 10,
            'end_hour' => 21,
        ])->assertCreated();

        $this->assertSame(
            "date,event_type,device_ids,notes,end_date,start_hour,end_hour\n"
            . "2026-12-14,market,\"urn:ngsi-ld:TestZone:plaza,urn:ngsi-ld:TestZone:muelle\",\"Mercado de Navidad, \"\"el grande\"\"\",2026-12-20,10,21\n",
            Storage::disk('s3')->get($this->key()),
        );
    }

    public function test_the_scope_is_one_segment_of_the_key_as_in_predictions(): void
    {
        $tenant = $this->tenantWithScopes('/norte/centro');
        $this->editor->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $tenant);

        $this->store(['date' => '2026-12-14', 'event_type' => 'concert'], $tenant->name, '/norte/centro')->assertCreated();

        Storage::disk('s3')->assertExists("prediction-models/{$tenant->name}/norte_centro/events_registry.csv");
    }

    public function test_a_one_day_event_leaves_the_optional_columns_empty(): void
    {
        $this->store(['date' => '2026-12-14', 'end_date' => '2026-12-14', 'event_type' => 'concert'])->assertCreated();

        $this->assertSame(
            "date,event_type,device_ids,notes,end_date,start_hour,end_hour\n2026-12-14,concert,,,,,\n",
            Storage::disk('s3')->get($this->key()),
        );
    }

    public function test_a_hand_written_file_with_the_first_four_columns_keeps_its_rows(): void
    {
        Storage::disk('s3')->put($this->key(), "date,event_type,device_ids,notes\r\n2026-08-04,fair,,Feria\r\n\r\n2026-09-01,,,\r\n");

        $this->store(['date' => '2026-12-14', 'event_type' => 'market'])->assertCreated();

        $this->assertSame(
            "date,event_type,device_ids,notes,end_date,start_hour,end_hour\n"
            . "2026-08-04,fair,,Feria,,,\n2026-09-01,,,,,,\n2026-12-14,market,,,,,\n",
            Storage::disk('s3')->get($this->key()),
        );
    }

    // ----------------------------------------------------------------- listing

    public function test_without_a_registry_the_list_is_empty(): void
    {
        $this->index()->assertOk()->assertExactJson(['rows' => [], 'canEdit' => true]);
    }

    public function test_the_list_reads_the_events_with_an_id_each(): void
    {
        Storage::disk('s3')->put($this->key(), implode("\n", [
            'date,event_type,device_ids,notes,end_date,start_hour,end_hour',
            '2026-12-14,market,"' . self::ZONE . '",Navidad,2026-12-20,10,21',
            ',,,row without a date,,,',
            '2026-12-31,concert,,,,,',
        ]) . "\n");

        $rows = $this->index()->assertOk()->json('rows');

        $this->assertCount(2, $rows);
        $this->assertSame(
            ['date' => '2026-12-14', 'end_date' => '2026-12-20', 'event_type' => 'market', 'device_ids' => [self::ZONE],
                'notes' => 'Navidad', 'start_hour' => 10, 'end_hour' => 21],
            array_diff_key($rows[0], ['id' => true]),
        );
        $this->assertSame(['2026-12-31', [], null], [$rows[1]['end_date'], $rows[1]['device_ids'], $rows[1]['start_hour']]);
        $this->assertStringStartsWith('2:', $rows[1]['id']); // its position in the file, blank-date row included
    }

    // ----------------------------------------------------------------- deleting

    public function test_an_event_is_deleted_by_its_id_and_the_rest_stay(): void
    {
        $this->store(['date' => '2026-12-14', 'event_type' => 'market'])->assertCreated();
        $second = $this->store(['date' => '2026-12-31', 'event_type' => 'concert'])->json();

        $this->destroy($second['id'])->assertNoContent();

        $this->assertSame(['2026-12-14'], array_column($this->index()->json('rows'), 'date'));
    }

    public function test_an_event_changed_since_it_was_listed_is_not_deleted(): void
    {
        $listed = $this->store(['date' => '2026-12-14', 'event_type' => 'market'])->json();
        $file = str_replace('market', 'fair', Storage::disk('s3')->get($this->key()));
        Storage::disk('s3')->put($this->key(), $file);

        $this->destroy($listed['id'])->assertStatus(409);
        $this->destroy('7:000000000000')->assertStatus(409);

        $this->assertSame($file, Storage::disk('s3')->get($this->key()));
    }

    // ----------------------------------------------------------------- validation

    public function test_what_predictions_would_skip_is_refused(): void
    {
        $this->store(['date' => '2026-12-14', 'end_date' => '2026-12-13', 'event_type' => 'market'])->assertUnprocessable();
        $this->store(['date' => '14/12/2026', 'event_type' => 'market'])->assertUnprocessable();
        $this->store(['date' => '2026-12-14', 'event_type' => 'market', 'start_hour' => 21, 'end_hour' => 10])->assertUnprocessable();
        $this->store(['date' => '2026-12-14', 'event_type' => 'market', 'start_hour' => 10])->assertUnprocessable();
        $this->store(['date' => '2026-12-14', 'event_type' => 'market', 'device_ids' => ['plaza']])->assertUnprocessable();
        $this->store(['date' => '2026-12-14', 'event_type' => 'market', 'device_ids' => [self::ZONE . ',' . self::OTHER_ZONE]])->assertUnprocessable();

        Storage::disk('s3')->assertMissing($this->key());
    }

    // ----------------------------------------------------------------- permissions

    public function test_whoever_may_only_read_sees_the_list_but_cannot_change_it(): void
    {
        $reader = $this->user([AppPermission::PREDICTION_EVENTS_READ]);
        $reader->giveResourcePermissionsTo([AppResourcePermission::READ], $this->tenant);

        $this->index($reader)->assertOk()->assertJson(['canEdit' => false]);
        $this->store(['date' => '2026-12-14', 'event_type' => 'market'], user: $reader)->assertForbidden();
        $this->destroy('0:000000000000', $reader)->assertForbidden();
    }

    public function test_the_update_permission_also_needs_update_access_to_the_tenant(): void
    {
        $editor = $this->user([AppPermission::PREDICTION_EVENTS_READ, AppPermission::PREDICTION_EVENTS_UPDATE]);
        $editor->giveResourcePermissionsTo([AppResourcePermission::READ], $this->tenant);

        $this->index($editor)->assertOk()->assertJson(['canEdit' => false]);
        $this->store(['date' => '2026-12-14', 'event_type' => 'market'], user: $editor)->assertForbidden();
    }

    public function test_access_to_the_scope_alone_is_enough(): void
    {
        $editor = $this->user([AppPermission::PREDICTION_EVENTS_READ, AppPermission::PREDICTION_EVENTS_UPDATE]);
        $editor->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $this->tenant->scopes()->first());

        $this->store(['date' => '2026-12-14', 'event_type' => 'market'], user: $editor)->assertCreated();
    }

    public function test_without_the_permission_or_the_tenant_nothing_is_shown(): void
    {
        $outsider = $this->user([]);
        $outsider->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $this->tenant);
        $this->index($outsider)->assertForbidden();

        $stranger = $this->user([AppPermission::PREDICTION_EVENTS_READ]);
        $this->index($stranger)->assertForbidden();

        $this->index($this->editor, 'no_such_tenant')->assertNotFound();
        $this->index($this->editor, $this->tenant->name, '/no/such/scope')->assertNotFound();
    }

    // ----------------------------------------------------------------- helpers

    private function key(?string $tenant = null): string
    {
        return 'prediction-models/' . ($tenant ?? $this->tenant->name) . '/_/events_registry.csv';
    }

    private function index(?User $user = null, ?string $tenant = null, string $scope = '/')
    {
        $query = http_build_query(['tenant' => $tenant ?? $this->tenant->name, 'scope' => $scope]);

        return $this->actingAs($user ?? $this->editor)->getJson("/api/V1/prediction-events?{$query}");
    }

    private function store(array $event, ?string $tenant = null, string $scope = '/', ?User $user = null)
    {
        return $this->actingAs($user ?? $this->editor)->postJson('/api/V1/prediction-events', $event + [
            'tenant' => $tenant ?? $this->tenant->name,
            'scope' => $scope,
        ]);
    }

    private function destroy(string $id, ?User $user = null)
    {
        $query = http_build_query(['tenant' => $this->tenant->name, 'scope' => '/']);

        return $this->actingAs($user ?? $this->editor)->deleteJson('/api/V1/prediction-events/' . rawurlencode($id) . "?{$query}");
    }

    private function tenantWithScopes(string $scope): FiwareTenant
    {
        $tenant = FiwareTenant::create(['name' => 'test_events_' . strtolower(Str::random(6))]);
        FiwareScope::create(['name' => $scope, 'fiware_tenant_id' => $tenant->id]);

        return $tenant;
    }

    private function user(array $permissions): User
    {
        $user = User::create([
            'name' => '[TEST] Events',
            'email' => 'events.' . strtolower(Str::random(8)) . '@events-test.local',
            'enabled' => true,
            'status' => UserStatus::Active,
            'keycloak_client_id' => 'test-kc-' . strtolower(Str::random(8)),
        ]);
        $organization = Organization::create(['name' => '[TEST] Events org ' . Str::random(6), 'admin' => $user->id]);
        $user->organization_id = $organization->id;
        $user->save();
        $user->givePermissionTo(array_map(fn (AppPermission $p) => $p->value, $permissions));

        return $user;
    }
}
