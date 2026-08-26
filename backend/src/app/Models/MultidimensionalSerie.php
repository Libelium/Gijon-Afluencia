<?php
namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class MultidimensionalSerie extends AuditableModel
{
    protected $table = 'multidimensional_series';

    protected $fillable = [
        'serie_id',
        'axis',
        'dimension_serie_id',
    ];

    protected $hidden = [

    ];

    public function serie()
    {
        return $this->belongsTo(\App\Models\Serie::class);
    }

    public function dimension()
    {
        return $this->belongsTo(\App\Models\Serie::class, 'dimension_serie_id')->with('extra_measure')->with('extra_calculated');
    }
}
