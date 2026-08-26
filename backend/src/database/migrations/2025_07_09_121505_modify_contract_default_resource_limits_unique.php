<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('contract_default_resource_limits', function (Blueprint $table) {
            $table->dropUnique(['contract_name']);

            $table->unique(['contract_name', 'resource_type']);
        });
    }

    public function down(): void
    {
        Schema::table('contract_default_resource_limits', function (Blueprint $table) {
            $table->dropUnique(['contract_name', 'resource_type']);

            $table->unique(['contract_name']);
        });
    }
};
