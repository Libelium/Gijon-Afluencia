<?php

namespace Tests\Feature\Auth;

use App\Helpers\MfaRoleSyncHelper;
use App\Models\User;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

/**
 * The second factor is a realm role in Keycloak; this checks that the helper maps it onto the
 * right user and reports when it could not. Keycloak is doubled with Http::fake and the user is
 * never persisted, so no database is needed.
 */
class MfaRoleSyncTest extends TestCase
{
    private const KEYCLOAK_URL = 'http://keycloak.invalid';
    private const REALM = 'pid-gijon';
    private const SUBJECT = '11111111-1111-4111-8111-111111111111';

    private const ADMIN_TOKEN = self::KEYCLOAK_URL . '/realms/master/protocol/openid-connect/token';
    private const ROLE = self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/roles/mail-mfa';
    private const MAPPINGS = self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users/' . self::SUBJECT . '/role-mappings/realm';
    private const ADMIN_USERS = self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users*';

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
            'keycloak.mfa_role_name' => 'mail-mfa',
            'logging.default' => 'null',
        ]);
    }

    public function test_enabling_assigns_the_realm_role(): void
    {
        Http::fake([
            self::ADMIN_TOKEN => Http::response(['access_token' => 'admin-token'], 200),
            self::ROLE => Http::response(['id' => 'role-id', 'name' => 'mail-mfa'], 200),
            self::MAPPINGS => Http::response('', 204),
        ]);

        $this->assertTrue((new MfaRoleSyncHelper())->syncUserMfaRole($this->user(self::SUBJECT), true));

        Http::assertSent(fn ($request) => $request->url() === self::MAPPINGS
            && $request->method() === 'POST'
            && $request[0]['name'] === 'mail-mfa');
    }

    public function test_disabling_removes_the_realm_role(): void
    {
        Http::fake([
            self::ADMIN_TOKEN => Http::response(['access_token' => 'admin-token'], 200),
            self::ROLE => Http::response(['id' => 'role-id', 'name' => 'mail-mfa'], 200),
            self::MAPPINGS => Http::response('', 204),
        ]);

        $this->assertTrue((new MfaRoleSyncHelper())->syncUserMfaRole($this->user(self::SUBJECT), false));

        Http::assertSent(fn ($request) => $request->url() === self::MAPPINGS && $request->method() === 'DELETE');
    }

    /** A rejected mapping is reported, so the preference is not saved as if it had worked. */
    public function test_a_failed_mapping_is_reported(): void
    {
        Http::fake([
            self::ADMIN_TOKEN => Http::response(['access_token' => 'admin-token'], 200),
            self::ROLE => Http::response(['id' => 'role-id', 'name' => 'mail-mfa'], 200),
            self::MAPPINGS => Http::response('', 500),
        ]);

        $this->assertFalse((new MfaRoleSyncHelper())->syncUserMfaRole($this->user(self::SUBJECT), true));
    }

    /**
     * A seeded user ('pending' in the column) that the realm does not know by e-mail either:
     * nothing is mapped onto the literal 'pending' and the failure is reported.
     */
    public function test_an_unresolvable_user_is_reported_and_nothing_is_mapped(): void
    {
        Http::fake([
            self::ADMIN_TOKEN => Http::response(['access_token' => 'admin-token'], 200),
            self::ADMIN_USERS => Http::response([], 200),
        ]);

        $this->assertFalse((new MfaRoleSyncHelper())->syncUserMfaRole($this->user('pending'), true));

        Http::assertNotSent(fn ($request) => str_contains($request->url(), '/role-mappings/'));
    }

    private function user(string $keycloakClientId): User
    {
        $user = new User([
            'name' => 'MFA Test',
            'email' => 'mfa.test@example.invalid',
            'enabled' => true,
            'keycloak_client_id' => $keycloakClientId,
        ]);
        $user->id = 1;

        return $user;
    }
}
