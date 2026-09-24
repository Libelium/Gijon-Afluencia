<?php

namespace Tests\Feature\Auth;

use App\Authorization\AppPermission;
use App\Authorization\AppResourcePermission;
use App\Enums\UserStatus;
use App\Models\Alarm;
use App\Models\Dashboard;
use App\Models\FiwareTenant;
use App\Models\Organization;
use App\Models\User;
use App\Repositories\OrganizationRepository;
use App\Services\OrganizationAccessService;
use Illuminate\Foundation\Testing\DatabaseTransactions;
use Illuminate\Support\Str;
use Tests\TestCase;

/**
 * Organization access levels: what a user sees and may change of its organization's tenants,
 * dashboards and alarms. The database rolls back after each test.
 */
class OrganizationAccessTest extends TestCase
{
    use DatabaseTransactions;

    protected $connectionsToTransact = ['pgsql', 'pgsql_realtime'];

    private User $admin;
    private User $member;
    private Organization $organization;
    private FiwareTenant $tenant;
    private Dashboard $dashboard;
    private Alarm $alarm;
    private OrganizationAccessService $service;

    protected function setUp(): void
    {
        parent::setUp();

        config(['logging.default' => 'null']);
        $this->service = app(OrganizationAccessService::class);

        $this->admin = $this->user('admin');
        $this->organization = Organization::create(['name' => '[TEST] Access org', 'admin' => $this->admin->id]);
        $this->admin->organization_id = $this->organization->id;
        $this->admin->save();
        $this->admin->assignRole('super_admin');

        $this->member = $this->user('member', $this->organization->id);

        $this->tenant = FiwareTenant::create(['name' => 'test_access_' . strtolower(Str::random(6))]);
        OrganizationRepository::assignResourceToOrganization($this->organization->id, $this->tenant);
        $this->admin->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $this->tenant);

