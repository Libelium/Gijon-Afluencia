<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Default Filesystem Disk
    |--------------------------------------------------------------------------
    |
    | Here you may specify the default filesystem disk that should be used
    | by the framework. The "local" disk, as well as a variety of cloud
    | based disks are available to your application. Just store away!
    |
    */

    'default' => env('FILESYSTEM_DISK', 'local'),

    /*
    |--------------------------------------------------------------------------
    | Filesystem Disks
    |--------------------------------------------------------------------------
    |
    | Here you may configure as many filesystem "disks" as you wish, and you
    | may even configure multiple disks of the same driver. Defaults have
    | been set up for each driver as an example of the required values.
    |
    | Supported Drivers: "local", "ftp", "sftp", "s3"
    |
    */

    'disks' => [

        'local' => [
            'driver' => 'local',
            'root' => storage_path('app'),
            'throw' => false,
        ],


        'logs' => [
            'driver' => 'local',
            'root' => storage_path('logs'),
        ],

        'public' => [
            'driver' => 'local',
            'root' => storage_path('app/public'),
            'url' => env('APP_URL').'/storage',
            'visibility' => 'public',
            'throw' => false,
        ],

        's3' => [
            'driver' => 's3',
            'key' => env('AWS_S3_KEY'),
            'secret' => env('AWS_S3_SECRET'),
            'region' => env('AWS_S3_REGION'),
            'bucket' => env('AWS_S3_BUCKET'),
            'url' => env('AWS_URL'),
            'endpoint' => env('AWS_ENDPOINT'),
            'use_path_style_endpoint' => env('AWS_USE_PATH_STYLE_ENDPOINT', false),
            'throw' => false,
        ],

        's3images' => [
            'driver' => 's3',
            'key' => env('AWS_S3_IMAGES_KEY'),
            'secret' => env('AWS_S3_IMAGES_SECRET'),
            'region' => env('AWS_S3_IMAGES_REGION'),
            'bucket' => env('AWS_S3_IMAGES_BUCKET'),
            'url' => env('AWS_URL'),
            'endpoint' => env('AWS_ENDPOINT'),
            'use_path_style_endpoint' => env('AWS_USE_PATH_STYLE_ENDPOINT', false),
            'throw' => false,
        ],
        
        's3documents' => [
            'driver' => 's3',
            'key' => env('AWS_S3_DOCS_KEY'),
            'secret' => env('AWS_S3_DOCS_SECRET'),
            'region' => env('AWS_S3_DOCS_REGION'),
            'bucket' => env('AWS_S3_DOCS_BUCKET'),
            'url' => env('AWS_URL'),
            'endpoint' => env('AWS_ENDPOINT'),
            'use_path_style_endpoint' => env('AWS_USE_PATH_STYLE_ENDPOINT', false),
            'throw' => false,
        ]
    ],

    /*
    |--------------------------------------------------------------------------
    | Symbolic Links
    |--------------------------------------------------------------------------
    |
    | Here you may configure the symbolic links that will be created when the
    | `storage:link` Artisan command is executed. The array keys should be
    | the locations of the links and the values should be their targets.
    |
    */

    'links' => [
        public_path('storage') => storage_path('app/public'),
    ],

    /*
    |--------------------------------------------------------------------------
    | Storage Paths
    |--------------------------------------------------------------------------
    |
    | Here you may configure the paths used for storing files in various
    | locations. These paths are used throughout the application.
    |
    */

    'paths' => [
        'dashboard_images' => env('STORAGE_PATH_DASHBOARD_IMAGES', '/dashboard/images'),
        'incident_images' => env('STORAGE_PATH_INCIDENT_IMAGES', '/incidents/images'),
        'entity_images' => env('STORAGE_PATH_ENTITY_IMAGES', '/entities/images'),
    ],

];
