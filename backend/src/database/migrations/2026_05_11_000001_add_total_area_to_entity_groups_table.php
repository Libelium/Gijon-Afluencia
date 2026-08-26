<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('entity_groups', function (Blueprint $table) {
            $table->unsignedInteger('total_area')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('entity_groups', function (Blueprint $table) {
            $table->dropColumn('total_area');
        });
    }
};