        $this->dashboard = $this->dashboardOf($this->admin);
        $this->alarm = $this->alarmOf($this->admin);
    }

    public function test_read_level_sees_the_organization_but_cannot_change_it(): void
    {
        $this->service->apply($this->member, OrganizationAccessService::READ);
        $member = $this->member->fresh();

        foreach ([$this->tenant, $this->dashboard, $this->alarm] as $resource) {
            $this->assertTrue($member->hasResourcePermissionTo(AppResourcePermission::READ, $resource), $resource->getTable());
            $this->assertFalse($member->hasResourcePermissionTo(AppResourcePermission::UPDATE, $resource), $resource->getTable());
        }

        $this->assertSame('read', $member->access_level);
        $this->assertTrue($member->can(AppPermission::DASHBOARDS_READ->value));
        $this->assertTrue($member->can(AppPermission::ALARMS_READ->value));
        $this->assertFalse($member->can(AppPermission::ALARMS_UPDATE->value));
    }

    public function test_edit_level_may_change_dashboards_and_alarms(): void
    {
        $this->service->apply($this->member, OrganizationAccessService::EDIT);
        $member = $this->member->fresh();

        $this->assertTrue($member->hasResourcePermissionTo(AppResourcePermission::UPDATE, $this->dashboard));
        $this->assertTrue($member->hasResourcePermissionTo(AppResourcePermission::UPDATE, $this->alarm));
        $this->assertTrue($member->can(AppPermission::ALARMS_UPDATE->value));
        $this->assertTrue($member->can(AppPermission::DASHBOARDS_UPDATE->value));
        $this->assertTrue($member->hasRole('org_editor'));
        $this->assertFalse($member->hasRole('org_viewer'));
    }

    public function test_lowering_the_level_revokes_edition_and_removing_it_revokes_everything(): void
    {
        $this->service->apply($this->member, OrganizationAccessService::EDIT);
        $this->service->apply($this->member, OrganizationAccessService::READ);
        $member = $this->member->fresh();

        $this->assertTrue($member->hasResourcePermissionTo(AppResourcePermission::READ, $this->dashboard));
        $this->assertFalse($member->hasResourcePermissionTo(AppResourcePermission::UPDATE, $this->dashboard));
        $this->assertFalse($member->can(AppPermission::ALARMS_UPDATE->value));

        $this->service->apply($member, null);
        $member = $member->fresh();

        $this->assertFalse($member->hasResourcePermissionTo(AppResourcePermission::READ, $this->tenant));
        $this->assertFalse($member->hasResourcePermissionTo(AppResourcePermission::READ, $this->dashboard));
        $this->assertNull($member->access_level);
        $this->assertFalse($member->can(AppPermission::DASHBOARDS_READ->value));
    }

    /** Only what belongs to others is revoked: the user's own dashboard stays its own. */
    public function test_removing_the_level_keeps_what_the_user_created(): void
    {
        $this->service->apply($this->member, OrganizationAccessService::EDIT);
        $own = $this->dashboardOf($this->member->fresh());

        $this->service->apply($this->member->fresh(), null);
        $member = $this->member->fresh();

        $this->assertTrue($member->hasResourcePermissionTo(AppResourcePermission::READ, $own));
        $this->assertTrue($member->hasResourcePermissionTo(AppResourcePermission::UPDATE, $own));
    }

    public function test_resources_created_later_reach_the_users_with_a_level(): void
    {
        $this->service->apply($this->member, OrganizationAccessService::READ);

        $later = $this->dashboardOf($this->admin);
        $alarm = $this->alarmOf($this->admin);
        $member = $this->member->fresh();

        $this->assertTrue($member->hasResourcePermissionTo(AppResourcePermission::READ, $later));
        $this->assertTrue($member->hasResourcePermissionTo(AppResourcePermission::READ, $alarm));
        $this->assertFalse($member->hasResourcePermissionTo(AppResourcePermission::UPDATE, $later));
    }

    public function test_a_user_without_level_gets_nothing_created_later(): void
    {
        $later = $this->dashboardOf($this->admin);

        $this->assertFalse($this->member->fresh()->hasResourcePermissionTo(AppResourcePermission::READ, $later));
    }

    public function test_the_administrator_changes_the_level_through_the_api(): void
    {
        $url = '/api/V1/organizations/' . $this->organization->id . '/users/' . $this->member->id . '/access';

        $this->actingAs($this->admin, 'api')
            ->putJson($url, ['accessLevel' => 'edit'])
            ->assertOk()
            ->assertJsonPath('accessLevel', 'edit');

        $this->actingAs($this->admin, 'api')
            ->putJson($url, ['accessLevel' => 'sudo'])
            ->assertStatus(422);

        $this->actingAs($this->admin, 'api')
            ->putJson('/api/V1/organizations/' . $this->organization->id . '/users/' . $this->admin->id . '/access', ['accessLevel' => 'read'])
            ->assertStatus(422);

        $this->actingAs($this->member->fresh(), 'api')
            ->putJson($url, ['accessLevel' => 'edit'])
            ->assertForbidden();
    }

    private function user(string $prefix, ?int $organizationId = null): User
    {
        return User::create([
            'name' => ucfirst($prefix),
            'email' => $prefix . '.' . strtolower(Str::random(6)) . '@access-test.local',
            'enabled' => true,
            'status' => UserStatus::Active,
            'keycloak_client_id' => 'test-kc-' . strtolower(Str::random(8)),
            'organization_id' => $organizationId,
        ]);
    }

    /** Created the way the controllers do it, so the sharing hook runs. */
    private function dashboardOf(User $owner): Dashboard
    {
        $dashboard = Dashboard::create([
            'name' => '[TEST] Dashboard',
            'type' => 'Custom',
            'timezone' => 'UTC',
            'user_id' => $owner->id,
            'layout' => ['lg' => [], 'md' => [], 'sm' => [], 'xs' => [], 'xxs' => []],
        ]);
        $owner->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $dashboard, true);

        return $dashboard;
    }

    private function alarmOf(User $owner): Alarm
    {
        $alarm = Alarm::create([
            'name' => '[TEST] Alarm',
            'user_id' => $owner->id,
            'type' => 'threshold',
            'function' => 'avg',
            'up' => false,
            'disabled' => false,
        ]);
        $owner->giveResourcePermissionsTo(AppResourcePermission::defaultPermissions(), $alarm, true);

        return $alarm;
    }
}
