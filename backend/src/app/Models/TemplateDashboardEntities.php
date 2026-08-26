<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class TemplateDashboardEntities extends AuditableModel
{
    protected $table = 'template_dashboard_entities';

    protected $fillable = [
        'template_dashboard_id',
        'entity_id',
    ];

    protected $hidden = [

    ];

    public function template_dashboard()
    {
        return $this->belongsTo(\App\Models\TemplateDashboard::class);
    }

    public function entity()
    {
        return $this->belongsTo(\App\Models\Entity::class)
            ->with(['devices', 'geolocation', 'fiwareScope', 'fiwareScope.tenant', 'entityProperties']);
    }
}
