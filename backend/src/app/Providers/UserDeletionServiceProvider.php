<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;

use App\Services\UserDeletion\TransferableRegistry;
use App\Services\UserDeletion\Handlers\ApiKeyHandler;
use App\Services\UserDeletion\Handlers\StandardUserIdHandler;
use App\Services\UserDeletion\Handlers\AlarmHandler;
use App\Services\UserDeletion\Handlers\StandardDeletableHandler;
use App\Services\UserDeletion\Handlers\OrganizationHandler;
use App\Services\UserDeletion\Handlers\ActionHandler;
use App\Services\UserDeletion\Handlers\MqttAclHandler;
use App\Services\UserDeletion\Handlers\SpatiePermissionsHandler;
use App\Services\UserDeletion\Handlers\ResourcePermissionsHandler;

// Standard models
use App\Models\CrowdVisitor;
use App\Models\Dashboard;
use App\Models\EntityGroup;
use App\Models\EtlExecution;
use App\Models\InConnector;
use App\Models\OutConnectors\OutConnector;
use App\Models\Preferencable;
use App\Models\UserResourceLimit;

class UserDeletionServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(TransferableRegistry::class, function () {
            return (new TransferableRegistry())

                // Transferable: standard user_id
                ->registerTransferable(AlarmHandler::class)
                ->registerTransferable(ApiKeyHandler::class)
                ->registerTransferable(StandardUserIdHandler::class, Dashboard::class)
                ->registerTransferable(StandardUserIdHandler::class, EntityGroup::class)
                ->registerTransferable(StandardUserIdHandler::class, InConnector::class)
                ->registerTransferable(StandardUserIdHandler::class, OutConnector::class)
                ->registerTransferable(StandardUserIdHandler::class, UserResourceLimit::class)
                ->registerTransferable(StandardUserIdHandler::class, CrowdVisitor::class)
                ->registerTransferable(StandardUserIdHandler::class, EtlExecution::class)

                // Transferable: special logic — order matters (org cascade must run last)
                ->registerTransferable(ActionHandler::class)
                ->registerTransferable(MqttAclHandler::class)
                ->registerTransferable(OrganizationHandler::class)

                // DeletableWithUser: standard user_id
                ->registerDeletable(StandardDeletableHandler::class, Preferencable::class)
                ->registerDeletable(SpatiePermissionsHandler::class)
                ->registerDeletable(ResourcePermissionsHandler::class);
        });
    }
}
