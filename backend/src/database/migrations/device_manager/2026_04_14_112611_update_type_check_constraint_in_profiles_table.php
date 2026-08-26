<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

return new class extends Migration
{
    protected $connection = 'device_manager';

    public function up(): void
    {
        DB::statement("ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_type_check");
        DB::statement("ALTER TABLE profiles ADD CONSTRAINT profiles_type_check CHECK (type IN
('https', 'http', 'mqtt', 'mqtts', 'coaps', 'azure', 'minimal', 'lora'))");
    }

    public function down(): void
    {
        DB::statement("ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_type_check");
        DB::statement("ALTER TABLE profiles ADD CONSTRAINT profiles_type_check CHECK (type IN
('https', 'mqtt', 'coap', 'azure-iot'))");
    }
};
