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
        Schema::create('entity_relationships', function (Blueprint $table) {
            $table->id();
            $table->string('urn');
            $table->string('name');
            $table->string('value')->nullable();
            $table->timestamp('timestamp');
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        
        Schema::dropIfExists('entity_relationships');
    }
};
