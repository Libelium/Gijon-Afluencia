<?php

namespace App\Console\Commands;

use App\Helpers\UserLocaleSyncHelper;
use App\Models\User;
use Illuminate\Console\Command;

class SyncKeycloakUserLocales extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'keycloak:sync-user-locales';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Backfill each Keycloak user locale attribute from their effective '
        . 'platform language preference (user -> organization -> default).';

    /**
     * Execute the console command.
     */
    public function handle(UserLocaleSyncHelper $helper): int
    {
        $query = User::whereNotNull('keycloak_client_id');
        $total = $query->count();

        if ($total === 0) {
            $this->info('No users with a Keycloak id to sync.');
            return self::SUCCESS;
        }

        $this->info("Syncing locale for {$total} user(s)...");
        $bar = $this->output->createProgressBar($total);
        $bar->start();

        $ok = 0;
        $failed = 0;

        $query->orderBy('id')->chunkById(200, function ($users) use ($helper, &$ok, &$failed, $bar) {
            foreach ($users as $user) {
                if ($helper->syncUserLocale($user)) {
                    $ok++;
                } else {
                    $failed++;
                }
                $bar->advance();
            }
        });

        $bar->finish();
        $this->newLine(2);
        $this->info("Done. Synced: {$ok}, skipped/failed: {$failed}.");

        return self::SUCCESS;
    }
}
