<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class OrganizationHasResource extends AuditableModel
{
    protected $table = 'organization_has_resource';

    protected $fillable = [
        'organization_id',
        'resource_id',
        'resource_type',
    ];
}
