<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

/**
 * App\Models\ResourceLimit
 *
 * @property int $id
 * @property string $resource_type
 * @property int $value
 * @property \Illuminate\Support\Carbon|null $created_at
 * @property \Illuminate\Support\Carbon|null $updated_at
 * @method static \Illuminate\Database\Eloquent\Builder|ResourceLimit newModelQuery()
 * @method static \Illuminate\Database\Eloquent\Builder|ResourceLimit newQuery()
 * @method static \Illuminate\Database\Eloquent\Builder|ResourceLimit query()
 * @method static \Illuminate\Database\Eloquent\Builder|ResourceLimit whereCreatedAt($value)
 * @method static \Illuminate\Database\Eloquent\Builder|ResourceLimit whereId($value)
 * @method static \Illuminate\Database\Eloquent\Builder|ResourceLimit whereResourceType($value)
 * @method static \Illuminate\Database\Eloquent\Builder|ResourceLimit whereUpdatedAt($value)
 * @method static \Illuminate\Database\Eloquent\Builder|ResourceLimit whereValue($value)
 * @mixin \Eloquent
 */
class ResourceLimit extends AuditableModel
{
    use HasFactory;

    /**
     * The table associated with the model.
     *
     * @var string
     */
    protected $table = 'resource_limits';

    /**
     * The attributes that are mass assignable.
     *
     * @var array<int, string>
     */
    protected $fillable = [
        'resource_type',
        'value',
    ];

    /**
     * The attributes that should be cast.
     *
     * @var array<string, string>
     */
    protected $casts = [
        'value' => 'integer',
    ];
}
