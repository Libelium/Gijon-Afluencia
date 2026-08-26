<?php

namespace Tests\Feature\UserDeletion;

use App\Authorization\AppPermission;
use App\Enums\UserStatus;
use App\Models\Actions\Action;
use App\Models\Actions\ActionEmail;
use App\Models\Alarm;
use App\Models\ApiKey;
use App\Models\Dashboard;
use App\Models\Download;
use App\Models\EntityGroup;
use App\Models\HomeLayout;
use App\Models\HomeWidget;
use App\Models\HtmlBlock;
use App\Models\InConnector;
use App\Models\Organization;
use App\Models\OutConnectors\OutConnector;
use App\Models\Preferencable;
use App\Models\Reports\Report;
use App\Models\Reports\ReportDocConfig;
use App\Models\User;
use App\Models\Workspace;
use App\Services\UserDeletion\UserDeletionService;
use Illuminate\Foundation\Testing\DatabaseTransactions;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Tests\TestCase;

/**
 * Tests the full admin transfer flow via UserDeletionService.
 *
 * Uses DatabaseTransactions so every test rolls back automatically —
 * safe to run against the real development database.
 *
 * Data is created through the real API endpoints (actingAs + postJson)
 * so the full application stack (controllers, policies, observers, etc.)
 * is exercised, not just raw model creation.
 *
 * We call deleteCompletelyTransactional() directly to skip the
 * Keycloak step (external dependency); that step is irreversible
 * and should be tested with a mock in isolation.
 */
class AdminTransferTest extends TestCase
{
    use DatabaseTransactions;

    private User $oldAdmin;
    private User $newAdmin;
    private UserDeletionService $service;

    protected function setUp(): void
    {
        parent::setUp();

        $this->service = app(UserDeletionService::class);

        [$this->oldAdmin, $this->newAdmin] = $this->createUsers();
    }

    // ─── Main transfer test ──────────────────────────────────────────────────

    public function test_all_resources_are_transferred_to_new_admin(): void
    {
        $this->createTransferableData($this->oldAdmin, $this->newAdmin);
        $this->createDeletableData($this->oldAdmin);

        $this->service->deleteCompletelyTransactional($this->oldAdmin, $this->newAdmin);

        $old = $this->oldAdmin;
        $new = $this->newAdmin;

        $this->assertEquals(UserStatus::Deleted, $old->fresh()->status);

        foreach ([Workspace::class, Dashboard::class, Alarm::class, HtmlBlock::class,
                  EntityGroup::class, ApiKey::class, Report::class, ReportDocConfig::class,
                  InConnector::class, OutConnector::class, Download::class] as $model) {
            $this->assertEquals(0, $model::where('user_id', $old->id)->count(), "{$model}: old admin still has records");
            $this->assertGreaterThan(0, $model::where('user_id', $new->id)->count(), "{$model}: new admin has no records after transfer");
        }

        // ── Workspace memberships transferred (no duplicates) ─────────────────
        $this->assertEquals(0, DB::table('workspace_has_users')->where('user_id', $old->id)->count(), 'Old admin still has workspace memberships');

        foreach (Workspace::where('user_id', $new->id)->pluck('id') as $wsId) {
            $count = DB::table('workspace_has_users')
                ->where('workspace_id', $wsId)
                ->where('user_id', $new->id)
                ->count();
            $this->assertLessThanOrEqual(1, $count, "Duplicate membership on workspace {$wsId}");
        }

        // ── Action user_id transferred ────────────────────────────────────────
        $this->assertEquals(0, Action::where('user_id', $old->id)->count(), 'Old admin still owns Actions');
        $this->assertGreaterThan(0, Action::where('user_id', $new->id)->count(), 'New admin has no Actions after transfer');

        // ── ActionEmail destination updated ───────────────────────────────────
        $this->assertCount(0, ActionEmail::where('destination', 'LIKE', '%' . $old->email . '%')->get(), 'Old admin email still present in ActionEmail destinations');

        $actionEmailWithNew = ActionEmail::where('destination', 'LIKE', '%' . $new->email . '%')->first();
        $this->assertNotNull($actionEmailWithNew, 'New admin email not found in ActionEmail destinations after transfer');
        $this->assertContains($new->email, $actionEmailWithNew->destination);

        // ── Organization.admin transferred ────────────────────────────────────
        $this->assertEquals(0, Organization::where('admin', $old->id)->count(), 'Old admin is still admin of an organization');
        $this->assertGreaterThan(0, Organization::where('admin', $new->id)->count(), 'New admin is not admin of any organization');

        // ── Deletable data removed ────────────────────────────────────────────
        $this->assertEquals(0, HomeLayout::where('user_id', $old->id)->count(), 'HomeLayout not deleted');
        $this->assertEquals(0, HomeWidget::where('user_id', $old->id)->count(), 'HomeWidget not deleted');
        $this->assertEquals(0, Preferencable::where('user_id', $old->id)->count(), 'Preferencable not deleted');
        $this->assertEquals(0, DB::table('password_resets')->where('email', $old->email)->count(), 'PasswordReset not deleted');

        // ── Spatie permissions removed ────────────────────────────────────────
        $this->assertEquals(0, DB::table('model_has_roles')->where('model_id', $old->id)->where('model_type', User::class)->count(), 'Old admin still has roles');
        $this->assertEquals(0, DB::table('model_has_permissions')->where('model_id', $old->id)->where('model_type', User::class)->count(), 'Old admin still has spatie permissions');

        // ── Resource permissions removed ──────────────────────────────────────
        $this->assertEquals(0, DB::table('model_has_resource_permissions')->where('model_id', $old->id)->where('model_type', 'users')->count(), 'Old admin still has resource permissions');
    }

