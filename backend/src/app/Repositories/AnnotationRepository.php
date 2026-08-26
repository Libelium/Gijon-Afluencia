<?php

namespace App\Repositories;

use Illuminate\Support\Facades\Validator;
use App\Models\Annotation;


class AnnotationRepository
{
  /**
   * Return paginated results using query and filters
   *
   * @return Illuminate\Support\Collection
   */

  public static function validateAnnotation($annotation)
  {
    $rules = [
      'alias' => 'nullable|string|max:255',
      'color' => 'required|string|max:255|min:1',
      'max' => 'required|numeric',
      'min' => 'required|numeric',
      'datamodel' => 'nullable|string',
      'measure' => 'nullable|string',
    ];

    $validator = Validator::make($annotation, $rules);

    $validator->validate();
  }

  public static function store($annotations, $panel)
  {
    foreach ($annotations as $annotation) {
      Annotation::create([
        'panel_id' => $panel->id,
        'alias' => $annotation['alias'],
        'color' => $annotation['color'],
        'max' => $annotation['max'],
        'min' => $annotation['min'],
        'datamodel' => $annotation['datamodel'] ?? null,
        'measure' => $annotation['measure'] ?? null,
      ]);
    }
  }

  public static function update($annotations, $panel)
  {
    Annotation::where('panel_id', $panel->id)->delete();
    self::store($annotations, $panel);
  }
}
