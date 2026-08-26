<?php

namespace App\Contracts;

/**
 * Marker interface for models that can have resource limits applied.
 *
 * Any Eloquent model implementing this interface is allowed to be
 * instantiated by ResourceLimitsHelper::getModelForResourceType().
 */
interface Limitable
{
}
