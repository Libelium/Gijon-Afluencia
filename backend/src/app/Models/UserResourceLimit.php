<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * App\Models\UserResourceLimit
 *
 * @property int $id
 * @property int $user_id
 * @property string $resource_type
 * @property int $value
 * @property \Illuminate\Support\Carbon|null $created_at
 * @property \Illuminate\Support\Carbon|null $updated_at
 * @property-read \App\Models\User $user
 * @method static \Illuminate\Database\Eloquent\Builder|UserResourceLimit newModelQuery()
 * @method static \Illuminate\Database\Eloquent\Builder|UserResourceLimit newQuery()
 * @method static \Illuminate\Database\Eloquent\Builder|UserResourceLimit query()
 * @method static \Illuminate\Database\Eloquent\Builder|UserResourceLimit whereCreatedAt($value)
 * @method static \Illuminate\Database\Eloquent\Builder|UserResourceLimit whereId($value)
 * @method static \Illuminate\Database\Eloquent\Builder|UserResourceLimit whereResourceType($value)
 * @method static \Illuminate\Database\Eloquent\Builder|UserResourceLimit whereUpdatedAt($value)
 * @method static \Illuminate\Database\Eloquent\Builder|UserResourceLimit whereUserId($value)
 * @method static \Illuminate\Database\Eloquent\Builder|UserResourceLimit whereValue($value)
 * @mixin \Eloquent
 */
class UserResourceLimit extends AuditableModel
{
    use HasFactory;

    /**
     * The table associated with the model.
     *
     * @var string
     */
    protected $table = 'user_resource_limits';

    /**
     * The attributes that are mass assignable.
     *
     * @var array<int, string>
     */
    protected $fillable = [
        'user_id',
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

    /**
     * Get the user that this resource limit belongs to.
     */
    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }
}
