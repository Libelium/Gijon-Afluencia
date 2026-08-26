<?php

namespace App\Http\V1\Controllers;

use App\Models\User;
use App\Http\V1\Controllers\Controller;
use App\Repositories\PreferenceRepository;
use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Illuminate\Support\Facades\Auth;
use App\Models\Preferencable;
use App\Models\Preference;
use App\Helpers\MfaRoleSyncHelper;
use App\Helpers\PreferenceValidator;
use App\Helpers\UserLocaleSyncHelper;

class UserPreferencesController extends Controller
{
    public function getPreferences(int $id): Response
    {

        $user = User::findOrFail($id);

        $this->authorize('read', $user);

        // Step 1: Get the user-defined preferences
        $preferences = PreferenceRepository::getUserPreferences($id);

        return response($preferences, 200);
    }

    public function getPreference(int $id, string $preferenceName): Response
    {

        $user = User::findOrFail($id);

        $this->authorize('read', $user);

        $preferencable = Preferencable::where('user_id', $id)
            ->whereHas('preference', function ($query) use ($preferenceName) {
                $query->where('name', $preferenceName);
            })
            ->first();

        $preferenceValue = null;

        if (!$preferencable) {
            // If the user does not have a preference, check the organization
            $organizationPreference = $user->organization->preferences->where('name', $preferenceName)->first();
            if ($organizationPreference) {
                $preferenceValue = $organizationPreference->value;
            } else {
                // If the organization does not have a preference, get the default
                $preference = Preference::where('name', $preferenceName)->first();
                if (!$preference) {
                    return response('The provided preference is not configurable', 404);
                }

                $preferenceValue = $preference->default_value;
            }
        } else {
            $preferenceValue = $preferencable->value;
        }

        return response(
            [
                'name' => $preferenceName,
                'value' => $preferenceValue,
            ],
            200
        );
    }

    public function updatePreference(int $id, string $preferenceName, Request $request): Response
    {

        $user = User::findOrFail($id);

        $this->authorize('update', $user);

        request()->validate([
            'value' => 'required',
        ]);

        $validation = PreferenceValidator::validate($preferenceName, $request->input('value'));
        if (!$validation['valid']) {
            return response($validation['error'] ?? 'Invalid preference value', 422);
        }

        if ($preferenceName === 'activeMFA') {
            $orgMfaValue = PreferenceRepository::getOrganizationPreference($user->organization, 'activeMFA');
            if ($orgMfaValue === 'true') {
                return response(['error' => 'MFA is enforced by your organization and cannot be modified'], 403);
            }
        }

        $preferencable = Preferencable::where('user_id', $id)
            ->whereHas('preference', function ($query) use ($preferenceName) {
                $query->where('name', $preferenceName);
            })
            ->first();

        if (!$preferencable) {
            // create new preference
            $preferencable = new Preferencable();
            $preferencable->user_id = $id;
            $preference = Preference::where('name', $preferenceName)->first();
            if (!$preference) {
                return response('The provided preference is not configurable', 404);
            }
            $preferencable->preference_id = $preference->id;
        }

        $preferencable->value = $validation['value'];

        if (!$preferencable->save()) {
            return response('Error saving preference', 500);
        }

        if ($preferenceName === 'activeMFA') {
            $mfaHelper = new MfaRoleSyncHelper();
            $mfaHelper->syncUserMfaRole($user, $validation['value'] === 'true');
        }

        // Keep the user's Keycloak locale (email language) in sync with their preference.
        if ($preferenceName === 'language') {
            (new UserLocaleSyncHelper())->syncUserLocale($user);
        }

        return response([
            'name' => $preferencable->preference->name,
            'value' => $preferencable->value,
        ], 200);

    }
}
