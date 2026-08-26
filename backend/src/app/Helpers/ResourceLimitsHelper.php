<?php

namespace App\Helpers;

use App\Models\User;
use App\Models\OrganizationResourceLimit;
use App\Models\ResourceLimit;
use App\Models\UserResourceLimit;
use App\Contracts\Limitable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\Relation;
use Illuminate\Support\Facades\Schema;
use Exception;
use Illuminate\Support\Facades\DB;

class ResourceLimitsHelper
{
    /**
     * Check if a user can create a new resource of a specific type.
     *
     * This method determines the user's effective limit, counts their current usage
     * of the resource at the correct scope (user, organization, etc.), and returns
     * true if their usage is below the limit.
     *
     * @param User $user The user attempting to create the resource.
     * @param string $resourceType The identifier for the resource type (e.g., 'projects', 'servers').
     * @return bool True if the user can create the resource, false otherwise.
     * @throws Exception If the resourceType cannot be mapped to a model for counting.
     */
    public static function canCreate(User $user, string $resourceType): bool
    {
        $limitDetails = self::getEffectiveLimit($user, $resourceType);

        // If no limit is defined at any level, creation is permitted.
        if (is_null($limitDetails)) {
            return true;
        }

        $limit = $limitDetails['value'];
        $scope = $limitDetails['scope'];

        // Get the current count of the resource based on the limit's scope.
        $currentUsage = self::getCurrentUsage($user, $resourceType, $scope);


        return $currentUsage < $limit;
    }

    /**
     * Maps a resource type string to its corresponding Eloquent model class.
     *
     * Resolves via the morph map first, then checks against an explicit allowlist.
     * This prevents arbitrary class instantiation from user-supplied input.
     *
     * @param string $resourceType The morph map alias or fully qualified model class name.
     * @return string The fully qualified class name of the model.
     * @throws Exception If the resource type is not permitted.
     */
    private static function getModelForResourceType(string $resourceType): string
    {
        if (is_a($resourceType, Limitable::class, true)
            || $resourceType === \Spatie\Permission\Models\Role::class) {
            return $resourceType;
        }

        throw new Exception(
            "'{$resourceType}' is not a valid limitable resource type."
        );
    }

    public static function canAllocate(User $user, string $resourceType, int $allocation): bool {
        $c = self::getCurrentAllocation($user, $resourceType);

        $allUserUsageExceptMineExceptUsersWithLimits  = $c['allUserUsageExceptMineExceptUsersWithLimits'];
        $allUserLimitExceptMine  = $c['allUserLimitExceptMine'];
        $userLimit        = $c['userLimit'];
        $currentUsageOwn  = $c['currentUsageOwn'];
        $totalLimit  = $c['totalLimit'];

        if (($userLimit === null || ($userLimit > 0)) && ($allocation >= $currentUsageOwn)) {
            if (($totalLimit - $allUserUsageExceptMineExceptUsersWithLimits - $allUserLimitExceptMine - $allocation) >= 0) {
                return true;
            }
        }
        return false;
    }



    /**
     * Counts the current usage of a resource at a given scope.
     *
     * @param User $user
     * @param string $resourceType
     * @param string $scope ('user', 'organization', 'global')
     * @return int
     * @throws Exception
     */
    public static function getCurrentAllocation(User $user, string $resourceType): array
    {
        $currentUsageOwn = self::getCurrentUsage($user, $resourceType, 'user');
        $currentUsageOrg = self::getCurrentUsage($user, $resourceType, 'organization');
        $userLimit = self::getCurrentReservedResources($user, $resourceType, 'user');
        $allUserLimits = self::getCurrentReservedResources($user, $resourceType, 'organization');
        $allUserUsageExceptMineExceptUsersWithLimits = self::getCurrentUsageExcludingUser($user, $resourceType, 'organization');

        $allUserLimitExceptMine = $allUserLimits - $userLimit;
        $usedByOtherUsers = ($currentUsageOrg - $currentUsageOwn) + ($allUserLimits - $userLimit);
        $totalLimit = self::getOrganizationLimit($user, $resourceType);

        return [
            "currentUsageOwn" => $currentUsageOwn,
            "currentUsageOrg" => $currentUsageOrg,
            "userLimit" => $userLimit,
            "currentReservedResourcesOrg" => $allUserLimits,
            "usedByOtherUsers" => $usedByOtherUsers,
            "totalLimit" => $totalLimit,
            "allUserUsageExceptMineExceptUsersWithLimits" => $allUserUsageExceptMineExceptUsersWithLimits,
            "allUserLimitExceptMine" => $allUserLimitExceptMine
        ];
    }

