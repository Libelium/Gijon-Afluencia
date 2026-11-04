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
        // A PEM CA certificate does not fit in the 255 characters of a string column.
        Schema::table('mqtt_connector', function (Blueprint $table) {
            $table->text('sslCert')->nullable()->change();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('mqtt_connector', function (Blueprint $table) {
            $table->string('sslCert')->nullable()->change();
        });
    }
};
