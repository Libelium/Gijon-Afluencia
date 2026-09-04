<?php

namespace App\Traits;

use Illuminate\Support\Facades\Http;
use Illuminate\Http\Response;
use Symfony\Component\HttpKernel\Exception\HttpException;
use Illuminate\Support\Facades\Log;

trait KeycloakHelper
{
    public function validateUserWithCode(string $code): array
    {
        if ($code === null) {
            return ['status' => 400, 'message' => "Code not provided"];
        }

        $response = Http::asForm()->post(config('keycloak.url') . '/realms/' . config('keycloak.realm') . '/protocol/openid-connect/token', [
            'client_id' => config('keycloak.client_id'),
            'client_secret' => config('keycloak.client_secret'),
            'code' => $code,
            'grant_type' => 'authorization_code',
            'redirect_uri' => config('keycloak.redirect_uri')
        ]);

        if ($response->status() !== 200) {
            return ['status' => $response->status(), 'message' => $response->json()];
        }
        return ['status' => $response->status(), 'access_token' => $response->json()['access_token'], 'refreshToken' => $response->json()['refresh_token']];
    }

    private function getAdminToken()
    {
        $response = Http::asForm()->post(config('keycloak.url') . '/realms/' . config('keycloak.admin.realm') . '/protocol/openid-connect/token', [
            'client_id' => config('keycloak.admin.client'),
            'username' => config('keycloak.admin.username'),
            'password' => config('keycloak.admin.password'),
            'grant_type' => 'password'
        ]);

        try {
            return $response->json()['access_token'];
        } catch (\Exception $e) {
            return false;
        }
    }

    private static function getImpersonationToken()
    {
        $response = Http::asForm()->post(config('keycloak.impersonation.url') . '/realms/' . config('keycloak.impersonation.realm') . '/protocol/openid-connect/token', [
            'client_id' => config('keycloak.impersonation.client'),
            'client_secret' => config('keycloak.impersonation.secret'),
            'username' => config('keycloak.impersonation.username'),
            'password' => config('keycloak.impersonation.password'),
            'grant_type' => 'password'
        ]);

        try {
            return $response->json()['access_token'];
        } catch (\Exception $e) {
            return false;
        }
    }

    /**
     * Deletes a user from Keycloak.
     *
     * @param string $user_id
     *
     * @return bool
     */
    public function deleteUser(string $user_id): bool
    {
        if ($user_id === null) {
            return false;
        }
        try {
            $token = $this->getAdminToken();
            $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/users/' . $user_id;

            $response = Http::withToken($token)->delete($url);

            if ($response->status() !== 204) {
                Log::error('keycloak.user.delete', ['user' => $user_id, 'status' => $response->status()]);
                return false;
            }
        } catch (\Exception $e) {
            Log::error('keycloak.user.delete.exception', ['user' => $user_id, 'error' => $e->getMessage()]);
            return false;
        }
        return true;
    }

    // We don't want to delete the user, just disable it
    public function disableUser(string $user_id): bool
    {
        if ($user_id === null) {
            return "User not provided";
        }
        try {
            $token = $this->getAdminToken();
            $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/users/' . $user_id;

            $response = Http::withToken($token)->put($url, [
                'enabled' => false
            ]);

            if ($response->status() > 299 || $response->status() < 200) {
                return false;
            }
        } catch (\Exception $e) {
            return false;
        }
        return true;
    }

    public function enableUser(string $user_id): bool
    {
        if ($user_id === null) {
            return "User not provided";
        }
        try {
            $token = $this->getAdminToken();
            $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/users/' . $user_id;

            $response = Http::withToken($token)->put($url, [
                'enabled' => true
            ]);

            if ($response->status() > 299 || $response->status() < 200) {
                return false;
            }
        } catch (\Exception $e) {
            return false;
        }
        return true;
    }

