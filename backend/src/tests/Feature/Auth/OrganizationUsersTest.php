<?php

namespace Tests\Feature\Auth;

use App\Enums\UserStatus;
use App\Models\Organization;
use App\Models\User;
use Illuminate\Foundation\Testing\DatabaseTransactions;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

/**
 * User management of an organization through the real routes. The database rolls back after
 * each test and Keycloak is doubled with Http::fake.
 */
class OrganizationUsersTest extends TestCase
{
    use DatabaseTransactions;

    protected $connectionsToTransact = ['pgsql', 'pgsql_realtime'];

    private const KEYCLOAK_URL = 'http://keycloak.invalid';
    private const REALM = 'pid-gijon';
    private const NEW_SUBJECT = '33333333-3333-4333-8333-333333333333';
    private const MEMBER_SUBJECT = '44444444-4444-4444-8444-444444444444';

    private User $admin;
    private User $member;
    private Organization $organization;

    protected function setUp(): void
    {
        parent::setUp();

        config([
            'keycloak.url' => self::KEYCLOAK_URL,
            'keycloak.realm' => self::REALM,
            'keycloak.admin.realm' => 'master',
            'keycloak.admin.client' => 'admin-cli',
            'keycloak.admin.username' => 'admin',
            'keycloak.admin.password' => 'admin',
            'keycloak.frontend_client_id' => 'pid-gijon-client',
            'keycloak.frontend_url' => 'http://app.invalid',
            'logging.default' => 'null',
        ]);

        $this->admin = User::create([
            'name' => 'Org Admin',
            'email' => 'org.admin.' . strtolower(Str::random(6)) . '@users-test.local',
            'enabled' => true,
            'status' => UserStatus::Active,
            'keycloak_client_id' => '11111111-1111-4111-8111-' . str_pad((string) random_int(0, 999999999999), 12, '0', STR_PAD_LEFT),
        ]);
        $this->organization = Organization::create(['name' => '[TEST] Users org', 'admin' => $this->admin->id]);
        $this->admin->organization_id = $this->organization->id;
        $this->admin->save();

        $this->member = User::create([
            'name' => 'Member',
            'email' => 'member.' . strtolower(Str::random(6)) . '@users-test.local',
            'enabled' => true,
            'status' => UserStatus::Active,
            'keycloak_client_id' => self::MEMBER_SUBJECT,
            'organization_id' => $this->organization->id,
        ]);
    }

    public function test_the_administrator_lists_the_users_of_the_organization(): void
    {
        User::create([
            'name' => 'Gone',
            'email' => 'gone.' . strtolower(Str::random(6)) . '@users-test.local',
            'status' => UserStatus::Deleted,
            'organization_id' => $this->organization->id,
        ]);

        $response = $this->actingAs($this->admin, 'api')->getJson($this->url());

        $response->assertOk();
        $emails = collect($response->json())->pluck('email');
        $this->assertTrue($emails->contains($this->admin->email));
        $this->assertTrue($emails->contains($this->member->email));
        $this->assertCount(2, $emails, 'a deleted user must not be listed');

        $admin = collect($response->json())->firstWhere('email', $this->admin->email);
        $this->assertTrue($admin['isOrganizationAdmin']);
    }

    public function test_a_member_that_is_not_the_administrator_is_refused(): void
    {
        $this->actingAs($this->member, 'api')->getJson($this->url())->assertForbidden();
    }

