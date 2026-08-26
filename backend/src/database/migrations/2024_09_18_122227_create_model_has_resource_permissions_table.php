<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('model_has_resource_permissions', function (Blueprint $table) {
            $table->id();
            $table->morphs('model');
            $table->foreignId('resource_permission_id')->references('id')->on('resource_permissions')->onDelete('cascade');
            $table->morphs('resource');
            $table->timestamps();

            // index
            $table->index(['model_id', 'model_type']);
            $table->index(['model_id', 'model_type', 'resource_type']);
            $table->index(['resource_type']);
            $table->index(['resource_permission_id', 'resource_type', 'resource_id']);
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('model_has_resource_permissions');
    }
};