    /**
     * Set the user's `locale` attribute in Keycloak. Keycloak uses this attribute to pick
     * the email theme language (with the realm default as the final fallback).
     *
     * The full current representation is read and PUT back with the locale merged in: a
     * partial body (just `attributes`) is re-validated against the user profile and rejected
     * (400) when required fields like email/firstName aren't present in the request.
     */
    public function setUserLocale(string $user_id, string $locale): bool
    {
        if (empty($user_id) || empty($locale)) {
            return false;
        }
        try {
            $token = $this->getAdminToken();
            $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/users/' . $user_id;

            // Read the full representation first, then merge the locale and PUT it all back.
            $current = Http::withToken($token)->get($url);
            if ($current->status() > 299 || $current->status() < 200) {
                Log::error('keycloak.user.locale.get', ['user' => $user_id, 'status' => $current->status()]);
                return false;
            }

            $user = $current->json();
            $attributes = $user['attributes'] ?? [];
            $attributes['locale'] = [$locale];
            $user['attributes'] = $attributes;

            $response = Http::withToken($token)->put($url, $user);

            if ($response->status() > 299 || $response->status() < 200) {
                Log::error('keycloak.user.locale', ['user' => $user_id, 'locale' => $locale, 'status' => $response->status()]);
                return false;
            }
        } catch (\Exception $e) {
            Log::error('keycloak.user.locale.exception', ['user' => $user_id, 'error' => $e->getMessage()]);
            return false;
        }
        return true;
    }

    /**
     * The OIDC logout is tried first when the caller owns the refresh token, as it closes only
     * that session; the administrative route is the fallback. Returns null when no route was
     * applicable, so the caller does not read it as a failed revocation.
     */
    public function revokeSession(?string $keycloakUserId, ?string $refreshToken): ?bool
    {
        if ($refreshToken && !$this->ownsRefreshToken($keycloakUserId, $refreshToken)) {
            $refreshToken = null;
        }

        if ($refreshToken && $this->logoutWithRefreshToken($refreshToken)) {
            return true;
        }

        // The administrative route needs the user's 'sub'; anything else (such as the 'pending'
        // seeded users start with) just returns a 404.
        if (!$this->isKeycloakUserId($keycloakUserId)) {
            Log::warning('keycloak.session.revoke.no_user_id', ['user' => $keycloakUserId]);

            return $refreshToken ? false : null;
        }

        return $this->logoutUserSessions($keycloakUserId);
    }

    /**
     * The refresh token arrives in the request body, so it is only used when its 'sub' is the
     * authenticated user's: another user's token would close someone else's session. The
     * signature needs no checking, Keycloak itself rejects a forged token on revocation.
     */
    private function ownsRefreshToken(?string $keycloakUserId, ?string $refreshToken): bool
    {
        if ($refreshToken === null || !$this->isKeycloakUserId($keycloakUserId)) {
            return false;
        }

        $subject = $this->jwtSubject($refreshToken);

        if ($subject !== $keycloakUserId) {
            Log::warning('keycloak.session.revoke.refresh_token_mismatch', ['user' => $keycloakUserId]);

            return false;
        }

        return true;
    }

    private function jwtSubject(string $token): ?string
    {
        $payload = explode('.', $token)[1] ?? '';
        $claims = json_decode((string) base64_decode(strtr($payload, '-_', '+/'), true), true);
        $subject = is_array($claims) ? ($claims['sub'] ?? null) : null;

        return is_string($subject) ? $subject : null;
    }

    private function isKeycloakUserId(?string $keycloakUserId): bool
    {
        return $keycloakUserId !== null
            && preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i', $keycloakUserId) === 1;
    }

    /**
     * Username is tried as well as email: in this realm the username is the e-mail itself, and
     * accounts created by hand do not always carry the email attribute.
     */
    public function findKeycloakUserIdByEmail(?string $email): ?string
    {
        if (empty($email)) {
            return null;
        }

        return $this->queryKeycloakUserId(['email' => $email, 'exact' => 'true'])
            ?? $this->queryKeycloakUserId(['username' => strtolower($email), 'exact' => 'true']);
    }

    private function queryKeycloakUserId(array $criteria): ?string
    {
        try {
            $token = $this->getAdminToken();

            if (!$token) {
                return null;
            }

            $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/users';

            $response = Http::withToken($token)->get($url, $criteria);

            if (!$response->successful()) {
                Log::error('keycloak.user.find', ['status' => $response->status()]);

                return null;
            }

            $id = $response->json()[0]['id'] ?? null;
        } catch (\Exception $e) {
            Log::error('keycloak.user.find.exception', ['error' => $e->getMessage()]);

            return null;
        }

        return is_string($id) && $this->isKeycloakUserId($id) ? $id : null;
    }

