<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
use App\Models\Entity;
use App\Models\FiwareTenant;
use App\Models\FiwareScope;

return new class extends Migration {
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('fiware_tenants', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->timestamps();
        });

        Schema::create('fiware_scopes', function (Blueprint $table) {
            $table->id();
            $table->foreignId('fiware_tenant_id')->references('id')->on('fiware_tenants')->onDelete('cascade');
            $table->string('name');
            $table->timestamps();

            $table->unique(['fiware_tenant_id', 'name']);
            $table->index('fiware_tenant_id');
        });

        // add the scope id to the entities
        Schema::table('entities', function (Blueprint $table) {
            $table->foreignId('fiware_scope_id')->nullable()->references('id')->on('fiware_scopes')->onDelete('cascade');
        });

        // to datamodel_subscriptions too
        Schema::table('datamodel_subscriptions', function (Blueprint $table) {
            $table->foreignId('fiware_scope_id')->nullable()->references('id')->on('fiware_scopes')->onDelete('cascade');
            // delete tenant and add scope 
            $table->dropColumn('tenant');
            $table->dropColumn('scope');
        });

        // sync the tenant and scope
        $this->syncTenantScopes();
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::table('entities', function (Blueprint $table) {
            $table->dropForeign(['fiware_scope_id']);
            $table->dropColumn('fiware_scope_id');
        });

        Schema::table('datamodel_subscriptions', function (Blueprint $table) {
            $table->dropForeign(['fiware_scope_id']);
            $table->dropColumn('fiware_scope_id');
            $table->string('tenant')->nullable();
            $table->string('scope')->nullable();
        });

        Schema::dropIfExists('fiware_scopes');
        Schema::dropIfExists('fiware_tenants');
    }

    public function syncTenantScopes()
    {
        $tenant_scopes = Entity::select('tenant', 'scope')->distinct()->get();

        foreach ($tenant_scopes as $tenant_scope) {
            $tenant = FiwareTenant::firstOrCreate(['name' => $tenant_scope->tenant]);
            if ($tenant) {
                $scope = FiwareScope::firstOrCreate(['fiware_tenant_id' => $tenant->id, 'name' => $tenant_scope->scope]);
            }
        }

        // raw sql
        DB::statement('
        UPDATE entities e
            SET fiware_scope_id = (
                SELECT s.id
                FROM fiware_scopes s
                JOIN fiware_tenants t ON s.fiware_tenant_id = t.id
                WHERE s.name = e.scope
                AND t.name = e.tenant
            )
      ');
    }
};
