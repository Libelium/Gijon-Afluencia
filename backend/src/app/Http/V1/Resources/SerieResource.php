<?php

namespace App\Http\V1\Resources;

use Illuminate\Http\Resources\Json\JsonResource;
use Illuminate\Support\Facades\Auth;

class SerieResource extends JsonResource
{
    /**
     * Transform the resource into an array.
     *
     * @param  \Illuminate\Http\Request  $request
     * @return array
     */
    public function toArray($request)
    {
        $serie = [
            'id' => $this->id,
            'alias' => $this->alias,
            'color' => $this->color,
            'type' => $this->type,
            'precision' => $this->precision,
            'style' => $this->style,
        ];

        if ($this->type == 'Measure' && isset($this->extra_measure)) {
            $measureData = $this->extra_measure->measure ?? [];
            $dynamicSource = $measureData['dynamicSource'] ?? null;
            unset($measureData['dynamicSource']);

            $serie['visible'] = $this->extra_measure->visible;
            $serie['grouping_function'] = $this->extra_measure->grouping_function;
            $serie['grouping_function_value'] = $this->extra_measure->grouping_function_value;
            $serie['grouping_interval'] = $this->extra_measure->grouping_interval;
            $serie['grouping_interval_value'] = $this->extra_measure->grouping_interval_value;
            $serie['period'] = $this->extra_measure->period;
            $serie['measure'] = !empty($measureData) ? $measureData : null;
            $serie['offset'] = $this->extra_measure->offset;

            if ($dynamicSource) {
                $serie['dynamicSource'] = $dynamicSource;
            }

            $isLinkEntity = $dynamicSource['linkEntity'] ?? false;
            if (!$isLinkEntity && $this->extra_measure->entity_id != -1 && $this->extra_measure->entity) {
                $serie['entity'] = EntityResource::make($this->extra_measure->entity->load(['devices', 'fiwareScope', 'fiwareScope.tenant', 'name']));
            }
        }

        if ($this->type == 'Calculated' && isset($this->extra_calculated)) {
            $serie['formula'] = $this->extra_calculated->formula;
            $serie['unit'] = $this->extra_calculated->unit;
        }

        if ($this->type == 'Multidimensional' && isset($this->extra_multidimensional)) {
            $serie['dimensions'] = SerieResource::collection($this->extra_multidimensional->pluck('dimension'));
        }

        return $serie;
    }
}
