<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Parking extends AuditableModel
{
  /**
  * The attributes that are mass assignable.
  *
  * @var array
  */
  // `id` is deliberately NOT fillable: letting a request set the primary key through a
  // mass assignment lets a caller overwrite or impersonate an existing row.
  protected $fillable = ['user_id', 'project_id', 'name', 'description', 'map_url', 'slug', 'content'];
}
