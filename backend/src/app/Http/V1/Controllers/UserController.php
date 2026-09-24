<?php

namespace App\Http\V1\Controllers;

use App\Http\V1\Requests\Users\UserUpdateRequest;
use App\Models\User;
use App\Http\V1\Resources\UserResource;
use App\Http\V1\Controllers\Controller;
use App\Traits\KeycloakHelper;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Auth;
use Laravel\Sanctum\PersonalAccessToken;

class UserController extends Controller
{

    use KeycloakHelper;
    /**
     * To take detail of current user
     */
    public function show(int $id): Response
    {

        $user = User::findOrFail($id);

        $this->authorize('read', $user);

        return response(new UserResource($user), 200);
    }

    public function getUser(): Response
    {
        $user = Auth::user();
        // no need to authorize, because the user is the same as the logged user

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

    /**
     * Logout user (Revoke the token)
     */
    public function logout(Request $request)
    {
        $user = Auth::user();

        $revoked = $this->revokeSession($this->resolveKeycloakUserId($user), $request->input('refreshToken'));

        // Under the Keycloak guard there is no Sanctum token, but if the request carries one it
        // must go: the local session has to fall even when the remote revocation failed.
        $localToken = $user?->currentAccessToken();
        if ($localToken instanceof PersonalAccessToken) {
            $localToken->delete();
        }

        // A failed revocation and an unidentifiable session (null) are told apart, but in both
        // cases the session is still alive in Keycloak, so neither answers 200.
        if ($revoked === null) {
            return response()->json(
                ['error' => 'The identity provider session could not be identified'],
                502
            );
        }

        if ($revoked === false) {
            return response()->json(
                ['error' => 'The session could not be revoked in the identity provider'],
                502
            );
        }

        return response()->json(['success' => true], 200);
    }
}