    /**
     * Counts the current usage of a resource at a given scope.
     *
     * @param User $user
     * @param string $resourceType
     * @param string $scope ('user', 'organization', 'global')
     * @return int
     * @throws Exception
     */
    public static function getCurrentReservedResources(User $user, string $resourceType, string $scope): ?int
    {

        $sum = null;
        $orgUserIds = [];

        switch ($scope) {
            case 'user':
                $orgUserIds = [$user->id];
                break;
            case 'organization':
            case 'global':
                $orgUserIds = $user->organization->users()->pluck('id');
            default:
                break;
        }

        $orgUserLimit = UserResourceLimit::whereIn('user_id', $orgUserIds)
            ->where('resource_type', $resourceType)->get();

        if ($orgUserLimit->isNotEmpty()) {
            $sum = $orgUserLimit->sum('value');
        }

        return $sum;
    }

    /**
     * Counts the current usage of a resource at a given scope.
     *
     * @param User $user
     * @param string $resourceType
     * @param string $scope ('user', 'organization', 'global')
     * @return int
     * @throws Exception
     */
    public static function getCurrentUsage(User $user, string $resourceType, string $scope): ?int
    {
        /** @var Model $modelClass */
        $modelClass = self::getModelForResourceType($resourceType);

        $modelInstance = new $modelClass;
        $table = $modelInstance->getTable();

        // For user-centric scopes, check if the table even has a user_id column.
        if (!Schema::hasColumn($table, 'user_id') && !method_exists($modelClass, 'countByUser')) {
            // If the resource isn't user-specific, its usage can't be counted against a user/org limit.
            // This prevents errors for models that don't have a user relationship.
            return null;
        }

        switch ($scope) {
            case 'user':
                if (method_exists($modelClass, 'countByUser')) {
                    return $modelClass::countByUser($user->id);
                }

                return $modelClass::where('user_id', $user->id)->count();
            case 'organization':
            case 'global':
                if (!$user->organization) {
                    return null; // Or handle as an error if user should always have an org
                }
                // Get all user IDs within the organization
                $memberIds = $user->organization->users()->pluck('id');

                // Exclude users that have a specific limit for the resource type
                $excludedUserIds = UserResourceLimit::where('resource_type', $resourceType)
                    ->whereIn('user_id', $memberIds)
                    ->pluck('user_id')
                    ->toArray();

                $memberIds = $memberIds->diff($excludedUserIds);

                if (method_exists($modelClass, 'countByUsers')) {
                    return $modelClass::countByUsers($memberIds);
                }
                return $modelClass::whereIn('user_id', $memberIds)->count();

            default:
                return null;
        }
    }


    /**
     * Counts the current usage of a resource at a given scope.
     *
     * @param User $user
     * @param string $resourceType
     * @param string $scope ('user', 'organization', 'global')
     * @return int
     * @throws Exception
     */
    public static function getCurrentUsageExcludingUser(User $user, string $resourceType, string $scope): ?int
    {
        /** @var Model $modelClass */
        $modelClass = self::getModelForResourceType($resourceType);

        $modelInstance = new $modelClass;
        $table = $modelInstance->getTable();

        // For user-centric scopes, check if the table even has a user_id column.
        if (!Schema::hasColumn($table, 'user_id') && !method_exists($modelClass, 'countByUser')) {
            // If the resource isn't user-specific, its usage can't be counted against a user/org limit.
            // This prevents errors for models that don't have a user relationship.
            return null;
        }

        switch ($scope) {
            case 'user':
                if (method_exists($modelClass, 'countByUser')) {
                    return $modelClass::countByUser($user->id);
                }

                return $modelClass::where('user_id', $user->id)->count();
            case 'organization':
            case 'global':
                if (!$user->organization) {
                    return null; // Or handle as an error if user should always have an org
                }
                // Get all user IDs within the organization
                $memberIds = $user->organization->users()->pluck('id');

                // Exclude users that have a specific limit for the resource type
                $excludedUserIds = UserResourceLimit::where('resource_type', $resourceType)
                    ->whereIn('user_id', $memberIds)
                    ->pluck('user_id')
                    ->toArray();

                $memberIds = $memberIds->diff($excludedUserIds);

                $memberIds = $memberIds->diff($user->id);

                if (method_exists($modelClass, 'countByUsers')) {
                    return $modelClass::countByUsers($memberIds);
                }
                return $modelClass::whereIn('user_id', $memberIds)->count();

            default:
                return null;
        }
    }

