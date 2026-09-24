<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Access level of a user over the data of its organization: 'read' (consulta) or 'edit'
     * (edicion). Null means no organization-wide access: only what the user creates, which is
     * what every non-admin user had before this column existed.
     */
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->string('access_level', 10)->nullable()->after('status');
        });
    }

    public function down(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->dropColumn('access_level');
        });
    }
};