    public function test_delete_without_transfer_cleans_data_and_marks_deleted(): void
    {
        $this->createTransferableData($this->oldAdmin, $this->newAdmin);
        $this->createDeletableData($this->oldAdmin);

        $this->service->deleteCompletelyTransactional($this->oldAdmin);

        $old = $this->oldAdmin;

        $this->assertEquals(UserStatus::Deleted, $old->fresh()->status);
        $this->assertEquals(0, Organization::where('admin', $old->id)->count(), 'Organization still exists after clean');
    }

    public function test_workspace_membership_dedup_is_handled(): void
    {
        $ws = Workspace::create(['name' => '[TEST] Shared WS', 'user_id' => $this->oldAdmin->id, 'collaborative' => false]);
        DB::table('workspace_has_users')->insert(['workspace_id' => $ws->id, 'user_id' => $this->oldAdmin->id]);
        DB::table('workspace_has_users')->insert(['workspace_id' => $ws->id, 'user_id' => $this->newAdmin->id]);

        $this->service->deleteCompletelyTransactional($this->oldAdmin, $this->newAdmin);

        $this->assertEquals(1, DB::table('workspace_has_users')->where('workspace_id', $ws->id)->where('user_id', $this->newAdmin->id)->count(), 'Duplicate workspace membership after dedup');
        $this->assertEquals(0, DB::table('workspace_has_users')->where('workspace_id', $ws->id)->where('user_id', $this->oldAdmin->id)->count(), 'Old admin membership not removed');
    }

    // ─── Setup helpers ───────────────────────────────────────────────────────

