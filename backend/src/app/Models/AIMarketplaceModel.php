<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\DB;

class AIMarketplaceModel extends AuditableModel
{
    protected $table = 'ai_marketplace_models';

    protected $fillable = [
        'name',
        'description',
        'image',
        'input_datamodels',
        'output_datamodels',
        'key',
        'input_type',
        'output_types',
    ];

    protected $hidden = [];

    protected $casts = [
        'input_datamodels' => 'array',
        'output_datamodels' => 'array',
        'output_types' => 'array',
    ];
}
