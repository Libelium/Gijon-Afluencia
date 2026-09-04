<?php

namespace App\Providers;

use Illuminate\Database\Eloquent\Relations\Relation;
use App\Models\Actions\ActionEmail;
use App\Models\Actions\ActionEntityCommand;
use Illuminate\Support\ServiceProvider;

/**
 *
 * Class MorphServiceProvider
 *
 * This class is used to map the morph classes to the actual classes
 * @package App\Providers
 *
 */
class MorphServiceProvider extends ServiceProvider
{
    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        Relation::morphMap([
            'action_email' => ActionEmail::class,
            'action_entity_command' => ActionEntityCommand::class,
        ]);
    }
}
