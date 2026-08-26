<?php

namespace App\Providers;

use Spatie\Permission\Models\Role;
use Spatie\Permission\Models\Permission;
use App\Guards\ExtendedKeycloakGuard;
use Illuminate\Support\Facades\Auth;

// use Illuminate\Support\Facades\Gate;
use Illuminate\Foundation\Support\Providers\AuthServiceProvider as ServiceProvider;

class AuthServiceProvider extends ServiceProvider
{
    /**
     * The model to policy mappings for the application.
     *
     * @var array<class-string, class-string>
     */
    protected $policies = [
        Role::class => 'App\Policies\RolePolicy',
        Permission::class => 'App\Policies\PermissionPolicy',
    ];

    /**
     * Register any authentication / authorization services.
     */
    public function boot(): void
    {
        $this->registerPolicies();

        Auth::extend('extended-keycloak', function ($app, $name, array $config) {
            return new ExtendedKeycloakGuard(
                Auth::createUserProvider($config['provider']),
                $app['request']
            );
        });
    }
}
