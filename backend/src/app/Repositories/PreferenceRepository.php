<?php

namespace App\Repositories;

use App\Models\Preference;
use App\Models\Preferencable;
use App\Models\User;
use App\Models\Organization;
use App\Models\FiwareScope;
use Illuminate\Support\Facades\Auth;

class PreferenceRepository
{
    public static function getUserPreferences(int $id = null)
    {
        if ($id) {
            $user = User::find($id);
        } else {
            $user = Auth::user();
        }

        // Step 1: Get the user-defined preferences
        $preferences = Preferencable::where('user_id', $user->id)->with([
            'preference' => function ($query) {
                $query->select('id', 'name');
            }
        ])->get();

        // transform into key value
        $keyValuePreferences = [];
        foreach ($preferences as $preference) {
            $keyValuePreferences[$preference->preference->name] = $preference->value;
        }

        // Step 2: Get the organization preferences
        $organizationPreferences = $user->organization->preferences;

        foreach ($organizationPreferences as $organizationPreference) {
            if (!array_key_exists($organizationPreference->name, $keyValuePreferences)) {
                $keyValuePreferences[$organizationPreference->name] = $organizationPreference->pivot->value;
            }
        }

        //Step 3: Get the default preferences
        $defaultPreferences = Preference::all();

        foreach ($defaultPreferences as $defaultPreference) {
            if (!array_key_exists($defaultPreference->name, $keyValuePreferences)) {
                $keyValuePreferences[$defaultPreference->name] = $defaultPreference->default_value;
            }
        }


        return $keyValuePreferences;
    }

    public static function getUserPreference(User $user, string $prefName): string | null
    {
        $preference = Preference::where('name', $prefName)->first();

        if (!$preference) {
            throw new \Exception("Preference with name $prefName not found");
        }

        $userPref = Preferencable::where('user_id', $user->id)
            ->where('preference_id', $preference->id)
            ->first();

        if ($userPref) {
            return $userPref->value;
        }

        $user->loadMissing('organization');

        $organizationPreference = $user->organization->preferences()
            ->where('name', $prefName)
            ->first();

        if ($organizationPreference) {
            return $organizationPreference->pivot->value;
        }

        return $preference->default_value;
    }

    public static function getOrganizationPreference(Organization $org, string $prefName): string
    {
        $preference = Preference::where('name', $prefName)->first();

        if (!$preference) {
            throw new \Exception("Preference with name $prefName not found");
        }

        $organizationPreference = $org->preferences()
            ->where('name', $prefName)
            ->first();

        if ($organizationPreference) {
            return $organizationPreference->pivot->value;
        }

        return $preference->default_value;
    }

    public static function getMainScope(User $user): FiwareScope
    {
        $scopeId = PreferenceRepository::getUserPreference($user, "mainScope");

        if ($scopeId == null) {
            return null;
        }

        $scope = FiwareScope::with('tenant')->find($scopeId);

        if ($scope == null) {
            throw new \Exception("Scope with id $scopeId not found, "
                . "user " . $user->id . " may have an invalid mainScope preference");
        }

        return $scope;
    }
}
