<?php

namespace Database\Seeders;

use App;
use Illuminate\Database\Seeder;
use App\Authorization\AppPermission;
use App\Models\Authorization\ResourcePermission;
use App\Authorization\AppResourcePermission;
use Spatie\Permission\Models\Permission;
use Spatie\Permission\Models\Role;
use App\Models\User;
use App\Authorization\ResourcePermissionCache;

class PermissionsSyncSeeder extends Seeder
{
    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $this->syncSpatiePermissions();
        $this->syncResourcePermissions();
    }

    private function syncSpatiePermissions()
    {
        $permissions = AppPermission::cases();
        foreach ($permissions as $permission) {
            Permission::firstOrCreate(
                [
                    'name' => $permission->value,
                ]
            );
        }

        // refresh permission cache
        App::make(\Spatie\Permission\PermissionRegistrar::class)->forgetCachedPermissions();

        // super admin role
        $super_admin_role = Role::firstOrCreate(
            [
                'name' => 'super_admin',
                'organization_id' => null,
            ]
        );


        $super_admin_permissions = AppPermission::superAdminPermissions();

        $super_admin_role->syncPermissions($super_admin_permissions);

        // qc admin role
        $qc_role = Role::firstOrCreate(
            [
                'name' => 'qc_admin',
                'organization_id' => null,
            ]
        );

        $qc_permissions = AppPermission::qcAdminPermissions();

        $qc_role->syncPermissions($qc_permissions);

        // Access levels of the organization users (OrganizationAccessService).
        foreach ([
            'org_viewer' => AppPermission::orgViewerPermissions(),
            'org_editor' => AppPermission::orgEditorPermissions(),
        ] as $name => $permissions) {
            Role::firstOrCreate(['name' => $name, 'organization_id' => null])
                ->syncPermissions($permissions);
        }
    }

    private function syncResourcePermissions()
    {
        $resource_permissions = AppResourcePermission::cases();

        foreach ($resource_permissions as $resource_permission) {
            ResourcePermission::firstOrCreate(
                [
                    'name' => $resource_permission->value,
                ]
            );
        }

        // get the app and refresh the cache
        $cache = App(ResourcePermissionCache::class);
        $cache->reset();
    }
}
