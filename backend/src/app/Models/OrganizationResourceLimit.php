<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * App\Models\OrganizationResourceLimit
 *
 * @property int $id
 * @property int $organization_id
 * @property string $resource_type
 * @property int $value
 * @property \Illuminate\Support\Carbon|null $created_at
 * @property \Illuminate\Support\Carbon|null $updated_at
 * @property-read \App\Models\Organization $organization
 * @method static \Illuminate\Database\Eloquent\Builder|OrganizationResourceLimit newModelQuery()
 * @method static \Illuminate\Database\Eloquent\Builder|OrganizationResourceLimit newQuery()
 * @method static \Illuminate\Database\Eloquent\Builder|OrganizationResourceLimit query()
 * @method static \Illuminate\Database\Eloquent\Builder|OrganizationResourceLimit whereCreatedAt($value)
 * @method static \Illuminate\Database\Eloquent\Builder|OrganizationResourceLimit whereId($value)
 * @method static \Illuminate\Database\Eloquent\Builder|OrganizationResourceLimit whereOrganizationId($value)
 * @method static \Illuminate\Database\Eloquent\Builder|OrganizationResourceLimit whereResourceType($value)
 * @method static \Illuminate\Database\Eloquent\Builder|OrganizationResourceLimit whereUpdatedAt($value)
 * @method static \Illuminate\Database\Eloquent\Builder|OrganizationResourceLimit whereValue($value)
 * @mixin \Eloquent
 */
class OrganizationResourceLimit extends AuditableModel
{
    use HasFactory;

    /**
     * The table associated with the model.
     *
     * @var string
     */
    protected $table = 'organization_resource_limits';

    /**
     * The attributes that are mass assignable.
     *
     * @var array<int, string>
     */
    protected $fillable = [
        'organization_id',
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
     * Get the organization that this resource limit belongs to.
     */
    public function organization(): BelongsTo
    {
        return $this->belongsTo(Organization::class);
    }
}
