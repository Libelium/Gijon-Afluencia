<?php

namespace App\Models;

use App\Contracts\Limitable;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\DB;

class AIMarketplacePipeline extends AuditableModel implements Limitable
{
    protected $table = 'ai_marketplace_pipelines';

    protected $fillable = [
        'name',
        'status',
        'description',
        'user_id',
    ];

    protected $hidden = [];

    public function user()
    {
        return $this->belongsTo(\App\Models\User::class);
    }

    public function models()
    {
        return $this->belongsToMany(\App\Models\AIMarketplaceModel::class, 'ai_marketplace_pipeline_models', 'ai_marketplace_pipeline_id', 'ai_marketplace_model_id')
            ->withPivot('order', 'extra')
            ->orderBy('ai_marketplace_pipeline_models.order');
    }

    public function entities()
    {
        return $this->belongsToMany(\App\Models\Entity::class, 'ai_marketplace_pipeline_entity', 'ai_marketplace_pipeline_id', 'entity_id');
    }

    public function permissions(): \Illuminate\Support\Collection
    {
        return \Illuminate\Support\Facades\Auth::user()->getResourcePermissions($this);
    }
}
