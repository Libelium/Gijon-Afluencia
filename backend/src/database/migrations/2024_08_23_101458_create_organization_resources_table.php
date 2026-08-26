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
        Schema::drop('device_organization');
        Schema::create('organization_has_resource', function (Blueprint $table) {
            $table->id();
            $table->foreignId('organization_id')->references('id')->on('organizations')->onDelete('cascade');
            $table->morphs('resource');
            $table->timestamps();

            $table->index(['organization_id']);
            $table->index(['resource_type']);
        });

        // update organization_preference for cascade delete
        Schema::table('organization_preference', function (Blueprint $table) {
            $table->dropForeign(['organization_id']);
            $table->foreign('organization_id')->references('id')->on('organizations')->onDelete('cascade');
        });

        // update user organization for cascade delete
        Schema::table('users', function (Blueprint $table) {
            $table->dropForeign(['organization_id']);
            $table->foreign('organization_id')->references('id')->on('organizations')->onDelete('cascade');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('organization_has_resource');

        Schema::create('device_organization', function (Blueprint $table) {
            $table->id();
            $table->foreignId('organization_id')->references('id')->on('organizations')->onDelete('cascade');
            $table->foreignId('device_id')->references('id')->on('devices')->onDelete('cascade');
            $table->timestamps();
        });
    }
};
