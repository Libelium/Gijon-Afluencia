<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Entity;
use App\Repositories\OrganizationRepository;
use App\Services\PublicIncidentsWorkspaceService;

class PublicIncidentsWorkspaceSeeder extends Seeder
{
    public function run()
    {
        // Public workspace (members = all citizens) — receives public incidents.
        if (PublicIncidentsWorkspaceService::enabled()) {
            $workspace = PublicIncidentsWorkspaceService::ensureWorkspace();
            if ($workspace) {
                $count = $this->backfillPublicReadonly();
                $this->command?->info("Public-incidents workspace ready: '{$workspace->name}' "
                    . "(all org users added, {$count} module entities backfilled).");
            } else {
                $this->command?->info('Public-incidents workspace not created (organization or admin missing).');
            }
        } else {
            $this->command?->info('Public-incidents workspace disabled (env not set); skipping.');
        }

        // Reviewers workspace (members = users with incidents.review) — receives EVERY incident.
        if (PublicIncidentsWorkspaceService::reviewersEnabled()) {
            $workspace = PublicIncidentsWorkspaceService::ensureReviewersWorkspace();
            if ($workspace) {
                $count = $this->backfillReviewers();
                $this->command?->info("Reviewers workspace ready: '{$workspace->name}' ({$count} incidents backfilled).");
            } else {
                $this->command?->info('Reviewers workspace not created (organization or admin missing).');
            }
        } else {
            $this->command?->info('Reviewers workspace disabled (env not set); skipping.');
        }
    }

    /**
     * Same treatment EntityObserver gives new notices/surveys/services/operator teams, applied to
     * the ones that already existed: READ via the PUBLIC workspace + READ+UPDATE for the
     * incidents-admins. They used to be reachable only through the blanket tenant/scope grant that
     * addUser() no longer hands out. Idempotent.
     *
     * Public incidents are NOT backfilled: `privacy` lives in Orion, not in the mirror, so which
     * ones are public cannot be derived locally — publish() shares them as they are published.
     */
    private function backfillPublicReadonly(): int
    {
        $orgId = PublicIncidentsWorkspaceService::organizationId();
        if ($orgId === null) {
            return 0;
        }

        $scopeIds = collect(OrganizationRepository::getOrganizationScopes($orgId))->pluck('id')->all();
        if (empty($scopeIds)) {
            return 0;
        }

        $count = 0;
        Entity::whereIn('datamodel', PublicIncidentsWorkspaceService::PUBLIC_READONLY_DATAMODELS)
            ->whereIn('fiware_scope_id', $scopeIds)
            ->chunkById(200, function ($entities) use (&$count) {
                foreach ($entities as $entity) {
                    PublicIncidentsWorkspaceService::shareEntityToPublic($entity);
                    PublicIncidentsWorkspaceService::grantAdminUpdate($entity);
                    $count++;
                }
            });

        return $count;
    }

    /**
     * Share every existing incident of the organization's scopes with the reviewers workspace.
     * Idempotent (shareIncidentToReviewers skips entities already present).
     */
    private function backfillReviewers(): int
    {
        $orgId = PublicIncidentsWorkspaceService::organizationId();
        if ($orgId === null) {
            return 0;
        }

        $scopeIds = collect(OrganizationRepository::getOrganizationScopes($orgId))->pluck('id')->all();
        if (empty($scopeIds)) {
            return 0;
        }

        $count = 0;
        Entity::where('datamodel', 'Incident')
            ->whereIn('fiware_scope_id', $scopeIds)
            ->chunkById(200, function ($incidents) use (&$count) {
                foreach ($incidents as $incident) {
                    PublicIncidentsWorkspaceService::shareIncidentToReviewers($incident);
                    $count++;
                }
            });

        return $count;
    }
}
