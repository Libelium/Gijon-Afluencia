<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class CalculatedSerie extends AuditableModel
{
    protected $table = 'calculated_series';

    protected $fillable = [
        'serie_id',
        'formula',
        'unit',
    ];

    protected $hidden = [

    ];

    public function serie()
    {
        return $this->belongsTo(\App\Models\Serie::class);
    }
}
