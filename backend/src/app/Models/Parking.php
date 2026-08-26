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
  protected $fillable = ['id', 'user_id', 'project_id', 'name', 'description', 'map_url', 'slug', 'content'];
}
