<?php

namespace App\Enums;

use Exception;

enum SmspDatamodels: string
{
    case AirQualityObserved = "aqo";
    case NoiseLevelObserved = "nlo";
    case CrowdFlowEvent = "cfe";
    case CrowdFlowObserved = "cfo";
    case CrowdSimulationEvent = "cse";
    case WeatherObserved = "wto";
    case Device = "dev";
    case DeviceHealthObserved = "dho";
    case Irrigation = "irr";

    /**
     * Creates an enum instance from a string value.
     *
     * @param string $value The string value (e.g., 'aqo').
     * @return self The corresponding enum case.
     * @throws Exception if the value is invalid.
     */
    public static function fromValue(string $value): SmspDatamodels
    {
        return match ($value) {
            'aqo' => self::AirQualityObserved,
            'nlo' => self::NoiseLevelObserved,
            'cfe' => self::CrowdFlowEvent,
            'cfo' => self::CrowdFlowObserved,
            'cse' => self::CrowdSimulationEvent,
            'wto' => self::WeatherObserved,
            'dev' => self::Device,
            'dho' => self::DeviceHealthObserved,
            'irr' => self::Irrigation,
            default => throw new Exception('Invalid permission value: ' . $value),
        };
    }
}