    /**
     * Get the effective resource limit and its scope for a given user and resource type.
     *
     * @param User $user
     * @param string $resourceType
     * @return array|null An array containing 'value' and 'scope', or null if no limit is found.
     */
    public static function getEffectiveLimit(User $user, string $resourceType): ?array
    {
        // 1. User-specific limit
        $userLimit = UserResourceLimit::where('user_id', $user->id)
            ->where('resource_type', $resourceType)->first();
        if ($userLimit) {
            return ['value' => $userLimit->value, 'scope' => 'user'];
        }

        // Get all the organization users that have a specific limit
        // This is to ensure we don't count the user limit again if they are part of an organization
        // and the organization has a specific limit for the resource type.
        $sum = self::getCurrentReservedResources($user, $resourceType, 'organization');

        // 2. Organization-specific limit
        if ($user->organization_id) {
            $orgLimit = OrganizationResourceLimit::where('organization_id', $user->organization_id)
                ->where('resource_type', $resourceType)->first();
            if ($orgLimit) {
                return ['value' => $orgLimit->value - $sum, 'scope' => 'organization'];
            }
        }

        // 3. Global resource limit
        $globalLimit = ResourceLimit::where('resource_type', $resourceType)->first();
        if ($globalLimit) {
            return ['value' => $globalLimit->value - $sum, 'scope' => 'global'];
        }

        return null;
    }

    /**
     * Get the effective resource limit for a user based on organization, contracts, and global limits.
     * This skips user-specific limits.
     *
     * @param User $user
     * @param string $resourceType
     * @return array|null An array containing 'value' and 'scope', or null if no limit is found.
     */
    public static function getOrganizationLimit(User $user, string $resourceType): ?int
    {

        // 1. Organization-specific limit
        if ($user->organization_id) {
            $orgLimit = OrganizationResourceLimit::where('organization_id', $user->organization_id)
                ->where('resource_type', $resourceType)
                ->first();
            if ($orgLimit) {
                return $orgLimit->value;
            }
        }

        // 2. Global resource limit
        $globalLimit = ResourceLimit::where('resource_type', $resourceType)->first();
        if ($globalLimit) {
            return $globalLimit->value;
        }

        return null;
    }

    /**
     * Get the effective resource limit value for a given user and resource type.
     *
     * Note: For more comprehensive checks, use the `canCreate` method.
     * This method is maintained for backward compatibility.
     *
     * @param User $user
     * @param string $resourceType
     * @return int The limit value. Returns 0 if no limit is defined.
     */
    public static function getLimitForUser(User $user, string $resourceType): int
    {
        $limitDetails = self::getEffectiveLimit($user, $resourceType);
        return $limitDetails['value'] ?? 0;
    }


    public static function canCreateOrFail(User $user, string $resourceType): void
    {
        asset($canResourceLimit = ResourceLimitsHelper::canCreate($user, $resourceType));

        $canResourceLimitNumber = ResourceLimitsHelper::getEffectiveLimit($user, $resourceType);


        if (!$canResourceLimit) {
            $pretty = ucwords(str_replace('_', ' ', $resourceType));

            $msg = "You have reached the limit of {$pretty} you can create";
             if ($canResourceLimitNumber) {
            $msg .= " ({$canResourceLimitNumber['value']})";
            }
            abort(403, $msg);
        }
    }

    /**
     * Counts the current usage of a resource at a given scope.
     *
     * @param User $user
     * @param string $resourceType
     * @param string $scope ('user', 'organization', 'global')
     * @return int
     * @throws Exception
     */
    public static function getAggregatedUsage(User $user, string $resourceType)
    {
        $modelClass = self::getModelForResourceType($resourceType);

        $modelInstance = new $modelClass;
        $table = $modelInstance->getTable();

        if (!Schema::hasColumn($table, 'user_id') && !method_exists($modelClass, 'aggregatedCountByUser')) {
            return null;
        }


        if (!$user->organization) {
            return null;
        }

        $memberIds = $user->organization->users()->pluck('id');

        if (method_exists($modelClass, 'aggregatedCountByUsers')) {
            return $modelClass::aggregatedCountByUsers($memberIds);
        }
        return $modelClass::whereIn('user_id', $memberIds)
            ->groupBy('user_id')
            ->select('user_id', DB::raw('count(*) as count'))
            ->orderBy('count', 'desc')
            ->pluck('count', 'user_id');

    }
}


