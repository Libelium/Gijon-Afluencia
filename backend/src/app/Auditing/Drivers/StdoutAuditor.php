<?php

namespace App\Auditing\Drivers;

use OwenIt\Auditing\Contracts\Auditable;
use OwenIt\Auditing\Contracts\Auditor;
use OwenIt\Auditing\Contracts\AuditDriver;
use OwenIt\Auditing\Contracts\Audit;

/**
 * Custom auditor that prints audits to STDOUT or error_log.
 */
class StdoutAuditor implements Auditor, AuditDriver
{
    /**
     * Returns the driver instance (required by the contract).
     */
    public function auditDriver(Auditable $model): AuditDriver
    {
        return $this;
    }

    /**
     * Executes the audit and prints the log to stdout.
     */
    public function audit(Auditable $model): ?Audit
    {
        $data = $model->toAudit();

        unset($data['user_type']);

        if (empty($data['old_values']) && empty($data['new_values'])) {
            return null;
        }

        $json = json_encode($data, JSON_UNESCAPED_SLASHES);

        if (defined('STDOUT')) {
            fwrite(\STDOUT, "[AUDIT] " . $json . PHP_EOL);
        } else {
            error_log("[AUDIT] " . $json);
        }

        // Nothing is stored, so we return null
        return null;
    }

    /**
     * Internal alias to execute the audit.
     */
    public function execute(Auditable $model): ?Audit
    {
        return $this->audit($model);
    }

    /**
     * Method required by the AuditDriver interface.
     * In this case, nothing is pruned, so we return false.
     */
    public function prune(Auditable $model): bool
    {
        return false;
    }
}
