<?php

namespace App\Observers;

use App\Models\Entity;
use App\Services\PublicIncidentsWorkspaceService;
use Illuminate\Support\Facades\Auth;

class EntityObserver
{
    /**
     * Incidents-module side effects on creation (other datamodels are untouched):
     *  - Incident: grant the creator READ+UPDATE (only they can edit it) and share with the
     *    reviewers workspace as READ+UPDATE (reviewers must act on it). Public sharing
     *    (privacy=public) is done separately via publish (privacy lives in Orion, not here).
     *  - Notices, surveys, services and operator teams (PUBLIC_READONLY_DATAMODELS): shared READ
     *    with the PUBLIC/guest workspace so citizens can see them, plus READ+UPDATE for the
     *    incidents-admins on the ones they manage.
     */
    public function created(Entity $entity): void
    {
        if ($entity->datamodel === 'Incident') {
            if (Auth::check()) {
                PublicIncidentsWorkspaceService::grantCreator($entity, Auth::user());
            }
            PublicIncidentsWorkspaceService::shareIncidentToReviewers($entity);

            return;
        }

        if (in_array($entity->datamodel, PublicIncidentsWorkspaceService::PUBLIC_READONLY_DATAMODELS, true)) {
            PublicIncidentsWorkspaceService::shareEntityToPublic($entity);
            PublicIncidentsWorkspaceService::grantAdminUpdate($entity);
        }
    }
}
