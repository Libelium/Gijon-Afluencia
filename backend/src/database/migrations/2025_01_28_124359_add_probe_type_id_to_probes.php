<?php

use App\Models\Probe;
use App\Models\ProbeType;
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
        Schema::table('probes', function (Blueprint $table) {
            $table->foreignId('probe_type_id')->references('id')->on('probe_types');
            $table->dropColumn('model');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('probes', function (Blueprint $table) {
            $table->string('model')->default('generic_one_probe');
            $table->dropForeign(['probe_type_id']);
            $table->dropColumn('probe_type_id');
        });
    }
};
