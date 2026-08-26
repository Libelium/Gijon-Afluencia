<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('resource_permissions', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->timestamps();
        });

        Schema::create('user_has_resource_permissions', function (Blueprint $table) {
            // this only needs an id because we are going to use it 
            // as a model and not as a pivot table, and laravel packages handle this
            // better with an id (and we have ids in everything else so...)
            $table->id();
            $table->foreignId('user_id')->references('id')->on('users')->onDelete('cascade');
            $table->foreignId('resource_permission_id')->references('id')->on('resource_permissions')->onDelete('cascade');
            $table->morphs('resource');
            $table->timestamps();

            // index
            $table->index(['user_id']);
            $table->index(['resource_type']);
            $table->index(['resource_permission_id', 'resource_type', 'resource_id']);
        });

    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('user_has_resource_permissions');
        Schema::dropIfExists('resource_permissions');
    }
};
