<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use OwenIt\Auditing\Contracts\Auditable as AuditableContract;
use OwenIt\Auditing\Auditable as AuditableTrait;

/**
 * Base model for all auditable models in the system.
 */
abstract class AuditableModel extends Model implements AuditableContract
{
    use AuditableTrait {
        toAudit as protected traitToAudit;
    }

    /**
     * Customize audit data globally.
     */
    public function toAudit(): array
    {
        $data = $this->traitToAudit();

        // Delete fields that should not be audited
        unset($data['user_type']);
        unset($data['tags']);

        return $data;
    }
}
