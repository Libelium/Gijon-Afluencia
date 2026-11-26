<?php

namespace Tests\Feature;

use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Enums\UserStatus;
use App\Models\Entity;
use App\Models\FiwareScope;
use App\Models\FiwareTenant;
use App\Models\Organization;
use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseTransactions;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

/**
 * The editors of an organization (access level «Edición», role org_editor) may change the name of
 * an entity and the maximum capacity of a zone, and nothing else of it. Viewers may change nothing.
 */
class EntityEditorInfoTest extends TestCase
{
    use DatabaseTransactions;

    protected $connectionsToTransact = ['pgsql', 'pgsql_realtime'];

    private FiwareTenant $tenant;
    private FiwareScope $scope;
    private Entity $zone;

    protected function setUp(): void
    {
        parent::setUp();

        Http::fake(['*/api/v1/context-broker/entities/*' => Http::response(['errors' => [], 'success' => []], 207)]);

        $this->tenant = FiwareTenant::create(['name' => 'test_editor_' . strtolower(Str::random(6))]);
        $this->scope = FiwareScope::create(['name' => '/', 'fiware_tenant_id' => $this->tenant->id]);
        $this->zone = Entity::create([
            'urn'             => 'urn:ngsi-ld:CrowdFlowZone:' . Str::random(8),
            'datamodel'       => 'CrowdFlowZone',
            'tenant'          => $this->tenant->name,
            'scope'           => $this->scope->name,
            'fiware_scope_id' => $this->scope->id,
        ]);
    }

    public function test_an_editor_may_rename_an_entity_and_set_or_remove_its_capacity(): void
    {
        $editor = $this->member(AppPermission::orgEditorPermissions(), [AppResourcePermission::READ, AppResourcePermission::UPDATE]);

        $this->actingAs($editor)->patchJson($this->url(), ['name' => 'Plaza Mayor'])->assertOk();
        $this->actingAs($editor)->patchJson($this->url(), ['maxCapacity' => 980])->assertOk();
        $this->actingAs($editor)->patchJson($this->url(), ['name' => 'Plaza Mayor', 'maxCapacity' => 980, 'timestamp' => '2026-11-26T10:00:00Z'])->assertOk();

        // Removing the capacity is allowed too; what the broker answers afterwards is another matter.
        $removed = $this->actingAs($editor)->deleteJson($this->url() . '/maxCapacity');
        $this->assertNotSame(403, $removed->status());
    }

    public function test_an_editor_may_not_touch_anything_else_of_the_entity(): void
    {
        $editor = $this->member(AppPermission::orgEditorPermissions(), [AppResourcePermission::READ, AppResourcePermission::UPDATE]);

        $this->actingAs($editor)
            ->patchJson($this->url(), ['geolocation' => ['type' => 'Point', 'coordinates' => [-5.66, 43.54]]])
            ->assertForbidden();
        $this->actingAs($editor)->patchJson($this->url(), ['temperature' => 21.5])->assertForbidden();
        // Mixing an allowed attribute with another one does not open the other one.
        $this->actingAs($editor)->patchJson($this->url(), ['name' => 'Plaza', 'description' => 'x'])->assertForbidden();
        $this->actingAs($editor)->deleteJson($this->url() . '/description')->assertForbidden();
    }

    public function test_a_viewer_may_change_nothing(): void
    {
        $viewer = $this->member(AppPermission::orgViewerPermissions(), [AppResourcePermission::READ]);

        $this->actingAs($viewer)->patchJson($this->url(), ['name' => 'Plaza Mayor'])->assertForbidden();
        $this->actingAs($viewer)->patchJson($this->url(), ['maxCapacity' => 980])->assertForbidden();
    }

    public function test_the_info_permission_without_update_over_the_data_is_not_enough(): void
    {
        $editor = $this->member(AppPermission::orgEditorPermissions(), [AppResourcePermission::READ]);

        $this->actingAs($editor)->patchJson($this->url(), ['maxCapacity' => 980])->assertForbidden();
    }

    // ----------------------------------------------------------------- helpers

    private function url(): string
    {
        return "/api/V1/entities/{$this->zone->id}/properties";
    }

    /** A member of an organization with the given module permissions and access over the tenant. */
    private function member(array $permissions, array $overTenant): User
    {
        $user = User::create([
            'name'               => '[TEST] Member',
            'email'              => 'member.' . strtolower(Str::random(8)) . '@editor-test.local',
            'enabled'            => true,
            'status'             => UserStatus::Active,
            'keycloak_client_id' => 'test-kc-' . strtolower(Str::random(8)),
        ]);
        $organization = Organization::create(['name' => '[TEST] Org ' . Str::random(6), 'admin' => $user->id]);
        $user->organization_id = $organization->id;
        $user->save();

        $user->givePermissionTo(array_map(fn (AppPermission $p) => $p->value, $permissions));
        $user->giveResourcePermissionsTo($overTenant, $this->tenant);

        return $user;
    }
}
