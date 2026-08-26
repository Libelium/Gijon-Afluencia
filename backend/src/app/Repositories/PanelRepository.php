<?php

namespace App\Repositories;

use Illuminate\Support\Facades\Validator;
use App\Models\Annotation;
use App\Models\Panel;
use App\Models\Serie;
use App\Models\CalculatedSerie;
use App\Models\MeasureSerie;
use App\Models\MultidimensionalSerie;
use App\Repositories\AnnotationRepository;
use App\Repositories\SerieRepository;
use Illuminate\Validation\ValidationException;


class PanelRepository
{
  /**
   * Return paginated results using query and filters
   */

  public static function validatePanel($request)
  {
    foreach ($request->series as $serie) {
      SerieRepository::validateSerie($serie);
    }

    $request->annotations = $request->annotations ?? [];

    foreach ($request->annotations as $annotation) {
      AnnotationRepository::validateAnnotation($annotation);
    }
  }

  /**
   * Return paginated results using query and filters
 
   */
  public static function store($request)
  {
    $panel = Panel::create([
      'title' => $request->title ?? null,
      'chart' => $request->chart,
      'dashboard_id' => $request->dashboard_id,
      'relative_time' => $request->relativeTime ?? false,
      'date_range' => $request->dateRange ?? null,
    ]);

    SerieRepository::store($request->series, $panel);
    AnnotationRepository::store($request->annotations, $panel);

    $panel['series'] = $panel->series()->with('extra_calculated')->with('extra_measure')->with('extra_multidimensional')->get();
    $panel['annotations'] = $panel->annotations()->get();

    return $panel;
  }

  /**
   * Return paginated results using query and filters
   */
  public static function update($request, $id)
  {
    $panel = Panel::findOrFail($id);

    $panel->update([
      'title' => $request->title ?? null,
      'chart' => $request->chart ?? $panel->chart,
      'dashboard_id' => $request->dashboard_id ?? $panel->dashboard_id,
      'relative_time' => $request->relativeTime ?? false,
      'date_range' => $request->dateRange ?? $panel->date_range,
    ]);


    SerieRepository::update($request->series, $panel);
    AnnotationRepository::update($request->annotations, $panel);

    $panel['series'] = $panel->series()->with('extra_calculated')->with('extra_measure')->with('extra_multidimensional')->get();
    $panel['annotations'] = $panel->annotations()->get();

    return $panel;
  }
}
