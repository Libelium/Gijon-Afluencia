<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Annotation extends AuditableModel
{
    protected $table = 'annotations';

    protected $fillable = [
        'max',
        'min',
        'alias',
        'color',
        'panel_id',
        'datamodel',
        'measure',
    ];

    protected $hidden = [

    ];

    protected $casts = [
        'max' => 'float',
        'min' => 'float',
        'alias' => 'string',
        'color' => 'string',
        'panel_id' => 'integer',
        'datamodel' => 'string',
        'measure' => 'string',
    ];

    public function panel()
    {
        return $this->belongsTo(\App\Models\Panel::class);
    }
    
    
}