    private function logoutWithRefreshToken(string $refreshToken): bool
    {
        try {
            $url = config('keycloak.url') . '/realms/' . config('keycloak.realm') . '/protocol/openid-connect/logout';

            $response = Http::asForm()->post($url, [
                'client_id' => config('keycloak.client_id'),
                'client_secret' => config('keycloak.client_secret'),
                'refresh_token' => $refreshToken,
            ]);
        } catch (\Exception $e) {
            Log::error('keycloak.session.logout.exception', ['error' => $e->getMessage()]);
            return false;
        }

        if (!$response->successful()) {
            Log::warning('keycloak.session.logout', ['status' => $response->status()]);
            return false;
        }

        return true;
    }

    private function logoutUserSessions(string $keycloakUserId): bool
    {
        try {
            $token = $this->getAdminToken();
            $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/users/' . $keycloakUserId . '/logout';

            $response = Http::withToken($token)->post($url);
        } catch (\Exception $e) {
            Log::error('keycloak.session.admin_logout.exception', ['user' => $keycloakUserId, 'error' => $e->getMessage()]);
            return false;
        }

        if (!$response->successful()) {
            Log::error('keycloak.session.admin_logout', ['user' => $keycloakUserId, 'status' => $response->status()]);
            return false;
        }

        return true;
    }

    private function generateRandomPassword(int $length = 16): string
    {
        $upper   = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        $lower   = 'abcdefghijklmnopqrstuvwxyz';
        $digits  = '0123456789';
        $special = '!@#$%^&*()-_=+[]{}';
        $all     = $upper . $lower . $digits . $special;

        // Keep within Keycloak policy bounds: length(8) .. maxLength(30)
        $length = max(8, min(30, $length));

        $pick = fn (string $set): string => $set[random_int(0, strlen($set) - 1)];

        // Guarantee at least one char from each required category, then fill the rest
        $required = array_map($pick, [$upper, $lower, $digits, $special]);
        $filler   = array_map($pick, array_fill(0, $length - count($required), $all));
        $chars    = array_merge($required, $filler);

        // Cryptographically secure shuffle so the guaranteed chars are not at fixed positions
        $keys = array_map(fn (): int => random_int(PHP_INT_MIN, PHP_INT_MAX), $chars);
        array_multisort($keys, $chars);

        return implode('', $chars);
    }

    public function createKeycloakUser(string $name, string $email, string|null $password = null): string
    {
        if ($password === null) {
            $password = $this->generateRandomPassword();
        }
        $token = $this->getAdminToken();

        $response = Http::withToken($token)->post(config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/users', [
            "username" => $email,
            'firstName' => $name,
            'email' => $email,
            'emailVerified' => true,
            'enabled' => true,
            'credentials' => [
                [
                    'type' => 'password',
                    'value' => $password,
                    'temporary' => false
                ]
            ]
        ]);

        if ($response->status() !== 201) {
            $status = $response->status();
            $data   = $response->json();
            $msg    = is_array($data)
                ? ($data['error_description'] ?? $data['errorMessage'] ?? $data['message'] ?? null)
                : null;
            $msg    = $msg ?? trim((string) $response->body()) ?: 'Keycloak user creation failed';

            Log::error('keycloak.user.create', ['status' => $status, 'message' => $msg]);
            throw new HttpException($status, $msg);
        }

        $location = explode('/', $response->header('Location'));

        $client_id = $location[count($location) - 1];

