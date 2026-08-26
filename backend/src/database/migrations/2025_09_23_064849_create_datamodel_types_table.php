<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('datamodel_types', function (Blueprint $table) {
            $table->id();
            $table->string('name')->unique();
            $table->timestamps();
        });

        /**
        * NOTA IMPORTANTE:
        * Insertamos el valor inicial directamente en la migración para que sea reversible con rollback.
        *
        * Política para añadir nuevos registros en esta tabla:
        * - Si necesitas añadir más entradas en el futuro, crea una NUEVA MIGRACIÓN que realice esos inserts.
        * - NO uses seeders para este tipo de datos, porque los seeders no pueden revertirse.
        * - En el método `down()` de esa nueva migración, debes ELIMINAR específicamente
        *   los registros añadidos por esa migración, asegurando que el rollback deje la tabla
        *   exactamente como estaba antes.
        */        
        
        DB::table('datamodel_types')->insert([
            'name' => 'TrafficFlowObserved',
            'created_at' => now(),
            'updated_at' => now(),
        ]);
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('datamodel_types');
    }
};
