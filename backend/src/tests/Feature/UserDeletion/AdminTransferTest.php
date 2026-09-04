<?php

namespace Tests\Feature\UserDeletion;

use App\Authorization\AppPermission;
use App\Enums\UserStatus;
use App\Models\Actions\Action;
use App\Models\Actions\ActionEmail;
use App\Models\Alarm;
use App\Models\ApiKey;
use App\Models\Dashboard;
use App\Models\EntityGroup;
use App\Models\InConnector;
use App\Models\Organization;
use App\Models\OutConnectors\OutConnector;
use App\Models\Preferencable;
use App\Models\User;
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

    /**
     * DatabaseTransactions only rolls back the DEFAULT connection unless told otherwise, and part
     * of the schema this flow touches lives in the separate `pgsql_realtime` database.
     */
    protected $connectionsToTransact = ['pgsql', 'pgsql_realtime'];

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
        $this->createTransferableData($this->oldAdmin);
        $this->createDeletableData($this->oldAdmin);

        $this->service->deleteCompletelyTransactional($this->oldAdmin, $this->newAdmin);

        $old = $this->oldAdmin;
        $new = $this->newAdmin;

        $this->assertEquals(UserStatus::Deleted, $old->fresh()->status);

        foreach ([Dashboard::class, Alarm::class,
                  EntityGroup::class, ApiKey::class,
                  InConnector::class, OutConnector::class] as $model) {
            $this->assertEquals(0, $model::where('user_id', $old->id)->count(), "{$model}: old admin still has records");
            $this->assertGreaterThan(0, $model::where('user_id', $new->id)->count(), "{$model}: new admin has no records after transfer");
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
        $this->assertEquals(0, Preferencable::where('user_id', $old->id)->count(), 'Preferencable not deleted');

        // ── Spatie permissions removed ────────────────────────────────────────
        $this->assertEquals(0, DB::table('model_has_roles')->where('model_id', $old->id)->where('model_type', User::class)->count(), 'Old admin still has roles');
        $this->assertEquals(0, DB::table('model_has_permissions')->where('model_id', $old->id)->where('model_type', User::class)->count(), 'Old admin still has spatie permissions');

        // ── Resource permissions removed ──────────────────────────────────────
        $this->assertEquals(0, DB::table('model_has_resource_permissions')->where('model_id', $old->id)->where('model_type', 'users')->count(), 'Old admin still has resource permissions');
    }

    public function test_delete_without_transfer_cleans_data_and_marks_deleted(): void
    {
        $this->createTransferableData($this->oldAdmin);
        $this->createDeletableData($this->oldAdmin);

        $this->service->deleteCompletelyTransactional($this->oldAdmin);

        $old = $this->oldAdmin;

        $this->assertEquals(UserStatus::Deleted, $old->fresh()->status);
        $this->assertEquals(0, Organization::where('admin', $old->id)->count(), 'Organization still exists after clean');
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
     *
     * NOTE (GDTIS-PT01-FUN-018): this used to call AppPermission::plusPermissions(), a method
     * that does not exist on the enum, so all three tests in this class died with
     * "Call to undefined method" even against a correctly configured PostgreSQL. The audit
     * attributed every non-mail failure to the missing database; that is only half the story.
     * superAdminPermissions() is the enum's real "everything" accessor (all 99 cases minus the
     * two hidden ones), and every value it returns is present in the permissions table because
     * PermissionsSyncSeeder seeds straight from the same enum.
     */
    private function grantPermissions(User $user): void
    {
        $permissions = array_map(fn (AppPermission $p) => $p->value, AppPermission::superAdminPermissions());
        $user->givePermissionTo($permissions);
    }

    /**
     * Creates one instance of every transferable resource, owned by $oldAdmin.
     *
     * NOTE (GDTIS-PT01-FUN-018): this used to create the data through the real API endpoints
     * (POST /api/V1/connectors/out/mqtt, ...). Most of the endpoint families it used DO NOT EXIST
     * in this codebase: routes/api.php has no route for connectors/in/*, connectors/out/* or
     * user/regenerate/apikey. Every one of those calls 404'd, so the two main tests failed
     * regardless of the database.
     *
     * The MODELS and the transfer handlers for all of them are still live code — see
     * App\Providers\UserDeletionServiceProvider, which registers each of these classes with the
     * TransferableRegistry — so the transfer logic is still worth testing. The data is therefore
     * created directly through the models. What is lost versus the original intent is the
     * controller/policy/observer stack; what is gained is a test that actually runs.
     */
    private function createTransferableData(User $oldAdmin): void
    {
        // Dashboard
        $dash = Dashboard::create([
            'name'     => '[TEST] Dashboard',
            'type'     => 'Custom',
            'timezone' => 'UTC',
            'user_id'  => $oldAdmin->id,
            'layout'   => ['lg' => [], 'md' => [], 'sm' => [], 'xs' => [], 'xxs' => []],
        ]);

        // Alarm
        $alarm = Alarm::create([
            'name'     => '[TEST] Alarm',
            'user_id'  => $oldAdmin->id,
            'type'     => 'threshold',
            'function' => 'avg',
            'up'       => false,
            'disabled' => false,
        ]);
        $oldAdmin->giveResourcePermissionsTo(
            \App\Authorization\AppResourcePermission::defaultPermissions(), $alarm, true
        );

        // Action + ActionEmail (old admin email in the destination list). ActionEmail overrides
        // getMorphClass() to return its table name, so actionable_type is 'action_email'.
        $actionEmail = ActionEmail::create([
            'destination' => [$oldAdmin->email],
            'subject'     => '[TEST] Subject',
            'content'     => 'Test body',
        ]);
        Action::create([
            'name'            => '[TEST] Action',
            'user_id'         => $oldAdmin->id,
            'actionable_type' => $actionEmail->getMorphClass(),
            'actionable_id'   => $actionEmail->id,
        ]);

        // EntityGroup
        EntityGroup::create(['name' => '[TEST] Group', 'user_id' => $oldAdmin->id]);

        // ApiKey
        ApiKey::create(['user_id' => $oldAdmin->id, 'key' => Str::random(40)]);

        // Connectors. connectable_* is a polymorphic pair with no foreign key, and the transfer
        // handler (StandardUserIdHandler) only rewrites user_id, so a placeholder target is
        // enough to characterise the transfer.
        InConnector::create([
            'uuid'             => (string) Str::uuid(),
            'name'             => '[TEST] InConnector',
            'type'             => 'loriot',
            'status'           => 'active',
            'user_id'          => $oldAdmin->id,
            'connectable_type' => 'loriot_connector',
            'connectable_id'   => 1,
        ]);

        OutConnector::create([
            'name'             => '[TEST] OutConnector MQTT',
            'type'             => 'mqtt',
            'status'           => 'active',
            'user_id'          => $oldAdmin->id,
            'connectable_type' => 'mqtt_connector',
            'connectable_id'   => 1,
        ]);

        // Keep the dashboard referenced so static analysis does not flag it as unused; it is the
        // Dashboard row the transfer assertions look for.
        $this->assertNotNull($dash->id);
    }

    private function createDeletableData(User $admin): void
    {
        // Preferencable
        $pref = DB::table('preferences')->first();
        if ($pref) {
            Preferencable::create(['user_id' => $admin->id, 'preference_id' => $pref->id, 'value' => 'test']);
        }
    }
}
