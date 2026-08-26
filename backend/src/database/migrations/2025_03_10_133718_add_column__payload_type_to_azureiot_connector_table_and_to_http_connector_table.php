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
        Schema::table('http_connector', function (Blueprint $table) {
            Schema::table('http_connector', function (Blueprint $table) {
                $table->string('payload_type')->default('legacy');
            });
            
            // // set default value for existing records to legacy
            // DB::table('http_connector')->update(['payload_type' => 'legacy']);
            
            // // make it not null 
            // Schema::table('http_connector', function (Blueprint $table) {
            //     $table->string('payload_type')->nullable(false)->change();
            // });
        });

        Schema::table('azureiot_connector', function (Blueprint $table) {
            Schema::table('azureiot_connector', function (Blueprint $table) {
                $table->string('payload_type')->default('legacy');
                $table->jsonb('payload_config')->nullable();
            });
            
            // // set default value for existing records to legacy
            // DB::table('azureiot_connector')->update(['payload_type' => 'legacy']);
            
            // Schema::table('azureiot_connector', function (Blueprint $table) {
            //     $table->string('payload_type')->nullable(false)->change();
            // });
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('http_connector', function (Blueprint $table) {
            $table->dropColumn('payload_type');
        });

        Schema::table('azureiot_connector', function (Blueprint $table) {
            $table->dropColumn('payload_type');
            $table->dropColumn('payload_config');
        });
    }
};
