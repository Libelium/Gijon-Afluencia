<?php

namespace Database\Seeders;

use App\Models\Organization;
use App\Models\User;
use Illuminate\Database\Seeder;
use App\Http\V1\Controllers\OrganizationController;
use App\Traits\KeycloakHelper;
use App\Authorization\AppResourcePermission;
use Spatie\Permission\Models\Role;
use App\Authorization\AppPermission;
use App\Models\FiwareTenant;
use App\Models\Workspace;
use App\Repositories\WorkspaceRepository;

class SaasOrganizationsSeeder extends Seeder
{
    use KeycloakHelper;

    /**
     * Run the database seeds.
     *
     * @return void
     */
    public function run()
    {
        $this->createRootOrganization();
    }

    /**
     * Create the root organization, its admin user and the QC admin user.
     * These users don't need to be created in Keycloak because they are always
     * created by the realm import script of Keycloak.
     */
    private function createRootOrganization()
    {
        // Create the admin user for the root organization
        $nexusUser = User::create([
            'name' => 'Nexus',
            'email' => 'nexus@pid.gijon.example',
            'organization_id' => null
        ]);

        // Create the root organization and assign the admin user
        $rootOrg = Organization::create([
            'name' => 'PID Gijon',
            'admin' => $nexusUser->id
        ]);

        $rootOrg = Organization::where('name', 'PID Gijon')->first();
        $rootOrg->admin = $nexusUser->id;
        $rootOrg->save();

        // Assign the organization and the admin role to the user
        $nexusUser->organization_id = $rootOrg->id;
        $nexusUser->save();

        $defaultPermissions = AppResourcePermission::defaultPermissions();
        $nexusUser->giveResourcePermissionsTo($defaultPermissions, $rootOrg);
        $nexusUser->assignRole('super_admin');

        // Repeat for QC Admin
        $qcUser = User::create([
            'name' => 'QC admin',
            'email' => 'admin_qc@pid.gijon.example',
            'organization_id' => $rootOrg->id
        ]);

        $qcUser->assignRole('qc_admin');

        $nexusUser->giveResourcePermissionsTo($defaultPermissions, $qcUser);

        // create qc workspace
        $qcWorkspace = Workspace::create([
            'name' => 'QC',
            'description' => 'Quality Control',
            'user_id' => $qcUser->id,
            'collaborative' => false
        ]);

        $qcUser->giveResourcePermissionsTo($defaultPermissions, $qcWorkspace);

        $orgController = app(OrganizationController::class);
        $orgController->setupOrganizationFiwareScopes($rootOrg);
    }
}
