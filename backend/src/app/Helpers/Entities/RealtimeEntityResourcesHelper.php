<?php

namespace App\Helpers\Entities;

use Illuminate\Http\Resources\Json\JsonResource;

class RealtimeEntityResourcesHelper
{
    public static function castValueTo($value, $valueType)
    {
        if ($valueType == 'string') {
            return RealtimeEntityResourcesHelper::toAsociativeArrayIfPossible($value);
        } else if ($valueType == 'double') {

            // if it contains a dot, then it is a double
            if (strpos($value, '.')) {
                $castedValue = (float) $value;
            } else {
                $castedValue = (int) $value;
            }

            // check if there is precission lost
            if ((string) $castedValue != $value) {
                return $value;
            }

            return $castedValue;
        } else if ($valueType == 'integer') {
            return (int) $value;
        } else if ($valueType == 'bool') {
            if ($value == 'true' || $value == 'True') {
                return true;
            } else {
                return false;
            }
        }

        return $value;
    }

    public static function toAsociativeArrayIfPossible($value)
    {
        # try to convert to associative array (it has to be a string)
        try {
            # first replace single quotes with double quotes
            $new_value = str_replace("'", '"', $value);
            # then convert to associative array
            $new_value = json_decode($new_value, true);
            # if it is not an array, return the original value
            if (!is_array($new_value)) {
                return $value;
            }

            // check if it is a null location 
            // because orion cannot set null locations,
            // so [0,0] is used instead
            $nullLocation = [
                "type" => "Point",
                "coordinates" => [0, 0],
            ];

            $ngsiNull = [
                "@type" => "@json",
                "@value" => null,
            ];

            if ($new_value == $nullLocation || $new_value == $ngsiNull) {
                return null;
            }

            return $new_value;
        } catch (\Exception $e) {
            # do nothing
            return $value;
        }
    }

    public static function camelCaseToSpaced($string)
    {
        $str = preg_replace('/(?<!^)[A-Z]/', ' $0', $string);
        #first letter to uppercase
        return ucfirst($str);
    }
}
