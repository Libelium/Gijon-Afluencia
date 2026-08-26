<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration {
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('report_generations', function (Blueprint $table) {
            $table->id();
            $table->string('file', 1024)->nullable(); //S3 paths are 1024 characters long at most
            $table->foreignId('report_id')->references('id')->on('reports')->onDelete('cascade');
            $table->timestamps();
        });

        // drop last generated from reports
        Schema::table('reports', function (Blueprint $table) {
            $table->dropColumn('last_generated');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('report_generations');

        Schema::table('reports', function (Blueprint $table) {
            $table->timestamp('last_generated')->nullable();
        });
    }
};
