<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class CustomDatamodelMapping extends AuditableModel
{

    protected $fillable = [
        'custom_datamodel_id',
        'datamodel',
        'mapping',
        'type'
    ];

    public function customDatamodel()
{
    return $this->belongsTo(CustomDatamodel::class, 'custom_datamodel_id');
}
}
