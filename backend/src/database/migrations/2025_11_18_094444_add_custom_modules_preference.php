<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use App\Models\Preference;


return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        // Crear si no existe
        Preference::firstOrCreate(
            ['name' => 'customModules'],
            ['default_value' => null]
        );
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Preference::where('name', 'customModules')->delete();
    }
};      