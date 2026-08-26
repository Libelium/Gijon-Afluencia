<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class TemplateDashboardDevices extends AuditableModel
{
    protected $table = 'template_dashboard_devices';

    protected $fillable = [
        'template_dashboard_id',
        'device_id',
    ];

    protected $hidden = [

    ];

    public function template_dashboard()
    {
        return $this->belongsTo(\App\Models\TemplateDashboard::class);
    }

    public function device()
    {
        return $this->belongsTo(\App\Models\Device::class)
            ->with(['entities.fiwareScope.tenant', 'mainEntity.entityProperties', 'entities.entityProperties' ]);
    }
}
