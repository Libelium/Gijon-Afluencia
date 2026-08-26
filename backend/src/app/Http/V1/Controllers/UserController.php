<?php

namespace App\Http\V1\Controllers;

use App\Http\V1\Requests\Users\UserUpdateRequest;
use App\Models\User;
use App\Http\V1\Resources\UserResource;
use App\Http\V1\Controllers\Controller;
use App\Models\AccessAttempt;
use App\Repositories\AccessAttemptRepository;
use App\Repositories\PreferenceRepository;
use App\Traits\KeycloakHelper;
use App\Traits\VCHelper;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Auth;

class UserController extends Controller
{

    use KeycloakHelper;
    use VCHelper;
    /**
     * To take detail of current user
     */
    public function show(int $id): Response
    {

        $user = User::with('lastLogin')->findOrFail($id);

        $this->authorize('read', $user);

        return response(new UserResource($user), 200);
    }

    public function getUser(): Response
    {
        $user = Auth::user();
        // no need to authorize, because the user is the same as the logged user
        $user->load('lastLogin');

        return response(new UserResource($user), 200);
    }

    /**
     * PUT/PATCH Full or partial udpate over the resource
     */
    public function update(int $id, UserUpdateRequest $request): Response
    {
        $user = User::findOrFail($id);

        $this->authorize('update', $user);

        $user->fill($request->only(['name']));

        if (!$user->save()) {
            return response('The operation couldn’t be completed (update)', 500);
        }

        return response(new UserResource($user), 200);
    }

    public function getPublicIp()
    {
        if (!empty($_SERVER['HTTP_CLIENT_IP'])) {
            $ip = $_SERVER['HTTP_CLIENT_IP'];
            return $ip;
        } elseif (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
            $ip = $_SERVER['HTTP_X_FORWARDED_FOR'];
            return $ip;
        } else {
            $ip = $_SERVER['REMOTE_ADDR'];
            return $ip;
        }
    }

    public function login(Request $request)
    {
        $request->validate([
            'username' => 'required',
            'password' => 'required',
        ]);

        $user = User::where('email', strtolower($request->username))->first();

        // Dont use firstOrFail, because we dont want ot inform if the user exists or not
        # First check if the user exists. If not, return an error
        if (!$user) {
            return response()->json(['email' => 'The provided credentials are incorrect'], 401);
        }

        # Once we know the user exists, check if the user is locked or blocked
        if (!$user->enabled) {
            return response()->json(['error' => 'The user is locked'], 401);
        }

        $kcResponse = $this->validateUser($request->username, $request->password);
        $validLogin = $kcResponse['status'] !== 200 ? false : true;

        $preferences = PreferenceRepository::getUserPreferences($user->id);
        $shouldLog = $preferences['accessLogEnabled'] === 'true';
        $maxAccessAttempts = (int) $preferences['maxAccessAttempts'];

        if ($shouldLog || !$validLogin) {
            $this->saveAttempt($request->username, $this->getPublicIp(), $validLogin);
        }

        if ($validLogin) {

            if (!$shouldLog) {
                AccessAttemptRepository::cleanLogsUntilLastSuccess($request->username);
            }

            return response()->json([
                'id' => $user->id,
                'token' => $kcResponse['access_token'],
                'refreshToken' => $kcResponse['refreshToken']
            ]);
        }

        $blockIntervalCheck = config('app.limits.login.block_interval_check_min');

        $shouldLock = AccessAttemptRepository::shouldLock(
            $request->username,
            $maxAccessAttempts,
            $blockIntervalCheck
        );

        if ($shouldLock) {
            $user->enabled = false;
            $user->save();
            return response()->json(['error' => 'The user is locked'], 401);
        }

        // keep the validation format (email =>) just in case for the front end
        return response()->json(['email' => 'The provided credentials are incorrect'], 401);
    }

    public function refreshKcToken(Request $request)
    {
        $request->validate([
            'refreshToken' => 'required'
        ]);

        $kcResponse = $this->refreshToken($request->refreshToken);

        if ($kcResponse['status'] !== 200) {
            return response()->json(['error' => 'Invalid refresh token'], 401);
        }

        return response()->json([
            'token' => $kcResponse['access_token'],
            'refreshToken' => $kcResponse['refreshToken']
        ]);
    }

    /**
     * Logout user (Revoke the token)
     */
    public function logout(Request $request)
    {
        $user = Auth::user();
        // $user->currentAccessToken()->delete();

        return response()->json(['success' => true], 200);
    }

    /**
     * Logout user from all sessions (Revoke all tokens)
     */
    private function saveAttempt(string $email, string $ip, bool $success)
    {
        $accessAttempt = new AccessAttempt([
            'email' => $email,
            'ip' => $ip,
            'success' => $success
        ]);
        $accessAttempt->save();
    }
}