    /** @return array{User, User} */
    private function createUsers(): array
    {
        $oldAdmin = User::create([
            'name'               => 'Old Admin',
            'email'              => 'old.admin.' . Str::random(6) . '@transfer-test.local',
            'enabled'            => true,
            'status'             => UserStatus::Active,
            'keycloak_client_id' => 'test-kc-old-' . Str::random(6),
        ]);

        $org = Organization::create(['name' => '[TEST] Org', 'admin' => $oldAdmin->id]);
        $oldAdmin->organization_id = $org->id;
        $oldAdmin->save();

        $newAdmin = User::create([
            'name'               => 'New Admin',
            'email'              => 'new.admin.' . Str::random(6) . '@transfer-test.local',
            'enabled'            => true,
            'status'             => UserStatus::Active,
            'keycloak_client_id' => 'test-kc-new-' . Str::random(6),
            'organization_id'    => $org->id,
        ]);

        $this->grantPermissions($oldAdmin);
        $this->grantPermissions($newAdmin);

        return [$oldAdmin, $newAdmin];
    }

    /**
     * Assigns the full set of application permissions to the user via Spatie so that
     * all policy checks pass when creating resources through the real API endpoints.
     */
    private function grantPermissions(User $user): void
    {
        $permissions = array_map(fn (AppPermission $p) => $p->value, AppPermission::plusPermissions());
        $user->givePermissionTo($permissions);
    }

    /**
     * Creates all transferable resources via the real API endpoints, acting as $oldAdmin.
     * This exercises the full controller / policy / observer stack, not just model creation.
     *
     * The $newAdmin is only used to seed the dedup scenario (ws1 shared membership).
     */
    private function createTransferableData(User $oldAdmin, User $newAdmin): void
    {
        // Workspaces (ws1 shared with newAdmin to test dedup)
        $ws1 = $this->api($oldAdmin, '/workspaces', ['name' => '[TEST] WS 1', 'collaborative' => false]);
        $this->api($oldAdmin, '/workspaces', ['name' => '[TEST] WS 2', 'collaborative' => false]);

        DB::table('workspace_has_users')->insert(['workspace_id' => $ws1['id'], 'user_id' => $oldAdmin->id]);
        DB::table('workspace_has_users')->insert(['workspace_id' => $ws1['id'], 'user_id' => $newAdmin->id]);

        // Dashboard
        $dash = $this->api($oldAdmin, '/dashboards', [
            'name'     => '[TEST] Dashboard',
            'type'     => 'Custom',
            'timezone' => 'UTC',
        ]);

        // Alarm — created directly because the API endpoint requires real IoT entities
        // for conditions (Entity::findOrFail), which don't exist in this test environment.
        // The transfer mechanism (StandardUserIdHandler) is the same regardless.
        $alarm = Alarm::create([
            'name'     => '[TEST] Alarm',
            'user_id'  => $oldAdmin->id,
            'type'     => 'threshold',
            'function' => 'avg',
            'up'       => false,
            'disabled' => false,
        ]);
        // Replicate what AlarmController does: grant the owner resource permissions
        // so that the alarm actions API can authorize the update check.
        $oldAdmin->giveResourcePermissionsTo(
            \App\Authorization\AppResourcePermission::defaultPermissions(), $alarm, true
        );

        // Action + ActionEmail (old admin email in destination) — via the real API endpoint.
        // This exercises the ActionHandler path including the email destination setup.
        $this->api($oldAdmin, '/alarms/actions', [
            'alarm_ids' => [$alarm->id],
            'actions'   => [
                [
                    'type'          => 'email',
                    'alarm_trigger' => 'up',
                    'to'            => [$oldAdmin->email],
                    'subject'       => '[TEST] Subject',
                    'body'          => 'Test body',
                ],
            ],
        ]);

        // EntityGroup — created directly: the API requires non-empty real entities (IoT),
        // which don't exist in this test environment.
        EntityGroup::create(['name' => '[TEST] Group', 'user_id' => $oldAdmin->id]);

        // ApiKey
        $this->api($oldAdmin, '/user/regenerate/apikey', []);

        // ReportDocConfig with header (also creates an HtmlBlock as a side-effect)
        $docConfig = $this->api($oldAdmin, '/reportDocConfigs', [
            'name'   => '[TEST] Doc Config',
            'config' => ['orientation' => 'portrait'],
            'header' => ['content' => '<p>[TEST] Header</p>'],
        ]);

        // Report referencing the dashboard
        $report = $this->api($oldAdmin, '/reports', [
            'name'     => '[TEST] Report',
            'priority' => 1,
            'config'   => [
                'name'   => '[TEST] Doc Config (report)',
                'config' => ['orientation' => 'portrait'],
            ],
            'blocks' => [
                [
                    'type'     => 'dashboard',
                    'position' => 0,
                    'block'    => ['id' => $dash['id']],
                ],
            ],
            'actions' => [],
        ]);

        // InConnector (Loriot)
        $this->api($oldAdmin, '/connectors/in/loriot', [
            'name'            => '[TEST] InConnector',
            'type'            => 'loriot',
            'status'          => 'active',
            'downlink_active' => false,
        ]);

        // OutConnector (MQTT) — entities/devices must be passed as [] (not omitted)
        // because linkEntities/linkDevices have non-nullable array type hints.
        $this->api($oldAdmin, '/connectors/out/mqtt', [
            'name'           => '[TEST] OutConnector MQTT',
            'status'         => 'active',
            'type'           => 'mqtt',
            'ipAddress'      => '127.0.0.1',
            'port'           => 1883,
            'ssl'            => false,
            'topicTemplate'  => ['test/topic'],
            'payload_type'   => 'legacy',
            'payload_config' => ['format' => 'legacy'],
            'entities'       => [],
            'devices'        => [],
        ]);

        // OutConnector (HTTP)
        $this->api($oldAdmin, '/connectors/out/http', [
            'name'         => '[TEST] OutConnector HTTP',
            'status'       => 'active',
            'url'          => 'https://httpbin.org/post',
            'method'       => 'POST',
            'payload_type' => 'legacy',
            'entities'     => [],
            'devices'      => [],
        ]);

        // Download — no public API endpoint, created directly.
        // Linked to the report as the downloadable resource.
        Download::create([
            'user_id'           => $oldAdmin->id,
            'downloadable_id'   => $report['id'],
            'downloadable_type' => 'reports',
            'file_name'         => '[TEST] Report Export',
            'file_extension'    => 'csv',
            'status'            => 'Completed',
            'downloaded'        => false,
        ]);
    }

