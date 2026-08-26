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
        Schema::create('fiware_out_connector', function (Blueprint $table) {
            $table->id();
            $table->string('url');
            $table->string('iota_type');
            $table->jsonb('i');
            $table->jsonb('k');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('fiware_out_connector');
    }
};
