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
        Schema::create('resource_limits', function (Blueprint $table) {
            $table->id();
            $table->string('resource_type')->unique();
            $table->unsignedInteger('value')->default(0);
            $table->timestamps();
        });

        Schema::create('organization_resource_limits', function (Blueprint $table) {
            $table->id();
            $table->foreignId('organization_id')->references('id')->on('organizations')->onDelete('cascade');
            $table->string('resource_type');
            $table->unsignedInteger('value')->default(0);
            $table->timestamps();
        });

        Schema::create('user_resource_limits', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->references('id')->on('users')->onDelete('cascade');
            $table->string('resource_type');
            $table->unsignedInteger('value')->default(0);
            $table->timestamps();
        });

    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('user_resource_limits');
        Schema::dropIfExists('organization_resource_limits');
        Schema::dropIfExists('resource_limits');
    }
};
