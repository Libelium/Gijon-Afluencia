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
        Schema::table('out_connectors', function (Blueprint $table) {
            $table->boolean('use_readable_names')->default(false)->after('connectable_id');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('out_connectors', function (Blueprint $table) {
            $table->dropColumn('use_readable_names');
        });
    }
};
