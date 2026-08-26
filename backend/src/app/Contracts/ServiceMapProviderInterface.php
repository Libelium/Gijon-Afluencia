<?php

namespace App\Contracts;

/**
 * Defines the contract for classes that provide the application's service map.
 * Any class implementing this interface must be able to return an array
 * that maps service names to their corresponding datamodels.
 */
interface ServiceMapProviderInterface
{
    /**
     * Returns the application's service map.
     *
     * @return array<string, string[]>
     */
    public function provide(): array;
}