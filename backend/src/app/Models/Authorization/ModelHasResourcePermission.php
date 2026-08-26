<?php

namespace App\Models\Authorization;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\MorphTo;

class ModelHasResourcePermission extends Model
{
    protected $primaryKey = 'id';

    protected $fillable = [
        'model_id',
        'model_type',
        'resource_permission_id',
        'resource_type',
        'resource_id',
    ];

    /**
     * Define the relationship to the ResourcePermission model.
     */
    public function resource_permission() {
        return $this->belongsTo(ResourcePermission::class, 'resource_permission_id');
    }

    /**
     * Define a polymorphic relation to the model (user, admin, etc.)
     */
    public function model(): MorphTo
    {
        return $this->morphTo();
    }

    /**
     * Define a polymorphic relation to the resource.
     */
    public function resource(): MorphTo
    {
        return $this->morphTo();
    }
}
