<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class WRFDomain extends Model
{
    protected $table = 'wrf_domains';

    protected $fillable = [
        'name',
        'upper_left_coordinates',
        'lower_right_coordinates',
        'current_simulation_id',
        'user_id',
        'entity_id',
    ];

    protected $casts = [
        'upper_left_coordinates' => 'array',
        'lower_right_coordinates' => 'array',
    ];

    /**
     * Set upper_left_coordinates from [latitude, longitude] array to GeoJSON Point format
     */
    public function setUpperLeftCoordinatesAttribute($value)
    {
        if (is_array($value) && isset($value[0]) && isset($value[1]) && !isset($value['type'])) {
            $this->attributes['upper_left_coordinates'] = json_encode([
                'type' => 'Point',
                'coordinates' => $value
            ]);
        } elseif (is_array($value)) {
            $this->attributes['upper_left_coordinates'] = json_encode($value);
        } else {
            $this->attributes['upper_left_coordinates'] = $value;
        }
    }

    /**
     * Set lower_right_coordinates from [latitude, longitude] array to GeoJSON Point format
     */
    public function setLowerRightCoordinatesAttribute($value)
    {
        if (is_array($value) && isset($value[0]) && isset($value[1]) && !isset($value['type'])) {
            $this->attributes['lower_right_coordinates'] = json_encode([
                'type' => 'Point',
                'coordinates' => $value
            ]);
        } elseif (is_array($value)) {
            $this->attributes['lower_right_coordinates'] = json_encode($value);
        } else {
            $this->attributes['lower_right_coordinates'] = $value;
        }
    }

    public function user()
    {
        return $this->belongsTo(\App\Models\User::class);
    }

    public function simulations()
    {
        return $this->hasMany(WRFSimulation::class, 'domain_id');
    }

    public function currentSimulation()
    {
        return $this->belongsTo(WRFSimulation::class, 'current_simulation_id');
    }

    public function entity()
    {
        return $this->belongsTo(Entity::class, 'entity_id');
    }
}
