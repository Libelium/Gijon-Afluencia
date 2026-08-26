<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Device Files Configuration
    |--------------------------------------------------------------------------
    |
    | This file contains configuration values for device file management,
    | including presigned URL expiration times for uploads and downloads.
    |
    */

    /*
    |--------------------------------------------------------------------------
    | Presigned URL Expiration Times
    |--------------------------------------------------------------------------
    |
    | Configure how long presigned URLs remain valid before expiring.
    | Times are specified in minutes.
    |
    */

    'presigned_url_expiration' => [
        // Download URL expiration (default: 60 minutes = 1 hour)
        // Used for: download, view, migration files
        'download' => env('DEVICE_FILES_DOWNLOAD_URL_EXPIRATION', 60),

        // Upload URL expiration (default: 30 minutes)
        // Used for: direct uploads to S3/Minio
        'upload' => env('DEVICE_FILES_UPLOAD_URL_EXPIRATION', 30),
    ],

    /*
    |--------------------------------------------------------------------------
    | Storage Configuration
    |--------------------------------------------------------------------------
    |
    | Storage disk and root folder for device files.
    |
    */

    'storage' => [
        // Storage disk to use (default: s3)
        'disk' => env('DEVICE_FILES_STORAGE_DISK', 's3'),

        // Root folder for device files in the storage
        'root_folder' => env('DEVICE_FILES_ROOT_FOLDER', '/device_files'),
    ],

];
