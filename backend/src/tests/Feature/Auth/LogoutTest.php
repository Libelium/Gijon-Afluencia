<?php

namespace Tests\Feature\Auth;

use App\Http\V1\Controllers\UserController;
use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

/**
  * The controller is called directly and the user is never persisted, so this class needs
  * no database; Keycloak is doubled with Http::fake.
  */
class LogoutTest extends TestCase
{
    private const KEYCLOAK_URL = 'http://keycloak.invalid';
    private const REALM = 'pid-gijon';
    private const OWN_SUBJECT = '11111111-1111-4111-8111-111111111111';
    private const OTHER_SUBJECT = '22222222-2222-4222-8222-222222222222';

    private const OIDC_LOGOUT = self::KEYCLOAK_URL . '/realms/' . self::REALM . '/protocol/openid-connect/logout';
    private const ADMIN_TOKEN = self::KEYCLOAK_URL . '/realms/master/protocol/openid-connect/token';
    private const ADMIN_LOGOUT = self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users/*/logout';
    private const ADMIN_USERS = self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users*';

    protected function setUp(): void
    {
        parent::setUp();

        config([
            'keycloak.url' => self::KEYCLOAK_URL,
            'keycloak.realm' => self::REALM,
            'keycloak.client_id' => 'pid-api',
            'keycloak.client_secret' => 'testing',
            'keycloak.admin.realm' => 'master',
            'keycloak.admin.client' => 'admin-cli',
            'keycloak.admin.username' => 'admin',
            'keycloak.admin.password' => 'admin',
            // The foreign-token warning is logged; the default channel would write to
            // storage/logs during the suite.
            'logging.default' => 'null',
        ]);
    }

    public function test_a_successful_revocation_answers_200(): void
    {
        Http::fake([self::OIDC_LOGOUT => Http::response('', 204)]);

        $response = $this->logout($this->user(self::OWN_SUBJECT), $this->refreshTokenFor(self::OWN_SUBJECT));

        $this->assertSame(200, $response->getStatusCode());
        $this->assertSame(['success' => true], $this->payload($response));

        Http::assertSent(fn ($request) => $request->url() === self::OIDC_LOGOUT
            && $request['refresh_token'] === $this->refreshTokenFor(self::OWN_SUBJECT));
    }

    /** If Keycloak does not revoke, the session is still alive there: 200 is not an option. */
    public function test_a_failed_revocation_answers_502(): void
    {
        Http::fake([
            self::OIDC_LOGOUT => Http::response(['error' => 'invalid_grant'], 400),
            self::ADMIN_TOKEN => Http::response(['access_token' => 'admin-token'], 200),
            self::ADMIN_LOGOUT => Http::response('', 500),
        ]);

        $response = $this->logout($this->user(self::OWN_SUBJECT), $this->refreshTokenFor(self::OWN_SUBJECT));

        $this->assertSame(502, $response->getStatusCode());
        $this->assertArrayHasKey('error', $this->payload($response));
    }

    /**
     * A seeded user ('pending' in the column) that the realm does not know by e-mail either:
     * there is no identifier to revoke with, and that is not a 200.
     */
    public function test_a_session_that_cannot_be_identified_answers_502(): void
    {
        Http::fake([
            self::ADMIN_TOKEN => Http::response(['access_token' => 'admin-token'], 200),
            self::ADMIN_USERS => Http::response([], 200),
        ]);

        $response = $this->logout($this->user('pending'));

        $this->assertSame(502, $response->getStatusCode());
        $this->assertArrayHasKey('error', $this->payload($response));
        Http::assertNotSent(fn ($request) => $request->url() === self::OIDC_LOGOUT);
    }

    /**
     * The refresh token comes in the request body, so someone else's would close their
     * session. It is ignored (even though the OIDC logout would have answered 204) and the
     * authenticated user's session is revoked through the admin path instead.
     */
    public function test_a_refresh_token_from_another_user_is_ignored(): void
    {
        Http::fake([
            self::OIDC_LOGOUT => Http::response('', 204),
            self::ADMIN_TOKEN => Http::response(['access_token' => 'admin-token'], 200),
            self::ADMIN_LOGOUT => Http::response('', 204),
        ]);

        $response = $this->logout($this->user(self::OWN_SUBJECT), $this->refreshTokenFor(self::OTHER_SUBJECT));

        $this->assertSame(200, $response->getStatusCode());

        Http::assertNotSent(fn ($request) => $request->url() === self::OIDC_LOGOUT);
        Http::assertSent(fn ($request) => $request->url()
            === self::KEYCLOAK_URL . '/admin/realms/' . self::REALM . '/users/' . self::OWN_SUBJECT . '/logout');
    }

    private function logout(User $user, ?string $refreshToken = null)
    {
        Auth::guard('api')->setUser($user);

        $request = Request::create(
            '/api/V1/logout',
            'POST',
            $refreshToken === null ? [] : ['refreshToken' => $refreshToken]
        );

        return app(UserController::class)->logout($request);
    }

    private function user(string $keycloakClientId): User
    {
        $user = new User([
            'name' => 'Logout Test',
            'email' => 'logout.test@example.invalid',
            'enabled' => true,
            'keycloak_client_id' => $keycloakClientId,
        ]);
        $user->id = 1;

        return $user;
    }

    /** A JWT-shaped refresh token: only 'sub' is read, the signature is not checked. */
    private function refreshTokenFor(string $subject): string
    {
        $segment = fn (array $claims): string => rtrim(
            strtr(base64_encode(json_encode($claims)), '+/', '-_'),
            '='
        );

        return $segment(['alg' => 'HS256', 'typ' => 'Refresh'])
            . '.' . $segment(['sub' => $subject, 'typ' => 'Refresh'])
            . '.signature';
    }

    private function payload($response): array
    {
        return json_decode((string) $response->getContent(), true);
    }
}
