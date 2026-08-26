<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    protected $connection = 'pgsql_realtime';

    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('entity_commands', function (Blueprint $table) {
            $table->id();
            $table->string('urn');
            $table->string('name');
            $table->string('status')->nullable();
            $table->string('info')->nullable();
            $table->boolean('available')->nullable();
            $table->boolean('pending')->nullable();
            $table->string('pending_value')->nullable();
            $table->timestamp('status_timestamp')->nullable();
            $table->timestamp('info_timestamp')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        
        Schema::dropIfExists('entity_commands');
    }
};
