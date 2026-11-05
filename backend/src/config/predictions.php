<?php

return [

    // Where the predictions component keeps its models and its events registry, which this
    // application lists and edits (App\Services\PredictionEventsRegistry). Both must match that
    // component: the disk of the bucket it reads (its STORAGE_TYPE and bucket) and the prefix
    // (its MODELS_PREFIX).
    'events_disk' => env('PREDICTION_EVENTS_DISK', 's3'),

    'models_prefix' => env('PREDICTION_MODELS_PREFIX', 'prediction-models'),

];
