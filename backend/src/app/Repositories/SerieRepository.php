<?php

namespace App\Repositories;

use App\Models\Dashboard;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Validator;
use App\Models\Panel;
use App\Models\Serie;
use App\Models\CalculatedSerie;
use App\Models\MeasureSerie;
use App\Models\Annotation;
use App\Models\MultidimensionalSerie;
use App\Repositories\AnnotationRepository;
use App\Models\Entity;
use Illuminate\Validation\ValidationException;


class SerieRepository
{
  /**
   * Return paginated results using query and filters
   *
   * @return Illuminate\Support\Collection
   */

  public static function validateSerie($serie)
  {

    $rules = [
      'id' => 'nullable|numeric',
      'alias' => 'required|string|max:255|min:1',
      'color' => 'required|string|max:255|min:1',
      'type' => 'required|string|max:255|min:1',
      'precision' => 'nullable|numeric',
      'style' => 'nullable|string',
    ];
    if ($serie['type'] == 'Calculated') {
      $rules['formula'] = 'required|string';
      $rules['unit'] = 'nullable|string|max:255';
    } else if ($serie['type'] == 'Measure') {
      $isDynamic = isset($serie['dynamicSource']);
      $linkMeasure = $isDynamic && ($serie['dynamicSource']['linkMeasure'] ?? false);
      $linkEntity  = $isDynamic && ($serie['dynamicSource']['linkEntity'] ?? false);

      $rules['entity.id'] = 'nullable|numeric';
      $rules['entity.urn'] = 'nullable|string';
      $rules['entity.tenant'] = 'nullable|string';
      $rules['entity.scope'] = 'nullable|string';
      $rules['measure.id'] = $linkMeasure ? 'nullable|string|max:255' : 'required|string|max:255|min:1';
      $rules['measure.name'] = $linkMeasure ? 'nullable|string|max:255' : 'required|string|max:255|min:1';
      $rules['measure.unit'] = 'nullable|string|max:255';
      $rules['visible'] = 'nullable|boolean';
      $rules['grouping_function'] = 'nullable|string|max:255|min:1';
      $rules['grouping_function_value'] = 'nullable|numeric';
      $rules['grouping_interval'] = 'nullable|string|max:255|min:1';
      $rules['grouping_interval_value'] = 'nullable|numeric';
      $rules['period'] = 'nullable|array';
      $rules['offset'] = 'nullable|array';
    } else if ($serie['type'] == 'Multidimensional') {
      $rules['dimensions'] = 'required|array';
      foreach ($serie['dimensions'] as $dimension) {
        SerieRepository::validateSerie($dimension);
      }
    }

    $validator = Validator::make($serie, $rules);

    $validator->validate();
  }

  /**
   * Store a new serie
   */
  private static function storeSeries($serie, $panel)
  {
    if (isset($serie['id']) && $serie['id'] > 0) {
      $s = Serie::find($serie['id']);
      $s->update([
        'alias' => $serie['alias'] ?? $s->alias,
        'color' => $serie['color'] ?? $s->color,
        'precision' => $serie['precision'] ?? null,
        'style' => $serie['style'] ?? $s->style,
      ]);
    } else {
      $s = Serie::create([
        'alias' => $serie['alias'],
        'color' => $serie['color'],
        'type' => $serie['type'],
        'panel_id' => $panel->id,
        'precision' => $serie['precision'] ?? null,
        'style' => $serie['style'] ?? null,
      ]);
    }

    return $s;
  }

  /**
   * Store calculated series
   */
  private static function storeCalculatedSerie($serie, $panel)
  {
    if (isset($serie['id']) && $serie['id'] > 0) {
      $s = SerieRepository::storeSeries($serie, $panel);

      CalculatedSerie::where('serie_id', $s->id)->update([
        'formula' => $serie['formula'],
        'unit' => $serie['unit'],
      ]);
    } else {
      $s = SerieRepository::storeSeries($serie, $panel);

      CalculatedSerie::create([
        'formula' => $serie['formula'],
        'unit' => $serie['unit'],
        'serie_id' => $s->id,
      ]);
    }
  }

