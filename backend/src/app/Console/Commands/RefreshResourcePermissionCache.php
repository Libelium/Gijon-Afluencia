<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use App\Authorization\ResourcePermissionCache;

class RefreshResourcePermissionCache extends Command
{
    /**
     * The name and signature of the console command.
     *
     * @var string
     */
    protected $signature = 'app:resource-permission-cache-reset';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Refresh the resource permission cache';

    /**
     * Execute the console command.
     */
    public function handle()
    {
        $cache = app(ResourcePermissionCache::class);
        $cache->reset();
    }
}
