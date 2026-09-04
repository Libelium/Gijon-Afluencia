<?php

namespace App\Guards;

use App\Services\UserProvisioningService;
use Illuminate\Auth\AuthenticationException;
use Illuminate\Contracts\Auth\Authenticatable;
use Illuminate\Support\Facades\Log;
use KeycloakGuard\Exceptions\UserNotFoundException;
use KeycloakGuard\KeycloakGuard;

class ExtendedKeycloakGuard extends KeycloakGuard
{
    public function login(Authenticatable $user)
    {
        $this->setUser($user);
    }

    public function setUser(Authenticatable $user)
    {
        $this->user = $user;
        return $this;
    }

    /**
     * Resolve the local user; JIT-provision self-registered identities from allowed clients.
     */
    public function validate(array $credentials = [])
    {
        $this->validateIssuingClient();

        if (!$this->config['load_user_from_database']) {
            return parent::validate($credentials);
        }

        $this->validateResources();

        $methodOnProvider = $this->config['user_provider_custom_retrieve_method'] ?? null;
        $user = $methodOnProvider
            ? $this->provider->{$methodOnProvider}($this->decodedToken, $credentials)
            : $this->provider->retrieveByCredentials($credentials);

        if (!$user && ($profile = $this->selfProvisioningProfile()) !== null) {
            $user = UserProvisioningService::ensureUserProvisioned($this->decodedToken, $profile);
        }

        if (!$user) {
            throw new UserNotFoundException('User not found. Credentials: ' . json_encode($credentials));
        }

        $this->setUser($user);

        return true;
    }

    /**
     * Rejects tokens issued by realm clients other than this API's: the signature is shared by
     * the whole realm, so without this any realm token with a known email would pass.
     */
    protected function validateIssuingClient(): void
    {
        $azp = $this->decodedToken->azp ?? null;

        if ($this->clientIsAllowed(is_string($azp) ? $azp : null)) {
            return;
        }

        Log::warning('keycloak.token.client_not_allowed', ['azp' => $azp]);

        throw new AuthenticationException();
    }

    /**
     * An empty list means no restriction, the historical behaviour, so deployments that never
     * declared it keep working. The clients named in the configuration always pass.
     */
    protected function clientIsAllowed(?string $azp): bool
    {
        $declared = array_values(array_filter(array_map(
            'trim',
            explode(',', (string) config('keycloak.allowed_clients'))
        )));

        if ($declared === []) {
            return true;
        }

        $allowed = array_merge($declared, array_filter([
            config('keycloak.client_id'),
            config('keycloak.frontend_client_id'),
        ]), config('provisioning.self_provisioning_clients', []));

        return $azp !== null && in_array($azp, $allowed, true);
    }

    /**
     * Provisioning profile for the token's client (azp), or null if the client is not allowed.
     * Allowed clients are a flat list; org + contract are global (citizen org + guest contract).
     */
    protected function selfProvisioningProfile(): ?array
    {
        $azp = $this->decodedToken->azp ?? null;
        if ($azp === null) {
            return null;
        }

        $clients = config('provisioning.self_provisioning_clients', []);
        if (!in_array($azp, $clients, true)) {
            return null;
        }

        // Citizen organization from SELF_PROVISIONING_ORGANIZATION ({"name": id}) — take the id.
        $org = config('provisioning.self_provisioning_organization', []);
        $organizationId = is_array($org) ? (array_values($org)[0] ?? null) : null;

        return [
            'organization_id' => $organizationId,
            'role' => config('provisioning.self_provisioning_role'),
        ];
    }
}
