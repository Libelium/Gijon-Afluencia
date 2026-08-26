<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Support\Facades\Auth;

class AppendUserIdToResponse
{
    public function handle($request, Closure $next)
    {
        $payload = $request->getContent();

        if (empty($payload)) {
            $payload = json_encode($request->all(), JSON_UNESCAPED_SLASHES);
        }

        $payload = $this->sanitize($payload);

        $response = $next($request);

        if (Auth::check()) {
            $response->headers->set('X-User-Id', Auth::id());
        } else {
            $response->headers->set('X-User-Id', '-');
        }

        $payloadSafe = str_replace('"', "'", $payload);

        // Skip X-Payload header if payload is larger than 8KB to avoid HTTP header size limits
        if (strlen($payloadSafe) <= 8192) {
            $response->headers->set('X-Payload', $payloadSafe);
        }

        return $response; 
    }

    private function sanitize(string $payload): string
    {
        $blacklist = ['password', 'token', 'refreshToken', 'secret', 'key'];

        $data = json_decode($payload, true);

        if (!is_array($data)) {
            return $payload;
        }

        foreach ($blacklist as $item) {
            if (array_key_exists($item, $data)) {
                $data[$item] = '[hidden]';
            }
        }

        return json_encode($data, JSON_UNESCAPED_SLASHES);
    }
}
