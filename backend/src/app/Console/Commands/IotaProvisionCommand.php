<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Helpers\ServiceProvisioningHelper;
use Exception;
use App\Models\Organization;
use App\Repositories\PreferenceRepository;
use App\Models\FiwareScope;



class IotaProvisionCommand extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'app:provision-iota
                            {--all : Execute for all organizations}
                            {--name= : Name of the organization or tenant}
                            {--scopeType= : mainScope|platformDataScope}';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Provisions IOTA services, either for a specific tenant/scope or for all organizations';

    /**
     * Execute the console command.
     *
     * @return int The exit code of the command. 0 for success, 1 for failure.
     */
    public function handle(): int
    {
        if ($this->hasInvalidArguments()) {
            return 1;
        }

        try {
            $name       = $this->option('name');
            $scopeType  = $this->option('scopeType');
            $scopeTypes = $scopeType ? [$scopeType] : ['mainScope', 'platformDataScope'];

            $organizations = $name
                ? collect([Organization::where('name', $name)->firstOrFail()])
                : Organization::lazy();

            foreach ($organizations as $org) {
                $this->info("Org #{$org->id}: {$org->name}");
                foreach ($scopeTypes as $type) {
                    try {
                        $scope = $this->findScopeForOrganization($org, $type);
                        if (!$scope) {
                            $this->error("  Could not find scope '{$type}'.");
                            continue;
                        }
                        $this->provisionScopeAndDisplay($org, $scope, $type);
                    } catch (Exception $e) {
                        $this->error("  Error on '{$type}': " . $e->getMessage());
                    }
                }
            }

            return 0;
        } catch (Exception $e) {
            $this->error("Error! " . $e->getMessage());
            return 1;
        }
    }

    /**
     * Provisions the given scope and displays the result.
     *
     * @param Organization $organization
     * @param FiwareScope $scope
     * @param string $scopeType
     * @return void
     */
    private function provisionScopeAndDisplay(Organization $organization, FiwareScope $scope, string $scopeType): void
    {
        $this->line("  <fg=cyan>[{$scopeType}]</> {$scope->tenant->name} / {$scope->name}");

        if ($scopeType === 'mainScope') {
            $result = resolve(ServiceProvisioningHelper::class)->getDevicesAndProbesAndProvision($scope->tenant, $scope);
            $this->displayMainScopeResult($result);
        } elseif ($scopeType === 'platformDataScope') {
            $entities = resolve(ServiceProvisioningHelper::class)->getEntitiesToProvisionAndProvision($scope->tenant, $scope);
            $this->displayDataScopeResult($entities);
        }
    }

    /**
     * Finds the FiwareScope for a given organization and scope type string.
     *
     * @param Organization $organization The organization model.
     * @param string $scopeType The scope type ('mainScope' or 'platformDataScope').
     * @return FiwareScope|null The found scope with its tenant, or null if not found.
     */
    private function findScopeForOrganization(Organization $organization, string $scopeType): ?FiwareScope
    {
        $scopeId = PreferenceRepository::getOrganizationPreference($organization, $scopeType);
        if (!$scopeId) {
            return null;
        }

        $scope = FiwareScope::with('tenant')->find($scopeId);

        if (!$scope || !$scope->tenant) {
            return null;
        }

        return $scope;
    }

    /**
     * Validates the command's arguments and options to ensure they are consistent.
     *
     * @return bool True if arguments are invalid, false otherwise.
     */
    private function hasInvalidArguments(): bool
    {
        $all       = $this->option('all');
        $name      = $this->option('name');
        $scopeType = $this->option('scopeType');

        if (!$all && !$name && !$scopeType) {
            $this->error('You must provide at least one of: --all, --name, or --scopeType.');
            return true;
        }

        if ($all && $name) {
            $this->error('Cannot use --all together with --name.');
            return true;
        }

        if ($scopeType && !in_array($scopeType, ['mainScope', 'platformDataScope'], true)) {
            $this->error('The --scopeType option must be either "mainScope" or "platformDataScope".');
            return true;
        }

        return false;
    }

    /**
     * Displays the provisioning results for a 'mainScope' operation.
     *
     * @param array $result The result containing devices and probes to provision.
     * @return void
     */
    private function displayMainScopeResult(array $result): void
    {
        $devices = $result['devicesToProvision'];
        $probes  = $result['probesToProvision'];

        if ($devices->isEmpty() && $probes->isEmpty()) {
            $this->line('    <fg=green>✓</> Nothing to provision.');
            return;
        }

        if ($devices->isNotEmpty()) {
            $this->line("    Devices provisioned ({$devices->count()}):");
            $this->table(
                ['Entity Type', 'Device Type Code'],
                $devices->map(fn($s) => [$s['entity_type'], $s['internal_attributes']['device_type_code']])->toArray()
            );
        }

        if ($probes->isNotEmpty()) {
            $this->line("    Probes provisioned ({$probes->count()}):");
            $this->table(
                ['Entity Type', 'Device Type Code'],
                $probes->map(fn($s) => [$s['entity_type'], $s['internal_attributes']['device_type_code']])->toArray()
            );
        }
    }

    /**
     * Displays the provisioning results for an 'platformDataScope' operation.
     *
     * @param array $entities A list of entity type strings to be provisioned.
     * @return void
     */
    private function displayDataScopeResult(array $entities): void
    {
        if (empty($entities)) {
            $this->line('    <fg=green>✓</> Nothing to provision.');
            return;
        }

        $this->line("    Entities provisioned (" . count($entities) . "):");
        $this->table(
            ['Entity Type'],
            collect($entities)->map(fn(string $e) => [$e])->toArray()
        );
    }
}
