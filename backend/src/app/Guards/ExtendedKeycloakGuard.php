<?php

namespace App\Guards;

use App\Services\UserProvisioningService;
use Illuminate\Contracts\Auth\Authenticatable;
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