    private function createDeletableData(User $admin): void
    {
        // HomeLayout + HomeWidget via API
        $layout = $this->api($admin, '/home-layouts', ['name' => '[TEST] Layout']);
        $this->api($admin, "/home-layouts/{$layout['id']}/widgets", ['type' => 'chart']);

        // Preferencable — no API endpoint, created directly
        $pref = DB::table('preferences')->first();
        if ($pref) {
            Preferencable::create(['user_id' => $admin->id, 'preference_id' => $pref->id, 'value' => 'test']);
        }

        // PasswordReset — no API endpoint, created directly
        DB::table('password_resets')->insert(['email' => $admin->email, 'token' => Str::random(60)]);
    }

    // ─── HTTP helper ─────────────────────────────────────────────────────────

    /**
     * Makes a POST request to /api/V1{$path} authenticated as $user.
     * Fails the test immediately if the response is not 2xx.
     *
     * @return array<string, mixed>
     */
    private function api(User $user, string $path, array $data): array
    {
        $response = $this->actingAs($user)->postJson('/api/V1' . $path, $data);

        $this->assertTrue(
            $response->isSuccessful(),
            "POST /api/V1{$path} returned {$response->status()}: " . $response->content()
        );
        $json = $response->json() ?? [];
        // Some resources use DefaultPermissionsResource ($wrap = null) and return the
        // payload flat; others extend JsonResource and wrap in {"data": {...}}.
        // Unwrap the 'data' key so callers always get the flat resource array.
        return (isset($json['data']) && is_array($json['data']) && !isset($json['data'][0]))
            ? $json['data']
            : $json;
    }
}
