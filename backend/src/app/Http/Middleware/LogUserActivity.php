<?php

namespace App\Http\Middleware;

use App\Models\User;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class LogUserActivity
{
    /**
     * This middleware should be used to register all the necesary activity for the user.
     *
     * @param  \Closure(\Illuminate\Http\Request): (\Symfony\Component\HttpFoundation\Response)  $next
     */
    public function handle(Request $request, Closure $next): Response
    {
        if ($request->user()) {
            self::logLastActivity($request->user());
        }
        return $next($request);
    }


    /**
     * To log the date of every request to the backend.
     */
    private function logLastActivity(User $user): void
    {
        $user->last_activity = now();
        $user->save();
    }
}
