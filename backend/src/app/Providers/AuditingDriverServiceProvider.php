<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use OwenIt\Auditing\Auditor;
use App\Auditing\Drivers\StdoutAuditor;

class AuditingDriverServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        // empty
    }

    public function boot(): void
    {
        $this->callAfterResolving(Auditor::class, function ($auditor, $app) {
            static $registered = false;

            if (! $registered) {
                $auditor->extend('stdout', function ($app) {
                    return new StdoutAuditor();
                });

                $registered = true;
            }

        });
    }
}
