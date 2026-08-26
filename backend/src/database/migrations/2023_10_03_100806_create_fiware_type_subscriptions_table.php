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
        Schema::create('fiware_type_subscriptions', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('fiware_type')->unique();
            $table->boolean('libelium_type')->default(false);
            $table->string('image')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('fiware_type_subscriptions');
    }
};
