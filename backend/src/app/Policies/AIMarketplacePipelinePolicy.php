<?php

namespace App\Policies;

use App\Repositories\PermissionRepository;

use App\Models\AIMarketplacePipeline;
use App\Models\User;
use Illuminate\Auth\Access\HandlesAuthorization;
use Illuminate\Auth\Access\Response;
use App\Helpers\ResourceLimitsHelper;



class AIMarketplacePipelinePolicy
{
    use HandlesAuthorization;

    /**
     * Checks if the user can read the report.
     *
     * @param  \App\Models\User $user
     * @param  \App\Models\Reports\Report $report
     * @return void|bool
     */

    public function read(User $user, AIMarketplacePipeline $pipeline)
    {
        return $user->id === $pipeline->user_id;
    }

    /**
     * Checks if the user can update the report.
     * @param User $user
     * @param Report $report
     * @return bool|mixed
     */
    public function update(User $user, AIMarketplacePipeline $pipeline)
    {
        return $user->id === $pipeline->user_id;
    }

    /**
     * Checks if the user can delete the report.
     * @param User $user
     * @param Report $report
     * @return bool|mixed
     */
    public function delete(User $user, AIMarketplacePipeline $pipeline)
    {
        return $user->id === $pipeline->user_id;
    }

    /**
     * Checks if the user can create a new AI Marketplace Pipeline,

     */
    public function create(User $user): Response
    {
        ResourceLimitsHelper::canCreateOrFail($user, AIMarketplacePipeline::class);

        return Response::allow();
    }
}
