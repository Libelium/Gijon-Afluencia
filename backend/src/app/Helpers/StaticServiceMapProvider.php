<?php

namespace App\Helpers;

use App\Contracts\ServiceMapProviderInterface;

/**
 * Concrete implementation of ServiceMapProviderInterface that returns
 * a service map defined statically in the code.
 */
class StaticServiceMapProvider implements ServiceMapProviderInterface
{
    /**
     * @var array<string, string[]>
     */
    private static array $map = [
        "Envair"  => ["PointOfInterest", "AirQualityObserved", "NoiseLevelObserved"],
        "Crowd"   => ["CrowdFlowEventETL", "CrowdFlowEvent", "CrowdFlowObservedETL", "CrowdFlowObserved"],
        "CrowdSimulations" => ["CrowdSimulationEvent"],
        "Alarms"  => ["PlatformAlarm"],
        "Traffic" => ["TrafficFlowObserved", "TrafficFlowEvent", "TrafficCamera", "Camera"],
        "Healthcheck" => ["DeviceHealthcheck"],
    ];

    /**
     * Provides the service map.
     *
     * @return array<string, string[]>
     */
    public function provide(): array
    {
        return self::$map;
    }
}