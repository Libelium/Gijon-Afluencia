<?php

namespace App\Http\Middleware;

use App\Models\ApiKey;
use App\Models\User;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Symfony\Component\HttpFoundation\Response;

class DeviceManagerAuth
{
    /**
     * This middleware should be used to autenticate Device Manager requests.
     *
     * @param  \Closure(\Illuminate\Http\Request): (\Symfony\Component\HttpFoundation\Response)  $next
     */
    public function handle(Request $request, Closure $next): Response
    {

        $host = $request->header('access-token');
        $apikeyData = ApiKey::with('user')->where('key', $host)->first();
        if (!$apikeyData) {
            return response()->json(['message' => 'Unauthorized'], 401);
        }
        $user = $apikeyData->user;
        Auth::login($user);
        return $next($request);
    }
}