  /**
   * Store measure series
   */
  private static function storeMeasureSerie($serie, $panel)
  {
    try {
      $isDynamic  = isset($serie['dynamicSource']);
      $linkEntity = $isDynamic && ($serie['dynamicSource']['linkEntity'] ?? false);
      $linkMeasure = $isDynamic && ($serie['dynamicSource']['linkMeasure'] ?? false);

      // Build measure JSON: include dynamicSource inside it when present
      $measureData = $linkMeasure ? [] : ($serie['measure'] ?? []);
      if ($isDynamic) {
        $measureData['dynamicSource'] = $serie['dynamicSource'];
      }

      // Resolve entity_id: use -1 as sentinel for dynamic entity
      if ($linkEntity) {
        $entityId = -1;
      } else {
        if (!isset($serie['entity']['id'])) {
          $e = Entity::where('urn', $serie['entity']['urn'])
            ->where('tenant', $serie['entity']['tenant'])
            ->where('scope', $serie['entity']['scope'])
            ->firstOrFail();
          $entityId = $e->id;
        } else {
          $entityId = $serie['entity']['id'];
        }
      }

      $measureFields = [
        'entity_id' => $entityId,
        'measure' => $measureData,
        'visible' => $serie['visible'] ?? true,
        'period' => $serie['period'] ?? [],
        'offset' => $serie['offset'] ?? null,
        'grouping_function' => array_key_exists('grouping_function', $serie) ? $serie['grouping_function'] : null,
        'grouping_function_value' => array_key_exists('grouping_function', $serie) && array_key_exists('grouping_function_value', $serie) ? $serie['grouping_function_value'] : null,
        'grouping_interval' => array_key_exists('grouping_function', $serie) ? $serie['grouping_interval'] : null,
        'grouping_interval_value' => array_key_exists('grouping_function', $serie) ? $serie['grouping_interval_value'] : null,
      ];

      if (isset($serie['id']) && $serie['id'] > 0) {
        $s = SerieRepository::storeSeries($serie, $panel);
        MeasureSerie::where('serie_id', $s->id)->update($measureFields);
      } else {
        $s = SerieRepository::storeSeries($serie, $panel);
        MeasureSerie::create(array_merge($measureFields, ['serie_id' => $s->id]));
      }
    } catch (\Exception $e) {
      throw ValidationException::withMessages([
        'measure' => ['Measure or entity not found'],
      ]);
    }
  }

  /**
   * Store monodimensional series
   */
  private static function storeMonodimensionalSeries($series, $panel)
  {
    foreach ($series as $serie) {
      if ($serie['type'] == 'Calculated') {
        SerieRepository::storeCalculatedSerie($serie, $panel);
      } else if ($serie['type'] == 'Measure') {
        SerieRepository::storeMeasureSerie($serie, $panel);
      }
    }
  }

  /**
   * Store multidimensional series
   */
  private static function storeMultidimensionalSeries($series, $panel)
  {
    foreach ($series as $serie) {
      if ($serie['type'] == 'Multidimensional') {
        $s = SerieRepository::storeSeries($serie, $panel);

        $s->extra_multidimensional()->delete();

        $i = 0;
        foreach ($serie['dimensions'] as $dimension) {
          if ($dimension['type'] == 'Calculated') {
            $d = CalculatedSerie::select('serie_id')
              ->leftJoin('series', 'calculated_series.serie_id', '=', 'series.id')
              ->where('formula', $dimension['formula'])
              ->where('unit', $dimension['unit'])
              ->where('series.panel_id', $panel->id)
              ->first();
          } else if ($dimension['type'] == 'Measure') {
            $d = MeasureSerie::select('serie_id')
              ->leftJoin('series', 'measure_series.serie_id', '=', 'series.id')
              ->where('entity_id', $dimension['entity']['id'])
              ->whereRaw("measure ->> 'id' = ?", [$dimension['measure']['id']])
              ->whereRaw("measure ->> 'urn' = ?", [$dimension['measure']['urn']])
              ->where('visible', $dimension['visible'])
              ->where('grouping_function', array_key_exists('grouping_function', $dimension) ? $dimension['grouping_function'] : null)
              ->where('grouping_function_value', array_key_exists('grouping_function', $serie) && array_key_exists('grouping_function_value', $serie) ? $serie['grouping_function_value'] : null)
              ->where('grouping_interval', array_key_exists('grouping_function', $dimension) ? $dimension['grouping_interval'] : null)
              ->where('grouping_interval_value', array_key_exists('grouping_function', $dimension) ? $dimension['grouping_interval_value'] : null)
              ->where('series.panel_id', $panel->id)
              ->first();
          } else {
            throw ValidationException::withMessages([
              'dimensions' => ['Invalid dimension type'],
            ]);
          }

          MultidimensionalSerie::create([
            'serie_id' => $s->id,
            'axis' => $i,
            'dimension_serie_id' => $d->serie_id,
          ]);

          $i++;
        }
      }
    }
  }


  /**
   * Store series
   */
  public static function store($series, $panel)
  {
    SerieRepository::storeMonodimensionalSeries($series, $panel);
    SerieRepository::storeMultidimensionalSeries($series, $panel);
  }

  /**
   * Update series
   */
  public static function update($series, $panel)
  {
    // Delete all series that are not in the new series
    $panel->series()->whereNotIn('id', array_map(function ($serie) {
      return isset($serie['id']) ? $serie['id'] : -1;
    }, $series))->delete();
    SerieRepository::store($series, $panel);
  }
}
