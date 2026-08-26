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
        Schema::create('action_http_push', function (Blueprint $table) {
            $table->id();
            $table->jsonb('url_template');
            $table->string('method');
            $table->string('authorization')->nullable();
            // $table->jsonb('payload_config')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('action_http_push');
    }
};