        return $client_id;
    }

    public static function tokenExchange(string $userToImpersonate): array
    {
        $token = self::getImpersonationToken();
        $response = Http::asForm()->post(config('keycloak.impersonation.url') . '/realms/' . config('keycloak.impersonation.realm') . '/protocol/openid-connect/token', [
            'grant_type' => 'urn:ietf:params:oauth:grant-type:token-exchange',
            'client_id' => config('keycloak.impersonation.client'),
            'client_secret' => config('keycloak.impersonation.secret'),
            'subject_token' => $token,
            'requested_subject' => $userToImpersonate,
        ]);
        if ($response->status() !== 200) {
            return ['status' => $response->status(), 'message' => $response->json()];
        }
        return ['status' => $response->status(), 'accessToken' => $response->json()['access_token'], 'refreshToken' => $response->json()['refresh_token']];
    }

   public function getRealmRole(string $roleName): ?array
    {
        try {
            $token = $this->getAdminToken();
            $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/roles/' . $roleName;

            $response = Http::withToken($token)->get($url);

            if ($response->status() !== 200) {
                return null;
            }

            return $response->json();
        } catch (\Exception $e) {
            Log::error('keycloak.role.get.exception', ['role' => $roleName, 'error' => $e->getMessage()]);
            return null;
        }
    }

    public function assignRealmRoleToUser(string $userId, string $roleName): bool
    {
        try {
            $token = $this->getAdminToken();
            $role = $this->getRealmRole($roleName);

            if (!$role) {
                Log::error('keycloak.role.assign', ['user' => $userId, 'role' => $roleName, 'error' => 'Role not found']);
                return false;
            }

            $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/users/' . $userId . '/role-mappings/realm';

            $response = Http::withToken($token)->post($url, [
                [
                    'id' => $role['id'],
                    'name' => $role['name'],
                ]
            ]);

            if ($response->status() !== 204) {
                Log::error('keycloak.role.assign', ['user' => $userId, 'role' => $roleName, 'status' => $response->status()]);
                return false;
            }

            return true;
        } catch (\Exception $e) {
            Log::error('keycloak.role.assign.exception', ['user' => $userId, 'role' => $roleName, 'error' => $e->getMessage()]);
            return false;
        }
    }

    public function removeRealmRoleFromUser(string $userId, string $roleName): bool
    {
        try {
            $token = $this->getAdminToken();
            $role = $this->getRealmRole($roleName);

            if (!$role) {
                Log::error('keycloak.role.remove', ['user' => $userId, 'role' => $roleName, 'error' => 'Role not found']);
                return false;
            }

            $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/users/' . $userId . '/role-mappings/realm';

            $response = Http::withToken($token)->delete($url, [
                [
                    'id' => $role['id'],
                    'name' => $role['name'],
                ]
            ]);

            if ($response->status() !== 204) {
                Log::error('keycloak.role.remove', ['user' => $userId, 'role' => $roleName, 'status' => $response->status()]);
                return false;
            }

            return true;
        } catch (\Exception $e) {
            Log::error('keycloak.role.remove.exception', ['user' => $userId, 'role' => $roleName, 'error' => $e->getMessage()]);
            return false;
        }
    }

    public function getUsersLastLogin(array $userIds): array
    {
        $results = [];
        $token = $this->getAdminToken();

        if (!$token) {
            Log::error('keycloak.users.lastlogin', ['error' => 'Failed to get admin token']);
            return $results;
        }

        $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm') . '/events';

        foreach ($userIds as $userId) {
            try {
                $response = Http::withToken($token)->get($url, [
                    'user' => $userId,
                    'type' => 'LOGIN',
                    'max' => 1,
                ]);

                if ($response->status() !== 200) {
                    $results[$userId] = null;
                    continue;
                }

                $events = $response->json();

                if (empty($events)) {
                    $results[$userId] = null;
                    continue;
                }

                $event = $events[0];

                $results[$userId] = [
                    'time' => $event['time'] ?? null,
                    'datetime' => isset($event['time']) ? date('Y-m-d H:i:s', $event['time'] / 1000) : null,
                    'ip' => $event['ipAddress'] ?? null,
                    'userId' => $event['userId'] ?? null,
                ];
            } catch (\Exception $e) {
                Log::error('keycloak.users.lastlogin.exception', ['user' => $userId, 'error' => $e->getMessage()]);
                $results[$userId] = null;
            }
        }

        return $results;
    }

    public function sendKeycloakResetPasswordEmail(string $keycloakUserId): bool
    {
        $token = $this->getAdminToken();

        if (!$token) {
            return false;
        }
        // Currently only UPDATE_PASSWORD is sent, so Keycloak redirects the user
        // directly to the reset password screen. If multiple actions were passed,
        // Keycloak would show an intermediate screen listing all pending actions first.  
        $url = config('keycloak.url') . '/admin/realms/' . config('keycloak.realm')
            . '/users/' . $keycloakUserId . '/execute-actions-email'
            . '?client_id=' . config('keycloak.frontend_client_id') . '&redirect_uri=' . urlencode(config('keycloak.frontend_url'));

        $response = Http::withToken($token)->put($url, ['UPDATE_PASSWORD']);
        return $response->successful();
    }
}
