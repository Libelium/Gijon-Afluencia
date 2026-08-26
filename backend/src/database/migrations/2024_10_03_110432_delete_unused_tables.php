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
        Schema::dropIfExists('companies');
        Schema::dropIfExists('personal_access_tokens');
        Schema::dropIfExists('user_has_resource_permissions');
        Schema::dropIfExists('subscription_plan_modules');
        Schema::dropIfExists('subscription_plans');
        Schema::dropIfExists('user_modules');
        Schema::dropIfExists('modules');
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        // This should never be undone
    }
};
