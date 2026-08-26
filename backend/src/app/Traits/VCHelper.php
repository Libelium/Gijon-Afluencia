<?php

namespace App\Traits;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Cache;
use Firebase\JWT\JWT;
use Firebase\JWT\JWK;

trait VCHelper
{
    public function exchangeVCCode(string $code, string $redirectUri): array
    {
        $response = Http::asForm()->post(
            config('vc.verifier_host') . config('vc.token_path'),
            [
                'grant_type' => 'authorization_code',
                'code' => $code,
                'redirect_uri' => $redirectUri,
            ]
        );

        if ($response->status() !== 200) {
            return ['status' => $response->status(), 'message' => $response->json()];
        }

        $data = $response->json();

        return [
            'status' => 200,
            'access_token' => $data['access_token'],
            'refresh_token' => $data['refresh_token'] ?? null,
        ];
    }

    public static function getVCJwks(): array
    {
        return Cache::remember('vc_jwks', 3600, function () {
            $response = Http::get(config('vc.verifier_host') . config('vc.jwks_path'));
            return $response->json();
        });
    }

    public static function decodeVCToken(string $token): object
    {
        $jwks = self::getVCJwks();
        $keys = JWK::parseKeySet($jwks, 'RS256');
        return JWT::decode($token, $keys);
    }

    public static function validateVCClaims(object $decoded): ?string
    {
        $vc = $decoded->verifiableCredential ?? null;

        $expectedType = config('vc.credential_type');
        if ($expectedType && ($vc->type ?? null) !== $expectedType) {
            return "VC credential type mismatch: expected {$expectedType}, got " . ($vc->type ?? 'null');
        }

        $expectedTarget = config('vc.role_target');
        if ($expectedTarget) {
            $roles = $vc->credentialSubject->roles ?? [];
            $found = false;
            foreach ($roles as $role) {
                if (($role->target ?? null) === $expectedTarget) {
                    $found = true;
                    break;
                }
            }
            if (!$found) {
                return "VC role target mismatch: expected {$expectedTarget}";
            }
        }

        return null;
    }
}
