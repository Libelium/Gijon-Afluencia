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
        Schema::create('http_connector', function (Blueprint $table) {
            $table->id();
            $table->string('method');
            $table->string('url');
            $table->integer('retries')->nullable();
            $table->integer('timeout')->nullable();
            $table->boolean('bulk')->default(false);
            $table->jsonb('payload_config')->nullable();
            $table->timestamps();
            $table->jsonb('headers')->nullable();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('http_connector');
    }
};