    public function test_creating_a_user_registers_it_in_keycloak_and_sends_the_password_email(): void
    {
        Http::fake([
            self::KEYCLOAK_URL . '/realms/master/protocol/openid-connect/token' => Http::response(['access_token' => 'admin-token'], 200),
            self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users/' . self::NEW_SUBJECT . '/execute-actions-email*' => Http::response('', 204),
            self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users/' . self::NEW_SUBJECT => Http::response(['id' => self::NEW_SUBJECT, 'attributes' => []], 200),
            self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users' => Http::response('', 201, [
                'Location' => self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users/' . self::NEW_SUBJECT,
            ]),
        ]);

        $email = 'new.' . strtolower(Str::random(6)) . '@users-test.local';

        $response = $this->actingAs($this->admin, 'api')->postJson($this->url(), [
            'name' => 'New Person',
            'email' => strtoupper($email),
        ]);

        $response->assertCreated();
        $this->assertTrue($response->json('invitationSent'));

        $created = User::where('email', $email)->first();
        $this->assertNotNull($created, 'the e-mail is stored in lower case');
        $this->assertSame(self::NEW_SUBJECT, $created->keycloak_client_id);
        $this->assertSame($this->organization->id, $created->organization_id);
        $this->assertSame($this->admin->id, $created->created_by);

        Http::assertSent(fn ($request) => str_contains($request->url(), '/execute-actions-email'));
    }

    public function test_an_existing_email_is_a_conflict(): void
    {
        Http::fake();

        $this->actingAs($this->admin, 'api')
            ->postJson($this->url(), ['name' => 'Dup', 'email' => strtoupper($this->member->email)])
            ->assertStatus(409);

        Http::assertNothingSent();
    }

    public function test_disabling_a_user_disables_it_in_keycloak_too(): void
    {
        Http::fake([
            self::KEYCLOAK_URL . '/realms/master/protocol/openid-connect/token' => Http::response(['access_token' => 'admin-token'], 200),
            self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users/' . self::MEMBER_SUBJECT => Http::response('', 204),
        ]);

        $response = $this->actingAs($this->admin, 'api')
            ->putJson($this->url() . '/' . $this->member->id . '/enabled', ['enabled' => false]);

        $response->assertOk();
        $this->assertFalse($response->json('enabled'));
        $this->assertSame(UserStatus::Suspended, $this->member->fresh()->status);

        Http::assertSent(fn ($request) => $request->method() === 'PUT'
            && $request->url() === self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users/' . self::MEMBER_SUBJECT
            && $request['enabled'] === false);
    }

    /** Keycloak refusing leaves the local row untouched: both must say the same. */
    public function test_a_keycloak_failure_does_not_change_the_local_state(): void
    {
        Http::fake([
            self::KEYCLOAK_URL . '/realms/master/protocol/openid-connect/token' => Http::response(['access_token' => 'admin-token'], 200),
            self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users/' . self::MEMBER_SUBJECT => Http::response('', 500),
        ]);

        $this->actingAs($this->admin, 'api')
            ->putJson($this->url() . '/' . $this->member->id . '/enabled', ['enabled' => false])
            ->assertStatus(502);

        $this->assertTrue((bool) $this->member->fresh()->enabled);
    }

    public function test_the_administrator_cannot_disable_or_delete_itself(): void
    {
        Http::fake();

        $this->actingAs($this->admin, 'api')
            ->putJson($this->url() . '/' . $this->admin->id . '/enabled', ['enabled' => false])
            ->assertStatus(422);

        $this->actingAs($this->admin, 'api')
            ->deleteJson($this->url() . '/' . $this->admin->id)
            ->assertStatus(422);

        Http::assertNothingSent();
    }

    public function test_a_user_of_another_organization_is_not_reachable(): void
    {
        $outsider = User::create([
            'name' => 'Outsider',
            'email' => 'outsider.' . strtolower(Str::random(6)) . '@users-test.local',
            'status' => UserStatus::Active,
        ]);
        $other = Organization::create(['name' => '[TEST] Other org', 'admin' => $outsider->id]);
        $outsider->organization_id = $other->id;
        $outsider->save();

        Http::fake();

        $this->actingAs($this->admin, 'api')
            ->putJson($this->url() . '/' . $outsider->id . '/enabled', ['enabled' => false])
            ->assertNotFound();
    }

    private function url(): string
    {
        return '/api/V1/organizations/' . $this->organization->id . '/users';
    }
}
