<?php

namespace Tests\Feature\Auth;

use App\Guards\ExtendedKeycloakGuard;
use Illuminate\Auth\AuthenticationException;
use Illuminate\Support\Facades\Auth;
use ReflectionMethod;
use Tests\TestCase;

/**
  * The public key belongs to the whole realm, so without a list of accepted issuing clients
  * any token from the realm is good enough. The real guard is exercised: decoding a token
  * would need a key pair and adds nothing to what is checked here.
  */
class AllowedClientsTest extends TestCase
{
    public function test_a_declared_client_is_accepted(): void
    {
        config(['keycloak.allowed_clients' => 'pid-gijon-client,pid-gijon-mcp-cli']);

        $this->assertTrue($this->clientIsAllowed('pid-gijon-mcp-cli'));
    }

    public function test_a_client_outside_the_list_is_rejected(): void
    {
        config(['keycloak.allowed_clients' => 'pid-gijon-client']);

        $this->assertFalse($this->clientIsAllowed('dlm-client'));
        $this->assertFalse($this->clientIsAllowed(null));
    }

    /** The clients that configuration itself names are, by definition, callers of this API. */
    public function test_the_configured_clients_are_always_allowed(): void
    {
        config([
            'keycloak.allowed_clients' => 'pid-gijon-client',
            'keycloak.client_id' => 'laravel-backend',
            'keycloak.frontend_client_id' => 'change-password-client',
            'provisioning.self_provisioning_clients' => ['pid-gijon-mcp-cli'],
        ]);

        $this->assertTrue($this->clientIsAllowed('laravel-backend'));
        $this->assertTrue($this->clientIsAllowed('change-password-client'));
        $this->assertTrue($this->clientIsAllowed('pid-gijon-mcp-cli'));
    }

    /** An empty list keeps the historical behaviour, so deployments without the variable survive. */
    public function test_an_empty_list_does_not_restrict(): void
    {
        config(['keycloak.allowed_clients' => '']);

        $this->assertTrue($this->clientIsAllowed('dlm-client'));
        $this->assertTrue($this->clientIsAllowed(null));
    }

    /** A token with no azp cannot prove which client it came from, so it does not pass. */
    public function test_a_token_without_azp_is_rejected(): void
    {
        config(['keycloak.allowed_clients' => 'pid-gijon-client']);

        $this->expectException(AuthenticationException::class);

        $method = new ReflectionMethod(ExtendedKeycloakGuard::class, 'validateIssuingClient');
        $method->setAccessible(true);
        $method->invoke($this->guard());
    }

    private function clientIsAllowed(?string $azp): bool
    {
        $method = new ReflectionMethod(ExtendedKeycloakGuard::class, 'clientIsAllowed');
        $method->setAccessible(true);

        return $method->invoke($this->guard(), $azp);
    }

    private function guard(): ExtendedKeycloakGuard
    {
        return new ExtendedKeycloakGuard(Auth::createUserProvider('users'), request());
    }
}
